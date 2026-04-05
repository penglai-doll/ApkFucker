from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QListWidget, QMainWindow, QSplitter, QStackedWidget, QWidget

from apk_hacker.interfaces.gui_pyqt.viewmodels import NavigationPage
from apk_hacker.interfaces.gui_pyqt.widgets.custom_scripts import CustomScriptsWidget
from apk_hacker.interfaces.gui_pyqt.widgets.execution_logs import ExecutionLogsWidget
from apk_hacker.interfaces.gui_pyqt.widgets.method_index import MethodIndexWidget
from apk_hacker.interfaces.gui_pyqt.widgets.results_summary import ResultsSummaryWidget
from apk_hacker.interfaces.gui_pyqt.widgets.script_plan import ScriptPlanWidget
from apk_hacker.interfaces.gui_pyqt.widgets.static_summary import StaticSummaryWidget
from apk_hacker.interfaces.gui_pyqt.widgets.task_center import TaskCenterWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("APKHacker")
        self.resize(1400, 900)

        self.open_jadx_action = QAction("Open in JADX", self)
        self.menuBar().addAction(self.open_jadx_action)

        self.nav_list = QListWidget()
        self.content_stack = QStackedWidget()

        for page, widget in self._pages():
            self.nav_list.addItem(page.title)
            widget.setObjectName(page.object_name)
            self.content_stack.addWidget(widget)

        splitter = QSplitter()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def _pages(self) -> tuple[tuple[NavigationPage, QWidget], ...]:
        return (
            (NavigationPage("Task Center", "task-center"), TaskCenterWidget()),
            (NavigationPage("Static Summary", "static-summary"), StaticSummaryWidget()),
            (NavigationPage("Method Index", "method-index"), MethodIndexWidget()),
            (NavigationPage("Hook Assistant", "hook-assistant"), QWidget()),
            (NavigationPage("Script Plan", "script-plan"), ScriptPlanWidget()),
            (NavigationPage("Custom Frida Scripts", "custom-scripts"), CustomScriptsWidget()),
            (NavigationPage("Execution & Logs", "execution-logs"), ExecutionLogsWidget()),
            (NavigationPage("Results Summary", "results-summary"), ResultsSummaryWidget()),
        )
