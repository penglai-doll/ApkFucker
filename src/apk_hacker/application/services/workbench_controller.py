from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
import json
from pathlib import Path

from apk_hacker.application.services.custom_script_service import CustomScriptRecord, CustomScriptService
from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.execution_runtime import build_execution_backends
from apk_hacker.application.services.execution_presets import (
    EXECUTION_PRESETS,
    ExecutionPresetStatus,
    build_execution_preset_statuses,
    label_for_preset,
    resolve_real_device_backend,
)
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.report_export_service import ExportableReport, ReportExportService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from apk_hacker.domain.models.environment import EnvironmentSnapshot
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_advice import HookRecommendation
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.domain.services.hook_advisor import OfflineHookAdvisor
from apk_hacker.domain.services.hook_search import HookSearch
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.backend import ExecutionBackend, ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def _empty_method_index() -> MethodIndex:
    return MethodIndex(classes=(), methods=())


def _empty_hook_plan() -> HookPlan:
    return HookPlan(items=())


@dataclass(frozen=True, slots=True)
class NavigationPage:
    title: str
    object_name: str


@dataclass(frozen=True, slots=True)
class WorkbenchState:
    sample_path: Path | None = None
    current_job: AnalysisJob | None = None
    static_inputs: StaticInputs | None = None
    method_index: MethodIndex = field(default_factory=_empty_method_index)
    visible_methods: tuple[MethodIndexEntry, ...] = ()
    hook_recommendations: tuple[HookRecommendation, ...] = ()
    selected_sources: tuple[HookPlanSource, ...] = ()
    hook_plan: HookPlan = field(default_factory=_empty_hook_plan)
    hook_events: tuple[HookEvent, ...] = ()
    traffic_capture: TrafficCapture | None = None
    environment_snapshot: EnvironmentSnapshot | None = None
    execution_preset_statuses: tuple[ExecutionPresetStatus, ...] = ()
    custom_scripts: tuple[CustomScriptRecord, ...] = ()
    execution_mode: str = "fake_backend"
    device_serial: str = ""
    frida_server_binary_path: str = ""
    frida_server_remote_path: str = ""
    frida_session_seconds: str = ""
    selected_custom_script_path: Path | None = None
    custom_script_draft_name: str = ""
    custom_script_draft_content: str = ""
    search_query: str = ""
    run_count: int = 0
    last_execution_db_path: Path | None = None
    last_execution_bundle_path: Path | None = None
    last_export_report_path: Path | None = None
    summary_text: str = "No analysis run yet."


