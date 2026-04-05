from pathlib import Path
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
            "--real-backend-command",
            "python /tmp/runner.py",
        ]
    )

    assert args.sample == Path("/samples/demo.apk")
    assert args.jadx_gui_path == "/opt/jadx/bin/jadx-gui"
    assert args.scripts_root == Path("/tmp/scripts")
    assert args.db_root == Path("/tmp/cache")
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

    assert len(events) == 1
    assert events[0].event_type == "cli_backend"
    assert events[0].arguments == ("com.demo.shell",)
    assert app is not None
    window.close()
