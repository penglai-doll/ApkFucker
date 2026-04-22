from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Event

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.execution_runtime import build_execution_backend_env
from apk_hacker.application.services.execution_runtime import build_execution_backend
from apk_hacker.application.services.execution_runtime import build_execution_runtime_availability
from apk_hacker.application.services.execution_runtime import ExecutionRouting
from apk_hacker.application.services.execution_runtime import resolve_execution_routing
from apk_hacker.application.services.execution_presets import build_execution_preset_statuses
from apk_hacker.application.services.execution_presets import label_for_preset
from apk_hacker.application.services.device_inventory_service import DeviceInventoryService
from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.environment_service import resolve_ssl_hook_template
from apk_hacker.application.services.custom_script_service import CustomScriptRecord
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.traffic_capture_service import LIVE_CAPTURE_PROVENANCE_KIND
from apk_hacker.application.services.traffic_capture_service import MANUAL_HAR_PROVENANCE_KIND
from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from apk_hacker.application.services.workspace_hook_plan_service import WorkspaceHookPlanService
from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.application.services.workspace_report_service import ReportExportResult
from apk_hacker.application.services.workspace_report_service import WorkspaceReportService
from apk_hacker.application.services.workspace_state_service import WorkspaceStateService
from apk_hacker.application.services.workspace_traffic_service import WorkspaceTrafficService
from apk_hacker.application.services.workspace_runtime_state import ExecutionHistoryEntry
from apk_hacker.application.services.workspace_runtime_state import normalize_path
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.execution import ExecutionRuntimeOptions
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.domain.models.traffic import TrafficCaptureSummary
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState
from apk_hacker.infrastructure.execution.backend import ExecutionCancelled
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def _build_runtime_env(runtime_options: ExecutionRuntimeOptions | None) -> dict[str, str]:
    if runtime_options is None:
        return {}

    frida_server_binary = runtime_options.frida_server_binary_path.strip()
    frida_server_remote_path = runtime_options.frida_server_remote_path.strip()
    frida_session_seconds = runtime_options.frida_session_seconds.strip()
    parsed_session_seconds: float | None = None
    if frida_session_seconds:
        parsed_session_seconds = float(frida_session_seconds)

    return build_execution_backend_env(
        device_serial=runtime_options.device_serial.strip() or None,
        frida_server_binary=Path(frida_server_binary).expanduser() if frida_server_binary else None,
        frida_server_remote_path=frida_server_remote_path or None,
        frida_session_seconds=parsed_session_seconds,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True, slots=True)
class ExecutionResult:
    state: WorkspaceRuntimeState
    execution_mode: str
    executed_backend_key: str
    run_id: str
    event_count: int
    db_path: Path
    bundle_path: Path
    executed_backend_label: str
    events: tuple[HookEvent, ...]


@dataclass(frozen=True, slots=True)
class ExecutionPreflightResult:
    case_id: str
    ready: bool
    execution_mode: str
    executed_backend_key: str | None
    executed_backend_label: str | None
    detail: str


