from pathlib import Path

from PyQt6.QtWidgets import QApplication

from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_main_window_runs_demo_hook_workflow(tmp_path: Path) -> None:
    app = _app()
    window = MainWindow(
        fixture_root=Path("tests/fixtures/static_outputs"),
        jadx_sources_root=Path("tests/fixtures/jadx_sources"),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )

    window.task_center.sample_path_input.setText("/samples/demo.apk")
    window.task_center.load_demo_button.click()

    assert window.static_summary.package_value.text() == "com.demo.shell"
    assert window.method_index.method_list.count() == 5

    window.method_index.search_input.setText("upload")
    window.method_index.apply_search()
    assert window.method_index.method_list.count() == 2

    window.method_index.method_list.setCurrentRow(1)
    window.method_index.add_selected_button.click()
    assert window.script_plan.plan_list.count() == 1
    selected_method = window.method_index.current_method()
    assert selected_method is not None
    assert selected_method.parameter_types == ("String", "String")

    window.script_plan.run_fake_button.click()
    assert window.execution_logs.log_list.count() == 1
    assert "buildUploadUrl" in window.execution_logs.log_list.item(0).text()
    assert "1 event" in window.results_summary.summary_label.text()

    window.script_plan.run_fake_button.click()
    assert window.execution_logs.log_list.count() == 1
    assert "1 event" in window.results_summary.summary_label.text()

    assert app is not None
    window.close()
