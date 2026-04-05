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
        "Results Summary",
    ]
    assert window.open_jadx_action.text() == "Open in JADX"
    assert window.content_stack.count() == len(labels)
    assert app is not None
    window.close()
