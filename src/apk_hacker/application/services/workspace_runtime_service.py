from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha1
import json
import os
from pathlib import Path

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.execution_presets import label_for_preset
from apk_hacker.application.services.custom_script_service import CustomScriptRecord, CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.report_export_service import ExportableReport, ReportExportService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.hook_plan import HookPlanItem
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.hook_plan import MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(value: object | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    if not isinstance(value, (str, bytes)):
        return None
    text = value.decode() if isinstance(value, bytes) else value
    text = text.strip()
    if not text:
        return None
    return Path(text)


def _serialize_method(entry: MethodIndexEntry) -> dict[str, object]:
    return {
        "class_name": entry.class_name,
        "method_name": entry.method_name,
        "parameter_types": list(entry.parameter_types),
        "return_type": entry.return_type,
        "is_constructor": entry.is_constructor,
        "overload_count": entry.overload_count,
        "source_path": entry.source_path,
        "line_hint": entry.line_hint,
        "tags": list(entry.tags),
        "evidence": list(entry.evidence),
    }


def _deserialize_method(payload: object) -> MethodIndexEntry | None:
    if not isinstance(payload, dict):
        return None
    class_name = payload.get("class_name")
    method_name = payload.get("method_name")
    parameter_types = payload.get("parameter_types", [])
    return_type = payload.get("return_type")
    source_path = payload.get("source_path")
    if not isinstance(class_name, str) or not isinstance(method_name, str):
        return None
    if not isinstance(return_type, str) or not isinstance(source_path, str):
        return None
    if not isinstance(parameter_types, list):
        parameter_types = []
    tags = payload.get("tags", [])
    evidence = payload.get("evidence", [])
    return MethodIndexEntry(
        class_name=class_name,
        method_name=method_name,
        parameter_types=tuple(str(value) for value in parameter_types),
        return_type=return_type,
        is_constructor=bool(payload.get("is_constructor", False)),
        overload_count=int(payload.get("overload_count", 1)),
        source_path=source_path,
        line_hint=payload.get("line_hint"),
        tags=tuple(str(value) for value in tags) if isinstance(tags, list) else (),
        evidence=tuple(str(value) for value in evidence) if isinstance(evidence, list) else (),
    )


def _serialize_source(source: HookPlanSource) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_id": source.source_id,
        "kind": source.kind,
    }
    if source.method is not None:
        payload["method"] = _serialize_method(source.method)
    if source.script_name is not None:
        payload["script_name"] = source.script_name
    if source.script_path is not None:
        payload["script_path"] = source.script_path
    if source.template_id is not None:
        payload["template_id"] = source.template_id
    if source.template_name is not None:
        payload["template_name"] = source.template_name
    if source.plugin_id is not None:
        payload["plugin_id"] = source.plugin_id
    return payload


def _deserialize_source(payload: object) -> HookPlanSource | None:
    if not isinstance(payload, dict):
        return None
    source_id = payload.get("source_id")
    kind = payload.get("kind")
    if not isinstance(source_id, str) or not isinstance(kind, str):
        return None
    method = _deserialize_method(payload.get("method"))
    script_name = payload.get("script_name")
    script_path = payload.get("script_path")
    template_id = payload.get("template_id")
    template_name = payload.get("template_name")
    plugin_id = payload.get("plugin_id")
    return HookPlanSource(
        source_id=source_id,
        kind=kind,
        method=method,
        script_name=str(script_name) if isinstance(script_name, str) else None,
        script_path=str(script_path) if isinstance(script_path, str) else None,
        template_id=str(template_id) if isinstance(template_id, str) else None,
        template_name=str(template_name) if isinstance(template_name, str) else None,
        plugin_id=str(plugin_id) if isinstance(plugin_id, str) else None,
    )


def _serialize_target(target: MethodHookTarget) -> dict[str, object]:
    return {
        "target_id": target.target_id,
        "class_name": target.class_name,
        "method_name": target.method_name,
        "parameter_types": list(target.parameter_types),
        "return_type": target.return_type,
        "source_origin": target.source_origin,
        "notes": target.notes,
    }


