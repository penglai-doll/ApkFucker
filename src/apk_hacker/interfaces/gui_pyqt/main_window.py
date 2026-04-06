from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable

from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import QListWidget, QMainWindow, QSplitter, QStackedWidget, QWidget

from apk_hacker.application.services.workbench_settings_service import WorkbenchSettings, WorkbenchSettingsService
from apk_hacker.infrastructure.integrations.jadx_launcher import open_in_jadx, resolve_jadx_gui_path
from apk_hacker.interfaces.gui_pyqt.viewmodels import NavigationPage, WorkbenchController, WorkbenchState
from apk_hacker.interfaces.gui_pyqt.widgets.custom_scripts import CustomScriptsWidget
from apk_hacker.interfaces.gui_pyqt.widgets.execution_logs import ExecutionLogsWidget
from apk_hacker.interfaces.gui_pyqt.widgets.hook_assistant import HookAssistantWidget
from apk_hacker.interfaces.gui_pyqt.widgets.method_index import MethodIndexWidget
from apk_hacker.interfaces.gui_pyqt.widgets.results_summary import ResultsSummaryWidget
from apk_hacker.interfaces.gui_pyqt.widgets.script_plan import ScriptPlanWidget
from apk_hacker.interfaces.gui_pyqt.widgets.static_summary import StaticSummaryWidget
from apk_hacker.interfaces.gui_pyqt.widgets.task_center import TaskCenterWidget
from apk_hacker.interfaces.gui_pyqt.widgets.traffic_capture import TrafficCaptureWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        fixture_root: Path | None = None,
        jadx_sources_root: Path | None = None,
        scripts_root: Path | None = None,
        db_root: Path | None = None,
        jadx_gui_path: str | None = None,
        jadx_launcher: Callable[[str, Path], object] | None = None,
        controller: WorkbenchController | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("APKHacker")
        self.resize(1400, 900)
        self._jadx_gui_path = resolve_jadx_gui_path(jadx_gui_path)
        self._jadx_launcher = jadx_launcher or open_in_jadx

        repo_root = Path(__file__).resolve().parents[4]
        resolved_db_root = db_root or (controller.db_root if controller is not None else repo_root / "cache" / "gui")
        if controller is not None:
            self._controller = controller
        else:
            self._controller = WorkbenchController(
                fixture_root=fixture_root,
                jadx_sources_root=jadx_sources_root,
                scripts_root=scripts_root or repo_root / "user_data" / "frida_plugins" / "custom",
                db_root=resolved_db_root,
            )
        self._settings_service = WorkbenchSettingsService(resolved_db_root / "workbench-settings.json")
        self._restoring_settings = False
        demo_available = self._controller.demo_available
        self._state = WorkbenchState(
            summary_text="Ready to analyze a sample." if not demo_available else "No analysis run yet."
        )
        self._state = self._controller.refresh_environment(self._state, announce=False)

        self.open_jadx_action = QAction("Open in JADX", self)
        self.menuBar().addAction(self.open_jadx_action)
        self.open_jadx_action.triggered.connect(self._open_in_jadx)
        self.export_report_action = QAction("Export Report", self)
        self.menuBar().addAction(self.export_report_action)
        self.export_report_action.triggered.connect(self._export_report)

        self.nav_list = QListWidget()
        self.content_stack = QStackedWidget()

        self.task_center = TaskCenterWidget()
        self.static_summary = StaticSummaryWidget()
        self.method_index = MethodIndexWidget()
        self.hook_assistant = HookAssistantWidget()
        self.script_plan = ScriptPlanWidget()
        self.custom_scripts = CustomScriptsWidget()
        self.execution_logs = ExecutionLogsWidget()
        self.traffic_capture = TrafficCaptureWidget()
        self.results_summary = ResultsSummaryWidget()

        self.method_index.on_search_requested = self._search_methods
        self.method_index.on_add_selected_requested = self._add_selected_method
        self.hook_assistant.on_add_selected_requested = self._add_selected_recommendation
        self.hook_assistant.on_add_top_requested = self._add_top_recommendations
        self.custom_scripts.on_add_selected_requested = self._add_selected_custom_script
        self.custom_scripts.on_save_requested = self._save_custom_script
        self.custom_scripts.on_selection_changed = self._select_custom_script
        self.script_plan.on_execution_mode_changed = self._change_execution_mode
        self.script_plan.on_run_requested = self._run_analysis
        self.traffic_capture.on_load_requested = self._load_traffic_capture
        self.task_center.run_analysis_button.clicked.connect(self._load_sample_workspace)
        self.task_center.load_demo_button.clicked.connect(self._load_demo_workspace)
        self.task_center.refresh_environment_button.clicked.connect(self._refresh_environment)
        self.task_center.set_analysis_available(True)
        self.task_center.set_demo_available(demo_available)

        for page, widget in self._pages():
            self.nav_list.addItem(page.title)
            widget.setObjectName(page.object_name)
            self.content_stack.addWidget(widget)

        self._restore_ui_settings()
        self._connect_settings_autosave()

        splitter = QSplitter()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)
        self._sync_ui()

    def _restore_ui_settings(self) -> None:
        settings = self._settings_service.load()
        available_modes = {status.key for status in self._state.execution_preset_statuses if status.available}
        restored_mode = settings.execution_mode if settings.execution_mode in available_modes else "fake_backend"
        self._restoring_settings = True
        try:
            if settings.sample_path:
                self.task_center.sample_path_input.setText(settings.sample_path)
            self.task_center.set_runtime_options(
                settings.device_serial,
                settings.frida_server_binary_path,
                settings.frida_server_remote_path,
                settings.frida_session_seconds,
            )
            self._state = replace(
                self._state,
                execution_mode=restored_mode,
                device_serial=settings.device_serial,
                frida_server_binary_path=settings.frida_server_binary_path,
                frida_server_remote_path=settings.frida_server_remote_path,
                frida_session_seconds=settings.frida_session_seconds,
            )
        finally:
            self._restoring_settings = False

    def _connect_settings_autosave(self) -> None:
        self.task_center.sample_path_input.textChanged.connect(self._persist_ui_settings)
        self.task_center.device_serial_input.textChanged.connect(self._persist_ui_settings)
        self.task_center.frida_server_binary_input.textChanged.connect(self._persist_ui_settings)
        self.task_center.frida_server_remote_path_input.textChanged.connect(self._persist_ui_settings)
        self.task_center.frida_session_seconds_input.textChanged.connect(self._persist_ui_settings)
        self.script_plan.execution_mode_combo.currentIndexChanged.connect(self._persist_ui_settings)

    def _persist_ui_settings(self) -> None:
        if self._restoring_settings:
            return
        try:
            self._settings_service.save(
                WorkbenchSettings(
                    sample_path=self.task_center.sample_path_input.text().strip(),
                    execution_mode=self.script_plan.current_execution_mode(),
                    device_serial=self.task_center.selected_device_serial(),
                    frida_server_binary_path=self.task_center.selected_frida_server_binary(),
                    frida_server_remote_path=self.task_center.selected_frida_server_remote_path(),
                    frida_session_seconds=self.task_center.selected_frida_session_seconds(),
                )
            )
        except OSError:
            return

    def _pages(self) -> tuple[tuple[NavigationPage, QWidget], ...]:
        return (
            (NavigationPage("Task Center", "task-center"), self.task_center),
            (NavigationPage("Static Summary", "static-summary"), self.static_summary),
            (NavigationPage("Method Index", "method-index"), self.method_index),
            (NavigationPage("Hook Assistant", "hook-assistant"), self.hook_assistant),
            (NavigationPage("Script Plan", "script-plan"), self.script_plan),
            (NavigationPage("Custom Frida Scripts", "custom-scripts"), self.custom_scripts),
            (NavigationPage("Execution & Logs", "execution-logs"), self.execution_logs),
            (NavigationPage("Traffic Capture", "traffic-capture"), self.traffic_capture),
            (NavigationPage("Results Summary", "results-summary"), self.results_summary),
        )

    def _load_demo_workspace(self) -> None:
        device_serial, frida_server_binary, frida_server_remote_path, frida_session_seconds = self._runtime_inputs()
        if not self._controller.demo_available:
            self._state = WorkbenchState(
                summary_text="Demo workspace not configured for this build.",
                device_serial=device_serial,
                frida_server_binary_path=frida_server_binary,
                frida_server_remote_path=frida_server_remote_path,
                frida_session_seconds=frida_session_seconds,
            )
            self._sync_ui()
            return
        sample_path = self.task_center.selected_sample_path()
        self._state = self._with_runtime_inputs(self._controller.load_demo_workspace(sample_path))
        self._sync_ui()

    def _load_sample_workspace(self) -> None:
        device_serial, frida_server_binary, frida_server_remote_path, frida_session_seconds = self._runtime_inputs()
        sample_path = self.task_center.selected_sample_path()
        try:
            self._state = self._with_runtime_inputs(self._controller.load_sample_workspace(sample_path))
        except Exception as exc:
            self._state = WorkbenchState(
                sample_path=sample_path,
                summary_text=f"Static analysis failed: {exc}",
                device_serial=device_serial,
                frida_server_binary_path=frida_server_binary,
                frida_server_remote_path=frida_server_remote_path,
                frida_session_seconds=frida_session_seconds,
            )
        self._sync_ui()

    def _refresh_environment(self) -> None:
        self._state = self._with_runtime_inputs(self._controller.refresh_environment(self._with_runtime_inputs(self._state)))
        self._sync_ui()

    def _export_report(self) -> None:
        self._state = self._with_runtime_inputs(self._controller.export_report(self._state))
        self._sync_ui()

    def _search_methods(self, query: str) -> None:
        self._state = self._controller.search_methods(self._state, query)
        self.method_index.set_methods(self._state.visible_methods)

    def _add_selected_method(self) -> None:
        method = self.method_index.current_method()
        if method is None:
            return
        self._state = self._controller.add_method_to_plan(self._state, method)
        self._sync_ui()

    def _run_analysis(self) -> None:
        self._state = self._controller.run_analysis(self._with_runtime_inputs(self._state))
        self._sync_ui()

    def _load_traffic_capture(self) -> None:
        har_path = self.traffic_capture.selected_har_path()
        self._state = self._controller.load_traffic_capture(self._state, har_path)
        self._sync_ui()

    def _add_selected_recommendation(self) -> None:
        recommendation = self.hook_assistant.current_recommendation()
        if recommendation is None:
            return
        self._state = self._controller.add_recommendation_to_plan(self._state, recommendation)
        self._sync_ui()

    def _add_top_recommendations(self) -> None:
        self._state = self._controller.add_top_recommendations_to_plan(self._state)
        self._sync_ui()

    def _add_selected_custom_script(self) -> None:
        script = self.custom_scripts.current_script()
        if script is None:
            return
        self._state = self._controller.add_custom_script_to_plan(self._state, script)
        self._sync_ui()

    def _save_custom_script(self) -> None:
        self._state = self._controller.save_custom_script(
            self._state,
            self.custom_scripts.draft_name(),
            self.custom_scripts.draft_content(),
        )
        self._sync_ui()

    def _select_custom_script(self) -> None:
        self._state = self._controller.select_custom_script(
            self._state,
            self.custom_scripts.current_script(),
        )
        self._sync_ui()

    def _change_execution_mode(self, mode: str) -> None:
        self._state = self._controller.set_execution_mode(self._with_runtime_inputs(self._state), mode)

    def _runtime_inputs(self) -> tuple[str, str, str, str]:
        return (
            self.task_center.selected_device_serial(),
            self.task_center.selected_frida_server_binary(),
            self.task_center.selected_frida_server_remote_path(),
            self.task_center.selected_frida_session_seconds(),
        )

    def _with_runtime_inputs(self, state: WorkbenchState) -> WorkbenchState:
        device_serial, frida_server_binary, frida_server_remote_path, frida_session_seconds = self._runtime_inputs()
        return replace(
            state,
            device_serial=device_serial,
            frida_server_binary_path=frida_server_binary,
            frida_server_remote_path=frida_server_remote_path,
            frida_session_seconds=frida_session_seconds,
        )

    def _open_in_jadx(self) -> None:
        if not self._can_open_in_jadx():
            return
        jadx_gui_path = self._jadx_gui_path
        sample_path = self._state.sample_path
        if jadx_gui_path is None or sample_path is None:
            return
        try:
            self._jadx_launcher(jadx_gui_path, sample_path)
        except OSError as exc:
            self._state = replace(self._state, summary_text=f"Failed to open JADX: {exc}")
            self._sync_ui()

    def _sync_ui(self) -> None:
        current_method = self.method_index.current_method()
        self.task_center.set_job(self._state.current_job, self._state.sample_path)
        self.task_center.set_runtime_options(
            self._state.device_serial,
            self._state.frida_server_binary_path,
            self._state.frida_server_remote_path,
            self._state.frida_session_seconds,
        )
        self.task_center.set_environment(self._state.environment_snapshot)
        self.task_center.set_execution_presets(self._state.execution_preset_statuses)
        self.static_summary.set_static_inputs(self._state.static_inputs)
        self.method_index.set_methods(self._state.visible_methods, preferred_method=current_method)
        current_recommendation = self.hook_assistant.current_recommendation()
        self.hook_assistant.set_context(self._state.static_inputs)
        self.hook_assistant.set_recommendations(
            self._state.hook_recommendations,
            preferred_recommendation_id=(
                current_recommendation.recommendation_id if current_recommendation is not None else None
            ),
        )
        if self.method_index.search_input.text() != self._state.search_query:
            self.method_index.search_input.setText(self._state.search_query)
        self.script_plan.set_execution_presets(self._state.execution_preset_statuses, self._state.execution_mode)
        self.script_plan.set_plan(self._state.hook_plan)
        self.script_plan.set_execution_mode(self._state.execution_mode)
        self.custom_scripts.set_scripts(
            self._state.custom_scripts,
            preferred_script_path=(
                str(self._state.selected_custom_script_path)
                if self._state.selected_custom_script_path is not None
                else None
            ),
        )
        self.custom_scripts.set_draft(
            self._state.custom_script_draft_name,
            self._state.custom_script_draft_content,
        )
        self.execution_logs.set_events(self._state.hook_events)
        self.traffic_capture.set_capture(self._state.traffic_capture)
        self.results_summary.set_summary(
            self._state.summary_text,
            db_path=self._state.last_execution_db_path,
            bundle_path=self._state.last_execution_bundle_path,
            report_path=self._state.last_export_report_path,
        )
        self.open_jadx_action.setEnabled(self._can_open_in_jadx())
        self.export_report_action.setEnabled(self._state.current_job is not None and self._state.static_inputs is not None)

    def _can_open_in_jadx(self) -> bool:
        return bool(
            self._jadx_gui_path
            and self._jadx_gui_path.strip()
            and self._state.sample_path is not None
            and self._state.static_inputs is not None
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self._persist_ui_settings()
        super().closeEvent(event)
