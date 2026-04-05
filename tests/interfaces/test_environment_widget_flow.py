from pathlib import Path

from PyQt6.QtWidgets import QApplication

from apk_hacker.application.services.environment_service import EnvironmentSnapshot, ToolStatus
from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow
from apk_hacker.interfaces.gui_pyqt.viewmodels import WorkbenchController


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _FakeEnvironmentService:
    def __init__(self) -> None:
        self.calls = 0

    def inspect(self) -> EnvironmentSnapshot:
        self.calls += 1
        if self.calls == 1:
            return EnvironmentSnapshot(
                tools=(
                    ToolStatus(name="jadx", label="jadx", available=True, path="/opt/tools/jadx"),
                    ToolStatus(name="adb", label="adb", available=False, path=None),
                )
            )
        return EnvironmentSnapshot(
            tools=(
                ToolStatus(name="jadx", label="jadx", available=True, path="/opt/tools/jadx"),
                ToolStatus(name="adb", label="adb", available=True, path="/opt/android/adb"),
            )
        )


def test_main_window_refreshes_environment_status(tmp_path: Path) -> None:
    app = _app()
    fake_service = _FakeEnvironmentService()
    controller = WorkbenchController(
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        environment_service=fake_service,
    )
    window = MainWindow(controller=controller)

    assert "1 available" in window.task_center.environment_summary_value.text().lower()
    assert "adb: missing" in window.task_center.environment_details_value.text().lower()

    window.task_center.refresh_environment_button.click()

    assert "2 available" in window.task_center.environment_summary_value.text().lower()
    assert "adb: /opt/android/adb" in window.task_center.environment_details_value.text().lower()
    assert app is not None
    window.close()