class WorkbenchController:
    def __init__(
        self,
        scripts_root: Path,
        db_root: Path,
        job_service: JobService | None = None,
        environment_service: EnvironmentService | None = None,
        fixture_root: Path | None = None,
        jadx_sources_root: Path | None = None,
        execution_backends: dict[str, ExecutionBackend] | None = None,
        execution_backend_env: Mapping[str, str] | None = None,
    ) -> None:
        self._fixture_root = fixture_root
        self._jadx_sources_root = jadx_sources_root
        self._scripts_root = scripts_root
        self._db_root = db_root
        self._analysis_output_root = db_root / "static-analysis"
        self._job_service = job_service or JobService()
        self._environment_service = environment_service or EnvironmentService()
        self._adapter = StaticAdapter()
        self._indexer = JavaMethodIndexer()
        self._hook_advisor = OfflineHookAdvisor()
        self._search = HookSearch()
        self._hook_plan_service = HookPlanService()
        self._traffic_capture_service = TrafficCaptureService()
        self._custom_scripts = CustomScriptService(scripts_root)
        self._report_export = ReportExportService()
        self._execution_backends = self._build_execution_backends_with_root(db_root, execution_backend_env)
        if execution_backends is not None:
            self._execution_backends.update(execution_backends)

    @property
    def db_root(self) -> Path:
        return self._db_root

    @property
    def demo_available(self) -> bool:
        return self._fixture_root is not None and self._jadx_sources_root is not None

    def _inspect_environment(self) -> tuple[EnvironmentSnapshot, tuple[ExecutionPresetStatus, ...]]:
        snapshot = self._environment_service.inspect()
        runtime_availability: dict[str, bool] = {}
        for preset in EXECUTION_PRESETS:
            backend = self._execution_backends.get(preset.key)
            if backend is None:
                runtime_availability[preset.key] = False
            elif isinstance(backend, RealExecutionBackend):
                runtime_availability[preset.key] = backend.configured
            else:
                runtime_availability[preset.key] = True
        statuses = build_execution_preset_statuses(snapshot, runtime_availability=runtime_availability)
        return snapshot, statuses

    @staticmethod
    def _build_execution_backends(extra_env: Mapping[str, str] | None = None) -> dict[str, ExecutionBackend]:
        return WorkbenchController._build_execution_backends_with_root(None, extra_env)

    @staticmethod
    def _build_execution_backends_with_root(
        db_root: Path | None,
        extra_env: Mapping[str, str] | None = None,
    ) -> dict[str, ExecutionBackend]:
        artifact_root = None if db_root is None else db_root / "execution-runs"
        return build_execution_backends(
            artifact_root=artifact_root,
            extra_env=extra_env,
        )

    def refresh_environment(self, state: WorkbenchState, announce: bool = True) -> WorkbenchState:
        snapshot, statuses = self._inspect_environment()
        if not announce:
            next_mode = state.execution_mode
            if not any(status.key == next_mode and status.available for status in statuses):
                next_mode = "fake_backend"
            return self._populate_custom_scripts(
                replace(
                    state,
                    environment_snapshot=snapshot,
                    execution_preset_statuses=statuses,
                    execution_mode=next_mode,
                )
            )
        return replace(
            state,
            environment_snapshot=snapshot,
            execution_preset_statuses=statuses,
            summary_text=f"Environment refreshed: {snapshot.summary}.",
        )

    def load_demo_workspace(self, sample_path: Path) -> WorkbenchState:
        if not self.demo_available:
            raise RuntimeError("Demo workspace is not configured.")
        analysis_report = json.loads(
            (self._fixture_root / "sample_analysis.json").read_text(encoding="utf-8")  # type: ignore[operator]
        )
        callback_config = json.loads(
            (self._fixture_root / "sample_callback-config.json").read_text(encoding="utf-8")  # type: ignore[operator]
        )
        job = self._job_service.create_job(sample_path)
        static_inputs = self._adapter.adapt(
            sample_path=sample_path,
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={
                "analysis_report": self._fixture_root / "sample_analysis.json",  # type: ignore[operator]
                "callback_config": self._fixture_root / "sample_callback-config.json",  # type: ignore[operator]
                "jadx_sources": self._jadx_sources_root,
            },
        )
        method_index = self._indexer.build(self._jadx_sources_root)  # type: ignore[arg-type]
        visible_methods = method_index.methods
        hook_recommendations = self._hook_advisor.recommend(static_inputs, method_index)
        snapshot, statuses = self._inspect_environment()

        return self._populate_custom_scripts(
            WorkbenchState(
                sample_path=sample_path,
                current_job=job,
                static_inputs=static_inputs,
                method_index=method_index,
                visible_methods=visible_methods,
                hook_recommendations=hook_recommendations,
                environment_snapshot=snapshot,
                execution_preset_statuses=statuses,
                summary_text=f"Loaded demo workspace for {sample_path.name}.",
            )
        )

    def load_sample_workspace(self, sample_path: Path) -> WorkbenchState:
        job, static_inputs, method_index = self._job_service.load_static_workspace(
            sample_path,
            output_dir=self._analysis_output_root,
        )
        hook_recommendations = self._hook_advisor.recommend(static_inputs, method_index)
        snapshot, statuses = self._inspect_environment()
        return self._populate_custom_scripts(
            WorkbenchState(
                sample_path=sample_path,
                current_job=job,
                static_inputs=static_inputs,
                method_index=method_index,
                visible_methods=method_index.methods,
                hook_recommendations=hook_recommendations,
                environment_snapshot=snapshot,
                execution_preset_statuses=statuses,
                summary_text=f"Static analysis finished for {sample_path.name}.",
            )
        )

    def search_methods(self, state: WorkbenchState, query: str) -> WorkbenchState:
        normalized_query = query.strip()
        visible_methods = self._search.search(state.method_index, normalized_query)
        return replace(state, search_query=normalized_query, visible_methods=visible_methods)

    def add_method_to_plan(self, state: WorkbenchState, method: MethodIndexEntry) -> WorkbenchState:
        return self._add_source_to_plan(state, HookPlanSource.from_method(method))

    def add_recommendation_to_plan(self, state: WorkbenchState, recommendation: HookRecommendation) -> WorkbenchState:
        if recommendation.kind == "template_hook":
            if recommendation.template_id is None or recommendation.template_name is None or recommendation.plugin_id is None:
                return replace(state, summary_text="The selected template recommendation is incomplete.")
            source = HookPlanSource.from_template(
                template_id=recommendation.template_id,
                template_name=recommendation.template_name,
                plugin_id=recommendation.plugin_id,
                reason=recommendation.reason,
                matched_terms=recommendation.matched_terms,
                source_signals=recommendation.source_signals,
                template_event_types=recommendation.template_event_types,
                template_category=recommendation.template_category,
                requires_root=recommendation.requires_root,
                supports_offline=recommendation.supports_offline,
            )
            return self._add_source_to_plan(state, source)
        if recommendation.method is None:
            return replace(state, summary_text="The selected recommendation is advisory only.")
        return self._add_source_to_plan(
            state,
            HookPlanSource.from_method(
                recommendation.method,
                source_kind="offline_recommendation",
                reason=recommendation.reason,
                matched_terms=recommendation.matched_terms,
                source_signals=recommendation.source_signals,
            ),
        )

    def add_top_recommendations_to_plan(self, state: WorkbenchState, limit: int = 3) -> WorkbenchState:
        next_state = state
        added = 0
        for recommendation in state.hook_recommendations[:limit]:
            if recommendation.method is None:
                continue
            before = len(next_state.selected_sources)
            next_state = self.add_method_to_plan(next_state, recommendation.method)
            if len(next_state.selected_sources) > before:
                added += 1
        if added == 0:
            return replace(next_state, summary_text="No new recommendations were added to the plan.")
        return replace(next_state, summary_text=f"Added {added} recommended hook(s) to the plan.")

    def add_custom_script_to_plan(self, state: WorkbenchState, script: CustomScriptRecord) -> WorkbenchState:
        source = HookPlanSource.from_custom_script(script.name, str(script.script_path))
        duplicate_message = f"Custom script {script.name} is already in the hook plan."
        return self._add_source_to_plan(state, source, duplicate_message=duplicate_message)

    def select_custom_script(self, state: WorkbenchState, script: CustomScriptRecord | None) -> WorkbenchState:
        if script is None:
            return replace(
                state,
                selected_custom_script_path=None,
                custom_script_draft_name="",
                custom_script_draft_content="",
            )
        return replace(
            state,
            selected_custom_script_path=script.script_path,
            custom_script_draft_name=script.name,
            custom_script_draft_content=self._custom_scripts.read_script(script),
        )

    def save_custom_script(self, state: WorkbenchState, name: str, content: str) -> WorkbenchState:
        try:
            record = self._custom_scripts.save_script(name, content)
        except (OSError, ValueError) as exc:
            return replace(state, summary_text=f"Failed to save custom script: {exc}")
        custom_scripts = tuple(self._custom_scripts.discover())
        return replace(
            state,
            custom_scripts=custom_scripts,
            selected_custom_script_path=record.script_path,
            custom_script_draft_name=record.name,
            custom_script_draft_content=content,
            summary_text=f"Saved custom script {record.name}.",
        )

    def _populate_custom_scripts(self, state: WorkbenchState) -> WorkbenchState:
        custom_scripts = tuple(self._custom_scripts.discover())
        if not custom_scripts:
            return replace(
                state,
                custom_scripts=(),
                selected_custom_script_path=None,
                custom_script_draft_name=state.custom_script_draft_name,
                custom_script_draft_content=state.custom_script_draft_content,
            )
        selected_script = None
        if state.selected_custom_script_path is not None:
            for script in custom_scripts:
                if script.script_path == state.selected_custom_script_path:
                    selected_script = script
                    break
        if selected_script is None:
            selected_script = custom_scripts[0]
        draft_name = state.custom_script_draft_name or selected_script.name
        draft_content = state.custom_script_draft_content or self._custom_scripts.read_script(selected_script)
        return replace(
            state,
            custom_scripts=custom_scripts,
            selected_custom_script_path=selected_script.script_path,
            custom_script_draft_name=draft_name,
            custom_script_draft_content=draft_content,
        )

    def set_execution_mode(self, state: WorkbenchState, mode: str) -> WorkbenchState:
        if state.execution_preset_statuses and not any(
            status.key == mode and status.available for status in state.execution_preset_statuses
        ):
            return replace(state, summary_text=f"Execution mode {mode} is not ready on this machine.")
        return replace(state, execution_mode=mode)

    def run_analysis(self, state: WorkbenchState) -> WorkbenchState:
        if state.current_job is None:
            return replace(state, summary_text="Load a workspace before running analysis.")
        if not state.hook_plan.items:
            return replace(state, summary_text="Add at least one hook plan item first.")
        backend_key = self._resolve_execution_backend_key(state)
        backend = self._execution_backends.get(backend_key)
        if backend is None:
            return replace(state, hook_events=(), summary_text=f"Execution mode {backend_key} is not available in this build.")
        request = self._build_execution_request(state)
        try:
            events = backend.execute(request)
        except ExecutionBackendUnavailable as exc:
            return replace(
                state,
                hook_events=(),
                last_execution_db_path=None,
                last_execution_bundle_path=None,
                summary_text=str(exc),
            )
        return self._persist_execution(state, events, executed_backend_key=backend_key)

    def load_traffic_capture(self, state: WorkbenchState, har_path: Path) -> WorkbenchState:
        if state.static_inputs is None:
            return replace(state, summary_text="Load a workspace before importing HAR capture.")
        try:
            capture = self._traffic_capture_service.load_har(har_path, state.static_inputs)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return replace(state, summary_text=f"Failed to load HAR capture: {exc}")
        return replace(
            state,
            traffic_capture=capture,
            summary_text=(
                f"Loaded {capture.flow_count} flow(s) from {capture.source_path.name}; "
                f"{capture.suspicious_count} suspicious flow(s) matched callback indicators."
            ),
        )

    def run_fake_analysis(self, state: WorkbenchState) -> WorkbenchState:
        if state.current_job is None:
            return replace(state, summary_text="Load a workspace before running fake analysis.")
        if not state.hook_plan.items:
            return replace(state, summary_text="Add at least one hook plan item first.")
        events = self._execution_backends["fake_backend"].execute(self._build_execution_request(state))
        return self._persist_execution(state, events, executed_backend_key="fake_backend")

    def export_report(self, state: WorkbenchState) -> WorkbenchState:
        if state.current_job is None or state.static_inputs is None:
            return replace(state, summary_text="Load a workspace before exporting a report.")
        report_root = self._db_root / "reports"
        report_path = report_root / f"{state.current_job.job_id}-report.md"
        exportable = ExportableReport(
            job_id=state.current_job.job_id,
            summary_text=state.summary_text,
            sample_path=state.sample_path,
            static_inputs=state.static_inputs,
            hook_plan=state.hook_plan,
            hook_events=state.hook_events,
            traffic_capture=state.traffic_capture,
            last_execution_db_path=state.last_execution_db_path,
            last_execution_bundle_path=state.last_execution_bundle_path,
        )
        try:
            exported_path = self._report_export.export_markdown(exportable, report_path)
        except OSError as exc:
            return replace(state, last_export_report_path=None, summary_text=f"Failed to export report: {exc}")
        return replace(
            state,
            last_export_report_path=exported_path,
            summary_text=f"Exported report to {exported_path}.",
        )

    def _resolve_execution_backend_key(self, state: WorkbenchState) -> str:
        if state.execution_mode != "real_device":
            return state.execution_mode
        backend = self._execution_backends.get("real_device")
        if isinstance(backend, RealExecutionBackend) and backend.configured:
            return "real_device"
        recommended = resolve_real_device_backend(state.execution_preset_statuses)
        return recommended or "real_device"

    @staticmethod
    def _build_execution_request(state: WorkbenchState) -> ExecutionRequest:
        if state.current_job is None:
            raise RuntimeError("Execution request requires a current job.")
        runtime_env: dict[str, str] = {}
        if state.device_serial:
            runtime_env["APKHACKER_DEVICE_SERIAL"] = state.device_serial
        if state.frida_server_binary_path:
            runtime_env["APKHACKER_FRIDA_SERVER_BINARY"] = state.frida_server_binary_path
        if state.frida_server_remote_path:
            runtime_env["APKHACKER_FRIDA_SERVER_REMOTE_PATH"] = state.frida_server_remote_path
        if state.frida_session_seconds:
            runtime_env["APKHACKER_FRIDA_SESSION_SECONDS"] = state.frida_session_seconds
        return ExecutionRequest(
            job_id=state.current_job.job_id,
            plan=state.hook_plan,
            package_name=state.static_inputs.package_name if state.static_inputs is not None else None,
            sample_path=state.sample_path,
            runtime_env=runtime_env,
        )

    def _persist_execution(
        self,
        state: WorkbenchState,
        events: tuple[HookEvent, ...],
        executed_backend_key: str,
    ) -> WorkbenchState:
        if state.current_job is None:
            return state
        run_count = state.run_count + 1
        db_path = self._db_root / f"{state.current_job.job_id}-run-{run_count}.sqlite3"
        store = HookLogStore(db_path)
        bundle_path = None
        persisted_events: list[HookEvent] = []
        for event in events:
            if event.event_type == "execution_bundle":
                if event.arguments:
                    bundle_path = Path(event.arguments[0])
                continue
            persisted_events.append(event)
        for event in persisted_events:
            store.insert(replace(event, job_id=state.current_job.job_id))
        rows = tuple(store.list_for_job(state.current_job.job_id))
        requested_label = label_for_preset(state.execution_mode)
        executed_label = label_for_preset(executed_backend_key)
        execution_detail = executed_label if state.execution_mode == executed_backend_key else f"{requested_label} -> {executed_label}"
        return replace(
            state,
            hook_events=rows,
            run_count=run_count,
            last_execution_db_path=db_path,
            last_execution_bundle_path=bundle_path,
            summary_text=(
                f"Captured {len(rows)} event(s) from {len(state.hook_plan.items)} planned hook(s) "
                f"via {execution_detail}."
            ),
        )

    def _add_source_to_plan(
        self,
        state: WorkbenchState,
        source: HookPlanSource,
        duplicate_message: str | None = None,
    ) -> WorkbenchState:
        if any(existing.source_id == source.source_id for existing in state.selected_sources):
            if duplicate_message is not None:
                return replace(state, summary_text=duplicate_message)
            return state
        selected_sources = (*state.selected_sources, source)
        hook_plan = self._hook_plan_service.plan_for_sources(list(selected_sources))
        return replace(
            state,
            selected_sources=selected_sources,
            hook_plan=hook_plan,
            summary_text=f"Prepared {len(hook_plan.items)} planned hook item(s).",
        )
