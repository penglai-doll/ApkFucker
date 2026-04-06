from pathlib import Path

from PyQt6.QtWidgets import QApplication

from apk_hacker.interfaces.gui_pyqt.widgets.results_summary import ResultsSummaryWidget


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_results_summary_widget_updates_paths_and_copy_buttons(tmp_path: Path) -> None:
    app = _app()
    widget = ResultsSummaryWidget()
    db_path = tmp_path / "job-1-run-1.sqlite3"
    bundle_path = tmp_path / "execution-runs" / "job-1-run-1"

    widget.set_summary("Captured 2 event(s).", db_path=db_path, bundle_path=bundle_path)

    assert "job-1-run-1.sqlite3" in widget.db_path_label.text()
    assert "execution-runs" in widget.bundle_path_label.text()
    assert widget.copy_db_path_button.isEnabled()
    assert widget.copy_bundle_path_button.isEnabled()
    assert app is not None
    widget.close()


def test_results_summary_widget_copies_paths_to_clipboard(tmp_path: Path) -> None:
    app = _app()
    widget = ResultsSummaryWidget()
    db_path = tmp_path / "job-1-run-1.sqlite3"
    bundle_path = tmp_path / "execution-runs" / "job-1-run-1"

    widget.set_summary("Captured 2 event(s).", db_path=db_path, bundle_path=bundle_path)

    widget.copy_db_path_button.click()
    assert app.clipboard().text() == str(db_path)

    widget.copy_bundle_path_button.click()
    assert app.clipboard().text() == str(bundle_path)
    widget.close()
