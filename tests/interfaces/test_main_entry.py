from pathlib import Path

from PyQt6.QtWidgets import QApplication

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
        ]
    )

    assert args.sample == Path("/samples/demo.apk")
    assert args.jadx_gui_path == "/opt/jadx/bin/jadx-gui"
    assert args.scripts_root == Path("/tmp/scripts")
    assert args.db_root == Path("/tmp/cache")


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
