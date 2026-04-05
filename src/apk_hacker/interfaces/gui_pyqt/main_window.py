from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLabel, QListWidget, QMainWindow, QSplitter, QStackedWidget, QVBoxLayout, QWidget

from apk_hacker.interfaces.gui_pyqt.viewmodels import NavigationPage, WorkbenchController, WorkbenchState
from apk_hacker.interfaces.gui_pyqt.widgets.custom_scripts import CustomScriptsWidget
from apk_hacker.interfaces.gui_pyqt.widgets.execution_logs import ExecutionLogsWidget
from apk_hacker.interfaces.gui_pyqt.widgets.method_index import MethodIndexWidget
from apk_hacker.interfaces.gui_pyqt.widgets.results_summary import ResultsSummaryWidget
from apk_hacker.interfaces.gui_pyqt.widgets.script_plan import ScriptPlanWidget
from apk_hacker.interfaces.gui_pyqt.widgets.static_summary import StaticSummaryWidget
from apk_hacker.interfaces.gui_pyqt.widgets.task_center import TaskCenterWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        fixture_root: Path | None = None,
        jadx_sources_root: Path | None = None,
        scripts_root: Path | None = None,
        db_root: Path | None = None,
        controller: WorkbenchController | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("APKHacker")
        self.resize(1400, 900)

        repo_root = Path(__file__).resolve().parents[4]
        if controller is not None:
            self._controller = controller
            demo_available = True
        elif fixture_root is not None and jadx_sources_root is not None:
            self._controller = WorkbenchController(
                fixture_root=fixture_root,
                jadx_sources_root=jadx_sources_root,
                scripts_root=scripts_root or repo_root / "user_data" / "frida_plugins" / "custom",
                db_root=db_root or repo_root / "cache" / "gui",
            )
            demo_available = True
        else:
            self._controller = None
            demo_available = False
        self._state = WorkbenchState(
            summary_text="Demo workspace not configured for this build." if not demo_available else "No analysis run yet."
        )

        self.open_jadx_action = QAction("Open in JADX", self)
        self.menuBar().addAction(self.open_jadx_action)

        self.nav_list = QListWidget()
        self.content_stack = QStackedWidget()

        self.task_center = TaskCenterWidget()
        self.static_summary = StaticSummaryWidget()
        self.method_index = MethodIndexWidget()
        self.hook_assistant = _PlaceholderPage("Hook Assistant")
        self.script_plan = ScriptPlanWidget()
        self.custom_scripts = CustomScriptsWidget()
        self.execution_logs = ExecutionLogsWidget()
        self.results_summary = ResultsSummaryWidget()

        self.method_index.on_search_requested = self._search_methods
        self.method_index.on_add_selected_requested = self._add_selected_method
        self.script_plan.on_run_requested = self._run_fake_analysis
        self.task_center.load_demo_button.clicked.connect(self._load_demo_workspace)
        self.task_center.set_demo_available(demo_available)

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
        self._sync_ui()

    def _pages(self) -> tuple[tuple[NavigationPage, QWidget], ...]:
        return (
            (NavigationPage("Task Center", "task-center"), self.task_center),
            (NavigationPage("Static Summary", "static-summary"), self.static_summary),
            (NavigationPage("Method Index", "method-index"), self.method_index),
            (NavigationPage("Hook Assistant", "hook-assistant"), self.hook_assistant),
            (NavigationPage("Script Plan", "script-plan"), self.script_plan),
            (NavigationPage("Custom Frida Scripts", "custom-scripts"), self.custom_scripts),
            (NavigationPage("Execution & Logs", "execution-logs"), self.execution_logs),
            (NavigationPage("Results Summary", "results-summary"), self.results_summary),
        )

    def _load_demo_workspace(self) -> None:
        if self._controller is None:
            self._state = WorkbenchState(summary_text="Demo workspace not configured for this build.")
            self._sync_ui()
            return
        sample_path = self.task_center.selected_sample_path()
        self._state = self._controller.load_demo_workspace(sample_path)
        self._sync_ui()

    def _search_methods(self, query: str) -> None:
        if self._controller is None:
            return
        self._state = self._controller.search_methods(self._state, query)
        self.method_index.set_methods(self._state.visible_methods)

    def _add_selected_method(self) -> None:
        if self._controller is None:
            return
        method = self.method_index.current_method()
        if method is None:
            return
        self._state = self._controller.add_method_to_plan(self._state, method)
        self._sync_ui()

    def _run_fake_analysis(self) -> None:
        if self._controller is None:
            return
        self._state = self._controller.run_fake_analysis(self._state)
        self._sync_ui()

    def _sync_ui(self) -> None:
        current_method = self.method_index.current_method()
        self.task_center.set_job(self._state.current_job, self._state.sample_path)
        self.static_summary.set_static_inputs(self._state.static_inputs)
        self.method_index.set_methods(self._state.visible_methods, preferred_method=current_method)
        if self.method_index.search_input.text() != self._state.search_query:
            self.method_index.search_input.setText(self._state.search_query)
        self.script_plan.set_plan(self._state.hook_plan)
        self.custom_scripts.set_scripts(self._state.custom_scripts)
        self.execution_logs.set_events(self._state.hook_events)
        self.results_summary.set_summary(self._state.summary_text)


class _PlaceholderPage(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))
        layout.addStretch(1)
