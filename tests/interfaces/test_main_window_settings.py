from pathlib import Path
import json

from PyQt6.QtWidgets import QApplication

from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.domain.models.environment import EnvironmentSnapshot, ToolStatus
from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow
from apk_hacker.interfaces.gui_pyqt.viewmodels import WorkbenchController


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _ReadyFridaEnvironmentService(EnvironmentService):
    def inspect(self) -> EnvironmentSnapshot:
        return EnvironmentSnapshot(
            tools=(
                ToolStatus(name="jadx", label="jadx", available=True, path="/opt/tools/jadx"),
                ToolStatus(name="jadx-gui", label="jadx-gui", available=True, path="/opt/tools/jadx-gui"),
                ToolStatus(name="apktool", label="apktool", available=True, path="/opt/tools/apktool"),
                ToolStatus(name="adb", label="adb", available=True, path="/opt/android/adb"),
                ToolStatus(name="frida", label="frida", available=True, path="/opt/homebrew/bin/frida"),
                ToolStatus(name="python-frida", label="python-frida", available=True, path="module:frida"),
            )
        )


def test_main_window_persists_runtime_preferences(tmp_path: Path) -> None:
    app = _app()
    controller = WorkbenchController(
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        environment_service=_ReadyFridaEnvironmentService(),
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText("/samples/persisted.apk")
    window.task_center.device_serial_input.setText("serial-123")
    window.task_center.frida_server_binary_input.setText("/tmp/frida-server")
    window.task_center.frida_server_remote_path_input.setText("/data/local/tmp/custom-frida")
    window.task_center.frida_session_seconds_input.setText("3.5")
    window.script_plan.execution_mode_combo.setCurrentIndex(
        window.script_plan.execution_mode_combo.findData("real_frida_inject")
    )
    window.close()

    settings_path = tmp_path / "workbench-settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload == {
        "sample_path": "/samples/persisted.apk",
        "execution_mode": "real_frida_inject",
        "device_serial": "serial-123",
        "frida_server_binary_path": "/tmp/frida-server",
        "frida_server_remote_path": "/data/local/tmp/custom-frida",
        "frida_session_seconds": "3.5",
    }
    assert app is not None


def test_main_window_restores_runtime_preferences_from_settings(tmp_path: Path) -> None:
    app = _app()
    settings_path = tmp_path / "workbench-settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "sample_path": "/samples/restored.apk",
                "execution_mode": "real_frida_session",
                "device_serial": "serial-restore",
                "frida_server_binary_path": "/tmp/restore-frida-server",
                "frida_server_remote_path": "/data/local/tmp/restore-frida",
                "frida_session_seconds": "4.5",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    controller = WorkbenchController(
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        environment_service=_ReadyFridaEnvironmentService(),
    )

    window = MainWindow(controller=controller)

    assert window.task_center.sample_path_input.text() == "/samples/restored.apk"
    assert window.task_center.device_serial_input.text() == "serial-restore"
    assert window.task_center.frida_server_binary_input.text() == "/tmp/restore-frida-server"
    assert window.task_center.frida_server_remote_path_input.text() == "/data/local/tmp/restore-frida"
    assert window.task_center.frida_session_seconds_input.text() == "4.5"
    assert window.script_plan.current_execution_mode() == "real_frida_session"
    assert window.task_center.current_sample_value.text() == "-"
    assert app is not None
    window.close()
