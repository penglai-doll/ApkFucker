import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def test_main_window_has_expected_navigation(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

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
