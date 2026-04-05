from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def run() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