def _deserialize_target(payload: object) -> MethodHookTarget | None:
    if not isinstance(payload, dict):
        return None
    target_id = payload.get("target_id")
    class_name = payload.get("class_name")
    method_name = payload.get("method_name")
    parameter_types = payload.get("parameter_types", [])
    return_type = payload.get("return_type")
    source_origin = payload.get("source_origin")
    if not all(isinstance(value, str) for value in (target_id, class_name, method_name, return_type, source_origin)):
        return None
    if not isinstance(parameter_types, list):
        parameter_types = []
    return MethodHookTarget(
        target_id=str(target_id),
        class_name=str(class_name),
        method_name=str(method_name),
        parameter_types=tuple(str(value) for value in parameter_types),
        return_type=str(return_type),
        source_origin=str(source_origin),
        notes=str(payload.get("notes", "")),
    )


def _serialize_plan_item(item: HookPlanItem) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "kind": item.kind,
        "enabled": item.enabled,
        "inject_order": item.inject_order,
        "target": _serialize_target(item.target) if item.target is not None else None,
        "render_context": dict(item.render_context),
        "plugin_id": item.plugin_id,
    }


def _deserialize_plan_item(payload: object) -> HookPlanItem | None:
    if not isinstance(payload, dict):
        return None
    item_id = payload.get("item_id")
    kind = payload.get("kind")
    if not isinstance(item_id, str) or not isinstance(kind, str):
        return None
    render_context = payload.get("render_context", {})
    if not isinstance(render_context, dict):
        render_context = {}
    return HookPlanItem(
        item_id=item_id,
        kind=kind,
        enabled=bool(payload.get("enabled", True)),
        inject_order=int(payload.get("inject_order", 0)),
        target=_deserialize_target(payload.get("target")),
        render_context={str(key): value for key, value in render_context.items()},
        plugin_id=str(payload["plugin_id"]) if isinstance(payload.get("plugin_id"), str) else None,
    )


def _serialize_plan(plan: HookPlan) -> dict[str, object]:
    return {"items": [_serialize_plan_item(item) for item in plan.items]}


def _deserialize_plan(payload: object) -> HookPlan | None:
    if not isinstance(payload, dict):
        return None
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    deserialized = [item for item in (_deserialize_plan_item(entry) for entry in items) if item is not None]
    return HookPlan(items=tuple(deserialized))


