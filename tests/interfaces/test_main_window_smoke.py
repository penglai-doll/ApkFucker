from PyQt6.QtWidgets import QApplication

from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_main_window_has_expected_navigation() -> None:
    app = _app()
    window = MainWindow()

    labels = [window.nav_list.item(i).text() for i in range(window.nav_list.count())]
    assert labels == [
        "Task Center",
        "Static Summary",
        "Method Index",
        "Hook Assistant",
        "Script Plan",
        "Custom Frida Scripts",
        "Execution & Logs",
        "Traffic Capture",
        "Results Summary",
    ]
    assert window.open_jadx_action.text() == "Open in JADX"
    assert not window.open_jadx_action.isEnabled()
    assert window.script_plan.execution_mode_combo.currentText() == "Fake Backend"
    assert [
        window.script_plan.execution_mode_combo.itemText(index)
        for index in range(window.script_plan.execution_mode_combo.count())
    ] == [
        "Fake Backend",
        "Real Device",
        "ADB Probe",
        "Frida Bootstrap",
        "Frida Probe",
        "Frida Inject",
        "Frida Session",
    ]
    assert window.content_stack.count() == len(labels)
    assert app is not None
    window.close()


def test_main_window_keeps_open_jadx_disabled_for_blank_launcher_path() -> None:
    app = _app()
    window = MainWindow(jadx_gui_path="")

    assert not window.open_jadx_action.isEnabled()
    assert app is not None
    window.close()


def test_main_window_disables_demo_loading_without_fixture_sources() -> None:
    app = _app()
    window = MainWindow()

    assert app is not None
    assert window.task_center.run_analysis_button.isEnabled()
    assert window.task_center.refresh_environment_button.isEnabled()
    assert window.task_center.environment_summary_value.text()
    assert not window.task_center.load_demo_button.isEnabled()
    assert "ready to analyze" in window.results_summary.summary_label.text().lower()

    window.close()
