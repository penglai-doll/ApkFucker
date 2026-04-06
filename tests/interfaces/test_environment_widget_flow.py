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
                    ToolStatus(name="frida", label="frida", available=False, path=None),
                    ToolStatus(name="python-frida", label="python-frida", available=False, path=None),
                )
            )
        return EnvironmentSnapshot(
            tools=(
                ToolStatus(name="jadx", label="jadx", available=True, path="/opt/tools/jadx"),
                ToolStatus(name="adb", label="adb", available=True, path="/opt/android/adb"),
                ToolStatus(name="frida", label="frida", available=True, path="/opt/homebrew/bin/frida"),
                ToolStatus(name="python-frida", label="python-frida", available=True, path="module:frida"),
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
    assert "Real Device: unavailable (no ready backend)" in window.task_center.execution_presets_value.text()
    assert "ADB Probe: unavailable" in window.task_center.execution_presets_value.text()
    assert "Frida Session: unavailable" in window.task_center.execution_presets_value.text()
    adb_probe_index = window.script_plan.execution_mode_combo.findData("real_adb_probe")
    frida_session_index = window.script_plan.execution_mode_combo.findData("real_frida_session")
    assert not window.script_plan.execution_mode_combo.model().item(adb_probe_index).isEnabled()
    assert not window.script_plan.execution_mode_combo.model().item(frida_session_index).isEnabled()

    window.task_center.refresh_environment_button.click()

    assert "4 available" in window.task_center.environment_summary_value.text().lower()
    assert "adb: /opt/android/adb" in window.task_center.environment_details_value.text().lower()
    assert "Real Device: ready (Frida Session)" in window.task_center.execution_presets_value.text()
    assert "ADB Probe: ready" in window.task_center.execution_presets_value.text()
    assert "Frida Session: ready" in window.task_center.execution_presets_value.text()
    assert window.script_plan.execution_mode_combo.model().item(adb_probe_index).isEnabled()
    assert window.script_plan.execution_mode_combo.model().item(frida_session_index).isEnabled()
    assert app is not None
    window.close()