def _stable_item_id(source_id: str) -> str:
    digest = sha1(source_id.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"hook-{digest}"


@dataclass(frozen=True, slots=True)
class WorkspaceRuntimeState:
    case_id: str
    workspace_root: Path
    updated_at: str
    selected_hook_sources: tuple[HookPlanSource, ...]
    rendered_hook_plan: HookPlan
    execution_count: int = 0
    last_execution_run_id: str | None = None
    last_execution_mode: str | None = None
    last_execution_status: str | None = None
    last_execution_event_count: int | None = None
    last_execution_result_path: Path | None = None
    last_execution_db_path: Path | None = None
    last_execution_bundle_path: Path | None = None
    last_report_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    state: WorkspaceRuntimeState
    execution_mode: str
    run_id: str
    event_count: int
    db_path: Path
    bundle_path: Path
    executed_backend_label: str
    events: tuple[HookEvent, ...]


@dataclass(frozen=True, slots=True)
class ReportExportResult:
    state: WorkspaceRuntimeState
    report_path: Path
    static_report_path: Path | None


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
        case_queue_service: CaseQueueService | None = None,
    ) -> None:
        self._registry_service = registry_service
        self._default_workspace_root = default_workspace_root
        self._inspection_service = inspection_service
        self._custom_script_service = custom_script_service or CustomScriptService(
            default_workspace_root.parent / "custom-scripts"
        )
        self._hook_plan_service = hook_plan_service or HookPlanService()
        self._report_export_service = report_export_service or ReportExportService()
        self._case_queue_service = case_queue_service or CaseQueueService()

    def get_state(self, case_id: str) -> WorkspaceRuntimeState:
        record = self._inspection_service.get_detail(case_id)
        return self._load_state(record)

    def list_custom_scripts(self, case_id: str) -> tuple[CustomScriptRecord, ...]:
        return self._inspection_service.get_detail(case_id).custom_scripts

    def save_custom_script(self, case_id: str, name: str, content: str) -> CustomScriptRecord:
        self._inspection_service.get_detail(case_id)
        return self._custom_script_service.save_script(name, content)

    def add_method_to_plan(self, case_id: str, method: MethodIndexEntry) -> WorkspaceRuntimeState:
        return self._mutate_selected_sources(case_id, HookPlanSource.from_method(method))

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

    def remove_hook_plan_item(self, case_id: str, item_id: str) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        remaining = tuple(source for source in state.selected_hook_sources if _stable_item_id(source.source_id) != item_id)
        if len(remaining) == len(state.selected_hook_sources):
            raise KeyError(item_id)
        return self._save_state(
            replace(
                state,
                selected_hook_sources=remaining,
                rendered_hook_plan=self._hook_plan_service.plan_for_sources(list(remaining)),
            )
        )

    def clear_hook_plan(self, case_id: str) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        return self._save_state(
            replace(
                state,
                selected_hook_sources=(),
                rendered_hook_plan=HookPlan(items=()),
            )
        )

    def execute_current_plan(self, case_id: str, execution_mode: str | None = None) -> ExecutionResult:
        record = self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        if not state.rendered_hook_plan.items:
            raise ValueError("Add at least one hook plan item first.")

        resolved_mode = execution_mode or "fake_backend"
        run_index = state.execution_count + 1
        run_id = f"run-{run_index}"
        bundle_path = record.workspace_root / "executions" / run_id
        bundle_path.mkdir(parents=True, exist_ok=True)

        if resolved_mode == "fake_backend":
            backend = FakeExecutionBackend()
        elif resolved_mode.startswith("real_"):
            backend = RealExecutionBackend(
                command=os.environ.get("APKHACKER_REAL_BACKEND_COMMAND"),
                artifact_root=bundle_path,
            )
        else:
            raise ValueError(f"Unsupported execution mode: {resolved_mode}")

        request = ExecutionRequest(
            job_id=record.bundle.job.job_id,
            plan=state.rendered_hook_plan,
            package_name=record.bundle.static_inputs.package_name,
            sample_path=record.sample_path,
        )
        events = backend.execute(request)

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
        store = HookLogStore(db_path)
        persisted_events: list[HookEvent] = []
        for event in events:
            if event.event_type == "execution_bundle":
                continue
            persisted_events.append(event)
        for event in persisted_events:
            store.insert(replace(event, job_id=record.bundle.job.job_id))
        runtime_state = self._save_state(
            replace(
                state,
                execution_count=run_index,
                last_execution_run_id=run_id,
                last_execution_mode=resolved_mode,
                last_execution_status="completed",
                last_execution_event_count=len(persisted_events),
                last_execution_result_path=bundle_path,
                last_execution_db_path=db_path,
                last_execution_bundle_path=bundle_path,
            )
        )
        return ExecutionResult(
            state=runtime_state,
            execution_mode=resolved_mode,
            run_id=run_id,
            event_count=len(persisted_events),
            db_path=db_path,
            bundle_path=bundle_path,
            executed_backend_label=label_for_preset(resolved_mode),
            events=tuple(persisted_events),
        )

    def export_report(self, case_id: str) -> ReportExportResult:
        record = self._inspection_service.get_detail(case_id)
        state = self.get_state(case_id)
        events: tuple[HookEvent, ...] = ()
        if state.last_execution_db_path is not None and state.last_execution_db_path.exists():
            events = tuple(HookLogStore(state.last_execution_db_path).list_for_job(record.bundle.job.job_id))

        static_report_path = record.bundle.static_inputs.artifact_paths.static_markdown_report
        summary_text = (
            f"当前 Hook Plan 共 {len(state.rendered_hook_plan.items)} 项，"
            f"最近一次执行产生 {len(events)} 条事件。"
        )
        report = ExportableReport(
            job_id=record.bundle.job.job_id,
            summary_text=summary_text,
            sample_path=record.sample_path,
            static_inputs=record.bundle.static_inputs,
            hook_plan=state.rendered_hook_plan,
            hook_events=events,
            traffic_capture=None,
            last_execution_db_path=state.last_execution_db_path,
            last_execution_bundle_path=state.last_execution_bundle_path,
        )
        report_path = record.workspace_root / "reports" / f"{case_id}-report.md"
        exported_path = self._report_export_service.export_markdown(report, report_path)
        saved_state = self._save_state(replace(state, last_report_path=exported_path))
        return ReportExportResult(
            state=saved_state,
            report_path=exported_path,
            static_report_path=static_report_path,
        )

    def _mutate_selected_sources(self, case_id: str, source: HookPlanSource) -> WorkspaceRuntimeState:
        state = self.get_state(case_id)
        if any(existing.source_id == source.source_id for existing in state.selected_hook_sources):
            return state
        selected_hook_sources = (*state.selected_hook_sources, source)
        return self._save_state(
            replace(
                state,
                selected_hook_sources=selected_hook_sources,
                rendered_hook_plan=self._hook_plan_service.plan_for_sources(list(selected_hook_sources)),
            )
        )

    def _state_path(self, workspace_root: Path) -> Path:
        return workspace_root / "workspace-runtime.json"

    def _load_state(self, record: WorkspaceInspectionRecord) -> WorkspaceRuntimeState:
        path = self._state_path(record.workspace_root)
        if not path.exists():
            return WorkspaceRuntimeState(
                case_id=record.case_id,
                workspace_root=record.workspace_root,
                updated_at=_now_iso(),
                selected_hook_sources=(),
                rendered_hook_plan=HookPlan(items=()),
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return WorkspaceRuntimeState(
                case_id=record.case_id,
                workspace_root=record.workspace_root,
                updated_at=_now_iso(),
                selected_hook_sources=(),
                rendered_hook_plan=HookPlan(items=()),
            )
        if not isinstance(payload, dict):
            return WorkspaceRuntimeState(
                case_id=record.case_id,
                workspace_root=record.workspace_root,
                updated_at=_now_iso(),
                selected_hook_sources=(),
                rendered_hook_plan=HookPlan(items=()),
            )
        selected_hook_sources = tuple(
            source for source in (_deserialize_source(entry) for entry in payload.get("selected_hook_sources", [])) if source is not None
        )
        rendered_hook_plan = _deserialize_plan(payload.get("rendered_hook_plan"))
        if rendered_hook_plan is None:
            rendered_hook_plan = self._hook_plan_service.plan_for_sources(list(selected_hook_sources))
        execution_count = int(payload.get("execution_count", 0))
        return WorkspaceRuntimeState(
            case_id=record.case_id,
            workspace_root=record.workspace_root,
            updated_at=str(payload.get("updated_at", _now_iso())),
            selected_hook_sources=selected_hook_sources,
            rendered_hook_plan=rendered_hook_plan,
            execution_count=execution_count,
            last_execution_run_id=payload.get("last_execution_run_id"),
            last_execution_mode=payload.get("last_execution_mode"),
            last_execution_status=payload.get("last_execution_status"),
            last_execution_event_count=payload.get("last_execution_event_count"),
            last_execution_result_path=_normalize_path(payload.get("last_execution_result_path")),
            last_execution_db_path=_normalize_path(payload.get("last_execution_db_path")),
            last_execution_bundle_path=_normalize_path(payload.get("last_execution_bundle_path")),
            last_report_path=_normalize_path(payload.get("last_report_path")),
        )

    def _save_state(self, state: WorkspaceRuntimeState) -> WorkspaceRuntimeState:
        payload = {
            "case_id": state.case_id,
            "updated_at": _now_iso(),
            "selected_hook_sources": [_serialize_source(source) for source in state.selected_hook_sources],
            "rendered_hook_plan": _serialize_plan(state.rendered_hook_plan),
            "execution_count": state.execution_count,
            "last_execution_run_id": state.last_execution_run_id,
            "last_execution_mode": state.last_execution_mode,
            "last_execution_status": state.last_execution_status,
            "last_execution_event_count": state.last_execution_event_count,
            "last_execution_result_path": str(state.last_execution_result_path) if state.last_execution_result_path else None,
            "last_execution_db_path": str(state.last_execution_db_path) if state.last_execution_db_path else None,
            "last_execution_bundle_path": str(state.last_execution_bundle_path) if state.last_execution_bundle_path else None,
            "last_report_path": str(state.last_report_path) if state.last_report_path else None,
        }
        path = self._state_path(state.workspace_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)
        return replace(state, updated_at=payload["updated_at"])
