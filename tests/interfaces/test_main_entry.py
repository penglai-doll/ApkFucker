from pathlib import Path
import os
import sys

from PyQt6.QtWidgets import QApplication

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.interfaces.gui_pyqt.main import build_window, parse_args


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_parse_args_accepts_gui_paths_and_sample() -> None:
    args = parse_args(
        [
            "--sample",
            "/samples/demo.apk",
            "--jadx-gui-path",
            "/opt/jadx/bin/jadx-gui",
            "--scripts-root",
            "/tmp/scripts",
            "--db-root",
            "/tmp/cache",
            "--device-serial",
            "serial-123",
            "--frida-server-binary",
            "/tmp/frida-server",
            "--real-backend-command",
            "python /tmp/runner.py",
        ]
    )

    assert args.sample == Path("/samples/demo.apk")
    assert args.jadx_gui_path == "/opt/jadx/bin/jadx-gui"
    assert args.scripts_root == Path("/tmp/scripts")
    assert args.db_root == Path("/tmp/cache")
    assert args.device_serial == "serial-123"
    assert args.frida_server_binary == Path("/tmp/frida-server")
    assert args.real_backend_command == "python /tmp/runner.py"


def test_build_window_prefills_sample_input(tmp_path: Path) -> None:
    app = _app()
    window = build_window(
        parse_args(
            [
                "--sample",
                str(tmp_path / "sample.apk"),
                "--scripts-root",
                str(tmp_path / "scripts"),
                "--db-root",
                str(tmp_path / "cache"),
            ]
        )
    )

    assert window.task_center.sample_path_input.text() == str(tmp_path / "sample.apk")
    assert app is not None
    window.close()


def test_build_window_uses_cli_real_backend_command(tmp_path: Path) -> None:
    app = _app()
    helper = tmp_path / "emit_real_backend.py"
    helper.write_text(
        """
import json
import os

print(json.dumps({
    "event_type": "cli_backend",
    "class_name": "cli.real",
    "method_name": "configured",
    "arguments": [os.environ.get("APKHACKER_TARGET_PACKAGE", "")],
    "return_value": "ok",
    "stacktrace": ""
}))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    window = build_window(
        parse_args(
            [
                "--scripts-root",
                str(tmp_path / "scripts"),
                "--db-root",
                str(tmp_path / "cache"),
                "--real-backend-command",
                f"{sys.executable} {helper}",
            ]
        )
    )

    backend = window._controller._execution_backends["real_device"]
    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=HookPlan(items=()),
            package_name="com.demo.shell",
        )
    )

    assert len(events) == 2
    assert events[0].event_type == "execution_bundle"
    assert Path(events[0].arguments[0]).exists()
    assert events[1].event_type == "cli_backend"
    assert events[1].arguments == ("com.demo.shell",)
    assert app is not None
    window.close()


def test_build_window_forwards_bootstrap_env_to_builtin_backends(tmp_path: Path) -> None:
    app = _app()
    adb_path = tmp_path / "adb"
    adb_state = tmp_path / "adb-state.jsonl"
    frida_server_binary = tmp_path / "frida-server"
    frida_server_binary.write_text("fake-binary", encoding="utf-8")
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
    printf '9001\\n'
  fi
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "push" ]; then
  append "push:$4->$5"
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ]; then
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
    original_path = os.environ["PATH"]
    os.environ["PATH"] = f"{tmp_path}:{original_path}"
    try:
        window = build_window(
            parse_args(
                [
                    "--scripts-root",
                    str(tmp_path / "scripts"),
                    "--db-root",
                    str(tmp_path / "cache"),
                    "--device-serial",
                    "serial-123",
                    "--frida-server-binary",
                    str(frida_server_binary),
                ]
            )
        )
        backend = window._controller._execution_backends["real_frida_bootstrap"]
        events = backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))
    finally:
        os.environ["PATH"] = original_path

    assert events[-1].return_value == "running:9001"
    assert app is not None
    window.close()
