from __future__ import annotations

from pathlib import Path

from apk_hacker.interfaces.gui_pyqt.main import LegacyGuiCompatWindow
from apk_hacker.interfaces.gui_pyqt.main import build_window
from apk_hacker.interfaces.gui_pyqt.main import parse_args
from apk_hacker.interfaces.gui_pyqt.main import run


def test_parse_args_accepts_legacy_runtime_options() -> None:
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


def test_build_window_returns_compatibility_descriptor(tmp_path: Path) -> None:
    window = build_window(
        parse_args(
            [
                "--sample",
                str(tmp_path / "sample.apk"),
                "--scripts-root",
                str(tmp_path / "scripts"),
                "--db-root",
                str(tmp_path / "cache"),
                "--device-serial",
                "serial-123",
            ]
        )
    )

    assert isinstance(window, LegacyGuiCompatWindow)
    assert window.sample_path == tmp_path / "sample.apk"
    assert window.scripts_root == tmp_path / "scripts"
    assert window.db_root == tmp_path / "cache"
    assert window.execution_backend_env["APKHACKER_DEVICE_SERIAL"] == "serial-123"
    assert "Tauri + React + FastAPI" in window.deprecation_message


def test_run_reports_legacy_gui_deprecation(capsys: object) -> None:
    exit_code = run([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "旧版 PyQt 工作台已退役" in captured.err
    assert "npm run dev:tauri" in captured.err
