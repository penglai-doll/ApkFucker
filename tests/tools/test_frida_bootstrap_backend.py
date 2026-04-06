from pathlib import Path
import json
import os
import sys

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def _write_fake_adb(path: Path, script: str) -> Path:
    adb_path = path / "adb"
    adb_path.write_text(script, encoding="utf-8")
    adb_path.chmod(0o755)
    return adb_path


def test_packaged_frida_bootstrap_backend_reports_running_server(tmp_path: Path) -> None:
    _write_fake_adb(
        tmp_path,
        """#!/bin/sh
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
  printf '2451\\n'
  exit 0
fi
exit 1
""",
    )
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_bootstrap_backend",
        extra_env={"PATH": env_path},
    )

    events = backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))

    assert [event.event_type for event in events] == [
        "device_connected",
        "device_property",
        "device_root_status",
        "frida_server_status",
    ]
    assert events[2].return_value == "rooted"
    assert events[3].return_value == "running:2451"


def test_packaged_frida_bootstrap_backend_pushes_and_starts_server(tmp_path: Path) -> None:
    state_file = tmp_path / "adb-state.jsonl"
    frida_server_binary = tmp_path / "frida-server"
    frida_server_binary.write_text("fake-binary", encoding="utf-8")
    _write_fake_adb(
        tmp_path,
        f"""#!/bin/sh
STATE_FILE="{state_file}"
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
    printf '9001\\n'
  fi
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
    )
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_bootstrap_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_FRIDA_SERVER_BINARY": str(frida_server_binary),
        },
    )

    events = backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))
    state_records = [line.strip() for line in state_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert [event.event_type for event in events] == [
        "device_connected",
        "device_property",
        "device_root_status",
        "frida_server_action",
        "frida_server_action",
        "frida_server_action",
        "frida_server_status",
    ]
    assert state_records == [
        f"push:{frida_server_binary}->/data/local/tmp/frida-server",
        "shell:chmod 755 /data/local/tmp/frida-server",
        "shell:/data/local/tmp/frida-server >/dev/null 2>&1 &",
    ]
    assert events[-1].return_value == "running:9001"