class WorkspaceRuntimeService:
    def __init__(
        self,
        *,
        registry_service: WorkspaceRegistryService,
        default_workspace_root: Path,
        inspection_service: WorkspaceInspectionService,
        custom_script_service: CustomScriptService | None = None,
        hook_plan_service: HookPlanService | None = None,
        report_export_service: ReportExportService | None = None,
        traffic_capture_service: TrafficCaptureService | None = None,
        case_queue_service: CaseQueueService | None = None,
        execution_backend_env: Mapping[str, str] | None = None,
        real_device_command: str | None = None,
        environment_service: EnvironmentService | None = None,
        device_inventory_service: DeviceInventoryService | None = None,
        workspace_state_service: WorkspaceStateService | None = None,
        workspace_hook_plan_service: WorkspaceHookPlanService | None = None,
        workspace_traffic_service: WorkspaceTrafficService | None = None,
        workspace_report_service: WorkspaceReportService | None = None,
    ) -> None:
        self._registry_service = registry_service
        self._default_workspace_root = default_workspace_root
        self._inspection_service = inspection_service
        self._custom_scripts_base_root = (
            custom_script_service.scripts_root if custom_script_service is not None else None
        )
        self._hook_plan_service = hook_plan_service or HookPlanService()
        resolved_report_export_service = report_export_service or ReportExportService()
        self._traffic_capture_service = traffic_capture_service or TrafficCaptureService()
        self._case_queue_service = case_queue_service or CaseQueueService()
        self._execution_backend_env = dict(execution_backend_env or {})
        self._real_device_command = real_device_command
        self._environment_service = environment_service or EnvironmentService()
        self._device_inventory_service = device_inventory_service or DeviceInventoryService()
        self._workspace_state_service = workspace_state_service or WorkspaceStateService(self._hook_plan_service)
        self._workspace_hook_plan_service = workspace_hook_plan_service or WorkspaceHookPlanService(
            hook_plan_service=self._hook_plan_service,
        )
        self._workspace_traffic_service = workspace_traffic_service or WorkspaceTrafficService(
            traffic_capture_service=self._traffic_capture_service,
        )
        self._workspace_report_service = workspace_report_service or WorkspaceReportService(
            report_export_service=resolved_report_export_service,
        )

    def get_state(self, case_id: str) -> WorkspaceRuntimeState:
        record = self._inspection_service.get_detail(case_id)
        return self._load_state(record)

    def list_custom_scripts(self, case_id: str) -> tuple[CustomScriptRecord, ...]:
        record = self._inspection_service.get_detail(case_id)
        return self._custom_script_service_for(record.workspace_root).discover_records()

    def get_traffic_capture(self, case_id: str) -> TrafficCapture | None:
        self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        return self._workspace_traffic_service.get_capture(state)

    def get_live_traffic_capture_state(self, case_id: str) -> TrafficLiveCaptureState:
        return self._workspace_traffic_service.get_live_capture_state(self._load_runtime_state_for(case_id))

    def save_live_traffic_capture_state(
        self,
        case_id: str,
        live_capture: TrafficLiveCaptureState,
    ) -> WorkspaceRuntimeState:
        state = self._load_runtime_state_for(case_id)
        return self._save_state(self._workspace_traffic_service.save_live_capture_state(state, live_capture))

    def build_live_traffic_capture_output_path(self, case_id: str, session_id: str) -> Path:
        workspace_root = self._locate_workspace_root(case_id)
        return self._workspace_traffic_service.build_live_capture_output_path(workspace_root, session_id)

    def get_execution_history(self, case_id: str, limit: int = 20) -> tuple[ExecutionHistoryEntry, ...]:
        state = self.get_state(case_id)
        bounded_limit = max(1, min(limit, 200))
        return tuple(reversed(state.execution_history[-bounded_limit:]))

    def build_execution_preflight(
        self,
        case_id: str,
        execution_mode: str | None = None,
        runtime_options: ExecutionRuntimeOptions | None = None,
    ) -> ExecutionPreflightResult:
        resolved_mode = execution_mode or "fake_backend"
        executed_backend_key: str | None = None
        executed_backend_label: str | None = None
        try:
            routing = self.resolve_execution_routing(resolved_mode)
            executed_backend_key = routing.executed_backend_key
            executed_backend_label = routing.executed_backend_label
        except ValueError:
            executed_backend_key = resolved_mode
            executed_backend_label = label_for_preset(resolved_mode)

        try:
            self.validate_execution_ready(
                case_id,
                execution_mode=resolved_mode,
                runtime_options=runtime_options,
            )
        except ValueError as exc:
            return ExecutionPreflightResult(
                case_id=case_id,
                ready=False,
                execution_mode=resolved_mode,
                executed_backend_key=executed_backend_key,
                executed_backend_label=executed_backend_label,
                detail=str(exc),
            )

        return ExecutionPreflightResult(
            case_id=case_id,
            ready=True,
            execution_mode=resolved_mode,
            executed_backend_key=executed_backend_key,
            executed_backend_label=executed_backend_label,
            detail="ready",
        )

    def import_traffic_capture(
        self,
        case_id: str,
        har_path: str,
        *,
        provenance_kind: str = MANUAL_HAR_PROVENANCE_KIND,
    ) -> TrafficCapture:
        record = self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        updated_state, capture = self._workspace_traffic_service.import_har(
            state,
            Path(har_path),
            record.bundle.static_inputs,
            provenance_kind=provenance_kind,
        )
        self._save_state(updated_state)
        return capture

    def save_custom_script(self, case_id: str, name: str, content: str) -> CustomScriptRecord:
        record = self._inspection_service.get_detail(case_id)
        saved = self._custom_script_service_for(record.workspace_root).save_script(name, content)
        state = self.get_state(case_id)
        updated_state = self._workspace_hook_plan_service.rerender_if_source_selected(
            state,
            source_path=str(saved.script_path),
        )
        if updated_state != state:
            self._save_state(updated_state)
        return saved

    def get_custom_script(self, case_id: str, script_id: str) -> tuple[CustomScriptRecord, str]:
        record = self._inspection_service.get_detail(case_id)
        service = self._custom_script_service_for(record.workspace_root)
        document = service.read_script_document(script_id)
        return document.record, document.content

    def update_custom_script(
        self,
        case_id: str,
        script_id: str,
        *,
        name: str,
        content: str,
    ) -> CustomScriptRecord:
        record = self._inspection_service.get_detail(case_id)
        service = self._custom_script_service_for(record.workspace_root)
        state = self.get_state(case_id)
        original = service.get_record(script_id)
        updated = service.update_script(script_id, name, content)
        updated_state = self._workspace_hook_plan_service.replace_custom_script_source(
            state,
            old_script_path=str(original.script_path),
            new_script_name=updated.name,
            new_script_path=str(updated.script_path),
        )
        if updated_state != state:
            self._save_state(updated_state)
        return updated

    def delete_custom_script(self, case_id: str, script_id: str) -> tuple[CustomScriptRecord, WorkspaceRuntimeState]:
        record = self._inspection_service.get_detail(case_id)
        service = self._custom_script_service_for(record.workspace_root)
        state = self.get_state(case_id)
        deleted = service.delete_script(script_id)
        return deleted, self._save_state(
            self._workspace_hook_plan_service.remove_custom_script_source(
                state,
                script_path=str(deleted.script_path),
            )
        )

    def add_method_to_plan(self, case_id: str, method: MethodIndexEntry) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        return self._save_state(self._workspace_hook_plan_service.add_method_source(state, method))

    def add_recommendation_to_plan(self, case_id: str, recommendation_id: str) -> WorkspaceRuntimeState:
        record = self._inspection_service.get_detail(case_id)
        recommendation = next(
            (
                item
                for item in self._inspection_service.get_recommendations(case_id, limit=100)
                if item.recommendation_id == recommendation_id
            ),
            None,
        )
        if recommendation is None:
            raise KeyError(recommendation_id)
        if recommendation.kind == "template_hook":
            if recommendation.template_id is None or recommendation.template_name is None or recommendation.plugin_id is None:
                raise ValueError("Template recommendation is incomplete.")
            source = HookPlanSource.from_template(
                template_id=recommendation.template_id,
                template_name=recommendation.template_name,
                plugin_id=recommendation.plugin_id,
            )
            return self._mutate_selected_sources(record.case_id, source)
        if recommendation.method is None:
            raise ValueError("Recommendation does not reference a method.")
        return self._mutate_selected_sources(record.case_id, HookPlanSource.from_method(recommendation.method))

    def add_custom_script_to_plan(self, case_id: str, script_id: str) -> WorkspaceRuntimeState:
        record = self._inspection_service.get_detail(case_id)
        script = next((item for item in record.custom_scripts if item.script_id == script_id), None)
        if script is None:
            raise KeyError(script_id)
        return self._mutate_selected_sources(
            record.case_id,
            HookPlanSource.from_custom_script(script.name, str(script.script_path)),
        )

    def add_template_to_plan(
        self,
        case_id: str,
        *,
        template_id: str,
        template_name: str,
        plugin_id: str,
    ) -> WorkspaceRuntimeState:
        record = self._inspection_service.get_detail(case_id)
        template = resolve_ssl_hook_template(template_id=template_id, plugin_id=plugin_id)
        if template is None:
            raise ValueError("Template is not available.")
        if template.template_name != template_name:
            raise ValueError("Template metadata does not match the available template.")
        source = HookPlanSource.from_template(
            template_id=template.template_id,
            template_name=template.template_name,
            plugin_id=template.plugin_id,
        )
        return self._mutate_selected_sources(record.case_id, source)

    def remove_hook_plan_item(self, case_id: str, item_id: str) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        return self._save_state(self._workspace_hook_plan_service.remove_item(state, item_id))

    def clear_hook_plan(self, case_id: str) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        return self._save_state(self._workspace_hook_plan_service.clear(state))

    def update_hook_plan_item(
        self,
        case_id: str,
        item_id: str,
        *,
        enabled: bool | None = None,
        inject_order: int | None = None,
    ) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        return self._save_state(
            self._workspace_hook_plan_service.update_item(
                state,
                item_id,
                enabled=enabled,
                inject_order=inject_order,
            )
        )

    def get_execution_events(
        self,
        case_id: str,
        limit: int = 20,
        *,
        history_id: str | None = None,
    ) -> tuple[HookEvent, ...]:
        record = self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        db_path = state.last_execution_db_path
        if history_id is not None:
            matched = next((entry for entry in state.execution_history if entry.history_id == history_id), None)
            if matched is None:
                raise KeyError(history_id)
            db_path = matched.db_path
        if db_path is None or not db_path.exists():
            return ()
        bounded_limit = max(1, min(limit, 200))
        return tuple(HookLogStore(db_path).list_tail_for_job(record.bundle.job.job_id, bounded_limit))

    def mark_execution_started(
        self,
        case_id: str,
        execution_mode: str | None = None,
        *,
        executed_backend_key: str | None = None,
        stage: str = "queued",
    ) -> WorkspaceRuntimeState:
        state = self.validate_execution_ready(case_id, execution_mode=execution_mode)
        resolved_mode = execution_mode or "fake_backend"
        history_id = f"exec-{len(state.execution_history) + 1}"
        now = _now_iso()
        history_entry = ExecutionHistoryEntry(
            history_id=history_id,
            execution_mode=resolved_mode,
            executed_backend_key=executed_backend_key or resolved_mode,
            status="started",
            stage=stage,
            started_at=now,
            updated_at=now,
        )
        return self._save_state(
            replace(
                state,
                current_execution_history_id=history_id,
                execution_history=(*state.execution_history, history_entry),
                last_execution_mode=resolved_mode,
                last_executed_backend_key=executed_backend_key or resolved_mode,
                last_execution_status="started",
                last_execution_stage=stage,
                last_execution_error_code=None,
                last_execution_error_message=None,
                last_execution_event_count=None,
            )
        )

    def mark_execution_progress(
        self,
        case_id: str,
        *,
        execution_mode: str | None = None,
        executed_backend_key: str | None = None,
        status: str = "started",
        stage: str,
    ) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        resolved_mode = execution_mode or state.last_execution_mode or "fake_backend"
        state = self._replace_current_execution_history(
            state,
            execution_mode=resolved_mode,
            executed_backend_key=executed_backend_key or state.last_executed_backend_key or resolved_mode,
            status=status,
            stage=stage,
            error_code=None,
            error_message=None,
        )
        return self._save_state(
            replace(
                state,
                last_execution_mode=resolved_mode,
                last_executed_backend_key=executed_backend_key or state.last_executed_backend_key or resolved_mode,
                last_execution_status=status,
                last_execution_stage=stage,
                last_execution_error_code=None,
                last_execution_error_message=None,
            )
        )

    def mark_execution_failed(
        self,
        case_id: str,
        execution_mode: str | None = None,
        *,
        executed_backend_key: str | None = None,
        stage: str = "failed",
        error_code: str | None = None,
        message: str | None = None,
    ) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        resolved_mode = execution_mode or state.last_execution_mode or "fake_backend"
        state = self._replace_current_execution_history(
            state,
            execution_mode=resolved_mode,
            executed_backend_key=executed_backend_key or state.last_executed_backend_key or resolved_mode,
            status="error",
            stage=stage,
            error_code=error_code,
            error_message=message,
            clear_current=True,
        )
        return self._save_state(
            replace(
                state,
                last_execution_mode=resolved_mode,
                last_executed_backend_key=executed_backend_key or state.last_executed_backend_key or resolved_mode,
                last_execution_status="error",
                last_execution_stage=stage,
                last_execution_error_code=error_code,
                last_execution_error_message=message,
            )
        )

    def mark_execution_cancelled(
        self,
        case_id: str,
        execution_mode: str | None = None,
        *,
        executed_backend_key: str | None = None,
    ) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        resolved_mode = execution_mode or state.last_execution_mode or "fake_backend"
        state = self._replace_current_execution_history(
            state,
            execution_mode=resolved_mode,
            executed_backend_key=executed_backend_key or state.last_executed_backend_key or resolved_mode,
            status="cancelled",
            stage="cancelled",
            error_code=None,
            error_message=None,
            clear_current=True,
        )
        return self._save_state(
            replace(
                state,
                last_execution_mode=resolved_mode,
                last_executed_backend_key=executed_backend_key or state.last_executed_backend_key or resolved_mode,
                last_execution_status="cancelled",
                last_execution_stage="cancelled",
                last_execution_error_code=None,
                last_execution_error_message=None,
            )
        )

    def mark_execution_completed(
        self,
        case_id: str,
        *,
        run_index: int,
        run_id: str,
        execution_mode: str,
        executed_backend_key: str,
        event_count: int,
        db_path: Path,
        bundle_path: Path,
    ) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        state = self._replace_current_execution_history(
            state,
            run_id=run_id,
            execution_mode=execution_mode,
            executed_backend_key=executed_backend_key,
            status="completed",
            stage="completed",
            error_code=None,
            error_message=None,
            event_count=event_count,
            db_path=db_path,
            bundle_path=bundle_path,
            clear_current=True,
        )
        return self._save_state(
            replace(
                state,
                execution_count=run_index,
                last_execution_run_id=run_id,
                last_execution_mode=execution_mode,
                last_executed_backend_key=executed_backend_key,
                last_execution_status="completed",
                last_execution_stage="completed",
                last_execution_error_code=None,
                last_execution_error_message=None,
                last_execution_event_count=event_count,
                last_execution_result_path=bundle_path,
                last_execution_db_path=db_path,
                last_execution_bundle_path=bundle_path,
            )
        )

    def resolve_execution_routing(self, execution_mode: str | None = None) -> ExecutionRouting:
        requested_mode = execution_mode or "fake_backend"
        runtime_availability = build_execution_runtime_availability(
            extra_env=self._execution_backend_env,
            real_device_command=self._real_device_command,
        )
        snapshot = self._environment_service.inspect()
        return resolve_execution_routing(
            requested_mode,
            snapshot=snapshot,
            runtime_availability=runtime_availability,
        )

    def execute_current_plan(
        self,
        case_id: str,
        execution_mode: str | None = None,
        *,
        executed_backend_key: str | None = None,
        runtime_options: ExecutionRuntimeOptions | None = None,
        cancellation_event: Event | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ExecutionResult:
        record = self._inspection_service.get_detail(case_id)
        state = self.validate_execution_ready(case_id, execution_mode=execution_mode)
        resolved_mode = execution_mode or "fake_backend"
        routing = self.resolve_execution_routing(resolved_mode)
        resolved_backend_key = executed_backend_key or routing.executed_backend_key
        run_index = state.execution_count + 1
        run_id = f"run-{run_index}"
        bundle_path = record.workspace_root / "executions" / run_id
        bundle_path.mkdir(parents=True, exist_ok=True)
        runtime_env = _build_runtime_env(runtime_options)
        backend_env = dict(self._execution_backend_env)
        backend_env.update(runtime_env)

        backend = build_execution_backend(
            resolved_backend_key,
            artifact_root=bundle_path,
            extra_env=backend_env,
            real_device_command=self._real_device_command,
        )

        if progress_callback is not None:
            progress_callback("executing")
        request = ExecutionRequest(
            job_id=record.bundle.job.job_id,
            plan=state.rendered_hook_plan,
            package_name=record.bundle.static_inputs.package_name,
            sample_path=record.sample_path,
            runtime_env=runtime_env,
            cancellation_event=cancellation_event,
        )
        events = backend.execute(request)
        if cancellation_event is not None and cancellation_event.is_set():
            raise ExecutionCancelled("Execution was cancelled by the user.")

        bundle_from_backend = next(
            (
                _normalize_path(event.arguments[0])
                for event in events
                if event.event_type == "execution_bundle" and event.arguments
            ),
            None,
        )
        if bundle_from_backend is not None:
            bundle_path = bundle_from_backend
            bundle_path.mkdir(parents=True, exist_ok=True)

        db_path = bundle_path / "hook-events.sqlite3"
        if progress_callback is not None:
            progress_callback("persisting")
        store = HookLogStore(db_path)
        persisted_events: list[HookEvent] = []
        for event in events:
            if event.event_type == "execution_bundle":
                continue
            persisted_events.append(event)
        for event in persisted_events:
            store.insert(replace(event, job_id=record.bundle.job.job_id))
        runtime_state = self.mark_execution_completed(
            case_id,
            run_index=run_index,
            run_id=run_id,
            execution_mode=resolved_mode,
            executed_backend_key=resolved_backend_key,
            event_count=len(persisted_events),
            db_path=db_path,
            bundle_path=bundle_path,
        )
        return ExecutionResult(
            state=runtime_state,
            execution_mode=resolved_mode,
            executed_backend_key=resolved_backend_key,
            run_id=run_id,
            event_count=len(persisted_events),
            db_path=db_path,
            bundle_path=bundle_path,
            executed_backend_label=label_for_preset(resolved_backend_key),
            events=tuple(persisted_events),
        )

    def export_report(self, case_id: str) -> ReportExportResult:
        record = self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        traffic_capture = self.get_traffic_capture(case_id)
        result = self._workspace_report_service.export(
            record,
            state,
            traffic_capture=traffic_capture,
        )
        return replace(result, state=self._save_state(result.state))

    def validate_execution_ready(
        self,
        case_id: str,
        execution_mode: str | None = None,
        runtime_options: ExecutionRuntimeOptions | None = None,
    ) -> WorkspaceRuntimeState:
        self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        if not state.rendered_hook_plan.items:
            raise ValueError("Add at least one hook plan item first.")
        resolved_mode = execution_mode or "fake_backend"
        if resolved_mode != "fake_backend" and not resolved_mode.startswith("real_"):
            raise ValueError(f"Unsupported execution mode: {resolved_mode}")
        if resolved_mode != "fake_backend" and runtime_options is not None:
            frida_server_binary_path = runtime_options.frida_server_binary_path.strip()
            if frida_server_binary_path:
                binary_path = Path(frida_server_binary_path).expanduser()
                if not binary_path.exists():
                    raise ValueError("Frida server binary path does not exist.")
            frida_session_seconds = runtime_options.frida_session_seconds.strip()
            if frida_session_seconds:
                try:
                    parsed_seconds = float(frida_session_seconds)
                except ValueError as exc:
                    raise ValueError("Frida session seconds must be a valid number.") from exc
                if parsed_seconds <= 0:
                    raise ValueError("Frida session seconds must be greater than zero.")
        runtime_availability = build_execution_runtime_availability(
            extra_env=self._execution_backend_env,
            real_device_command=self._real_device_command,
        )
        preset_statuses = build_execution_preset_statuses(
            self._environment_service.inspect(),
            runtime_availability=runtime_availability,
        )
        status_by_key = {status.key: status for status in preset_statuses}
        preset_status = status_by_key.get(resolved_mode)
        if preset_status is not None and not preset_status.available:
            raise ValueError(f"Execution preset unavailable: {preset_status.detail}")

        if resolved_mode == "fake_backend":
            return state

        record = self._inspection_service.get_detail(case_id)
        routing = self.resolve_execution_routing(resolved_mode)
        device_snapshot = self._device_inventory_service.inspect(
            package_name=record.bundle.static_inputs.package_name,
        )
        available_devices = [device for device in device_snapshot.devices if device.available]
        if not available_devices:
            raise ValueError("未发现已连接 Android 设备。")

        requested_serial = runtime_options.device_serial.strip() if runtime_options is not None else ""
        selected_device = None
        if requested_serial:
            selected_device = next((device for device in available_devices if device.serial == requested_serial), None)
            if selected_device is None:
                raise ValueError(f"所选设备未连接：{requested_serial}")
        elif len(available_devices) == 1:
            selected_device = available_devices[0]
        else:
            raise ValueError("检测到多个已连接设备，请先选择目标设备。")

        if routing.executed_backend_key in {"real_frida_probe", "real_frida_inject"} and not selected_device.frida_visible:
            raise ValueError("所选设备当前未被 Frida 识别，请先启动 frida-server。")
        if routing.executed_backend_key == "real_frida_session":
            has_bootstrap_binary = bool(runtime_options and runtime_options.frida_server_binary_path.strip())
            if not selected_device.frida_visible and not has_bootstrap_binary:
                raise ValueError("所选设备当前未被 Frida 识别，请提供 Frida Server 文件或先完成自举。")
        if routing.executed_backend_key == "real_frida_bootstrap":
            has_bootstrap_binary = bool(runtime_options and runtime_options.frida_server_binary_path.strip())
            if not has_bootstrap_binary:
                raise ValueError("Frida 自举模式需要提供 Frida Server 文件。")
            if selected_device.rooted is False:
                raise ValueError("所选设备当前未 Root，无法自举 frida-server。")
        return state

    def _mutate_selected_sources(self, case_id: str, source: HookPlanSource) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        return self._save_state(self._workspace_hook_plan_service.add_source(state, source))

    def _state_path(self, workspace_root: Path) -> Path:
        return self._workspace_state_service.state_path(workspace_root)

    def _custom_script_service_for(self, workspace_root: Path) -> CustomScriptService:
        if self._custom_scripts_base_root is not None:
            return CustomScriptService(self._custom_scripts_base_root / workspace_root.name)
        return CustomScriptService(workspace_root / "scripts")

    def _locate_workspace_root(self, case_id: str) -> Path:
        registry = self._registry_service.load()
        seen: set[Path] = set()
        roots: list[Path] = [self._default_workspace_root]
        roots.extend(registry.known_workspace_roots)
        for root in roots:
            normalized_root = root.expanduser()
            if normalized_root in seen:
                continue
            seen.add(normalized_root)
            for item in self._case_queue_service.list_cases(normalized_root):
                if item.case_id == case_id:
                    return item.workspace_root
        raise CaseNotFoundError(case_id)

    def _load_runtime_state_for(self, case_id: str) -> WorkspaceRuntimeState:
        workspace_root = self._locate_workspace_root(case_id)
        return self._workspace_state_service.load_for_case(case_id, workspace_root)

    def _load_state(self, record: WorkspaceInspectionRecord) -> WorkspaceRuntimeState:
        return self._workspace_state_service.load_from_record(record)

    def _save_state(self, state: WorkspaceRuntimeState) -> WorkspaceRuntimeState:
        return self._workspace_state_service.save(state)

    def _replace_current_execution_history(
        self,
        state: WorkspaceRuntimeState,
        *,
        run_id: str | None = None,
        execution_mode: str | None = None,
        executed_backend_key: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        event_count: int | None = None,
        db_path: Path | None = None,
        bundle_path: Path | None = None,
        clear_current: bool = False,
    ) -> WorkspaceRuntimeState:
        history_id = state.current_execution_history_id
        if history_id is None:
            return state

        updated_entries = list(state.execution_history)
        for index, entry in enumerate(updated_entries):
            if entry.history_id != history_id:
                continue
            updated_entries[index] = replace(
                entry,
                run_id=run_id if run_id is not None else entry.run_id,
                execution_mode=execution_mode if execution_mode is not None else entry.execution_mode,
                executed_backend_key=(
                    executed_backend_key
                    if executed_backend_key is not None
                    else entry.executed_backend_key
                ),
                status=status if status is not None else entry.status,
                stage=stage if stage is not None else entry.stage,
                error_code=error_code if error_code is not None else entry.error_code,
                error_message=error_message if error_message is not None else entry.error_message,
                event_count=event_count if event_count is not None else entry.event_count,
                db_path=db_path if db_path is not None else entry.db_path,
                bundle_path=bundle_path if bundle_path is not None else entry.bundle_path,
                updated_at=_now_iso(),
            )
            return replace(
                state,
                current_execution_history_id=None if clear_current else history_id,
                execution_history=tuple(updated_entries),
            )
        return state
