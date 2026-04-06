from pathlib import Path
import os
import sys
import time

from pytest import raises

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def _write_fake_frida(path: Path, args_file: Path) -> Path:
    frida_path = path / "frida"
    frida_path.write_text(
        f"""#!/bin/sh
printf '%s\\n' "$@" > "{args_file}"
sleep 5
""",
        encoding="utf-8",
    )
    frida_path.chmod(0o755)
    return frida_path


def _read_text_eventually(path: Path, timeout_seconds: float = 3.0) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    return path.read_text(encoding="utf-8")


def test_packaged_frida_inject_backend_invokes_frida_with_target_and_script(tmp_path: Path) -> None:
    args_file = tmp_path / "frida-args.txt"
    _write_fake_frida(tmp_path, args_file)
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="sources/com/demo/net/Config.java",
        line_hint=4,
    )
    plan = HookPlanService().plan_for_methods([method])
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_inject_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_FRIDA_WARMUP_SECONDS": "1.5",
        },
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
        )
    )

    recorded_args = _read_text_eventually(args_file).splitlines()
    assert recorded_args[:3] == ["-U", "-f", "com.demo.shell"]
    assert "-l" in recorded_args
    assert any(argument.endswith(".js") for argument in recorded_args)
    assert len(events) == 1
    assert events[0].event_type == "frida_injection"
    assert events[0].method_name == "spawn_attach"
    assert events[0].arguments[0] == "com.demo.shell"


def test_packaged_frida_inject_backend_honors_selected_device_serial(tmp_path: Path) -> None:
    args_file = tmp_path / "frida-args.txt"
    _write_fake_frida(tmp_path, args_file)
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="sources/com/demo/net/Config.java",
        line_hint=4,
    )
    plan = HookPlanService().plan_for_methods([method])
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_inject_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_DEVICE_SERIAL": "serial-123",
            "APKHACKER_FRIDA_WARMUP_SECONDS": "1.5",
        },
    )

    backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
        )
    )

    recorded_args = _read_text_eventually(args_file).splitlines()
    assert recorded_args[:4] == ["-D", "serial-123", "-f", "com.demo.shell"]


def test_packaged_frida_inject_backend_requires_rendered_script(tmp_path: Path) -> None:
    _write_fake_frida(tmp_path, tmp_path / "unused-frida-args.txt")
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_inject_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_FRIDA_WARMUP_SECONDS": "1.5",
        },
    )

    with raises(ExecutionBackendUnavailable, match="No rendered Frida scripts"):
        backend.execute(
            ExecutionRequest(
                job_id="job-1",
                plan=HookPlan(items=()),
                package_name="com.demo.shell",
            )
        )


def test_packaged_frida_inject_backend_bootstraps_and_installs_before_probe(tmp_path: Path) -> None:
    args_file = tmp_path / "frida-args.txt"
    adb_state = tmp_path / "adb-state.jsonl"
    sample_path = tmp_path / "sample.apk"
    frida_server_binary = tmp_path / "frida-server"
    sample_path.write_bytes(b"apk")
    frida_server_binary.write_text("fake-binary", encoding="utf-8")
    _write_fake_frida(tmp_path, args_file)
    adb_path = tmp_path / "adb"
    adb_path.write_text(
        f"""#!/bin/sh
STATE_FILE="{adb_state}"
append() {{
  printf '%s\\n' "$1" >> "$STATE_FILE"
}}
if [ "$1" = "devices" ]; then
  printf 'List of devices attached\\nserial-123\\tdevice\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "getprop" ] && [ "$5" = "ro.product.cpu.abi" ]; then
  printf 'arm64-v8a\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ] && [ "$6" = "id" ]; then
  printf 'uid=0(root) gid=0(root)\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ] && [ "$6" = "pidof frida-server" ]; then
  if [ -f "$STATE_FILE.started" ]; then
    printf '9999\\n'
  fi
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "pm" ] && [ "$5" = "path" ] && [ "$6" = "com.demo.shell" ]; then
  append "pm-path:$6"
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "install" ] && [ "$4" = "-r" ] && [ "$5" = "{sample_path}" ]; then
  append "install:$5"
  printf 'Success\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "push" ]; then
  append "push:$4->$5"
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ]; then
  append "shell:$6"
  case "$6" in
    "chmod 755 /data/local/tmp/frida-server")
      exit 0
      ;;
    "/data/local/tmp/frida-server >/dev/null 2>&1 &")
      : > "$STATE_FILE.started"
      exit 0
      ;;
  esac
fi
exit 1
""",
        encoding="utf-8",
    )
    adb_path.chmod(0o755)
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="sources/com/demo/net/Config.java",
        line_hint=4,
    )
    plan = HookPlanService().plan_for_methods([method])
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_inject_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_DEVICE_SERIAL": "serial-123",
            "APKHACKER_FRIDA_SERVER_BINARY": str(frida_server_binary),
            "APKHACKER_FRIDA_WARMUP_SECONDS": "1.5",
        },
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
            sample_path=sample_path,
        )
    )

    adb_records = [line.strip() for line in _read_text_eventually(adb_state).splitlines() if line.strip()]
    recorded_args = _read_text_eventually(args_file).splitlines()
    assert adb_records == [
        "pm-path:com.demo.shell",
        f"install:{sample_path}",
        f"push:{frida_server_binary}->/data/local/tmp/frida-server",
        "shell:chmod 755 /data/local/tmp/frida-server",
        "shell:/data/local/tmp/frida-server >/dev/null 2>&1 &",
    ]
    assert recorded_args[:4] == ["-D", "serial-123", "-f", "com.demo.shell"]
    assert [event.event_type for event in events[:5]] == [
        "app_install_status",
        "device_connected",
        "device_property",
        "device_root_status",
        "frida_server_action",
    ]
    assert events[-1].event_type == "frida_injection"
