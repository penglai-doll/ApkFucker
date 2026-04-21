from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
import json

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.hook_plan import HookPlanItem
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.hook_plan import MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_path(value: object | None) -> Path | None:
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
        "declaration": entry.declaration,
        "source_preview": entry.source_preview,
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
    declaration = payload.get("declaration", "")
    source_preview = payload.get("source_preview", "")
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
        declaration=str(declaration) if isinstance(declaration, str) else "",
        source_preview=str(source_preview) if isinstance(source_preview, str) else "",
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
    return HookPlanSource(
        source_id=source_id,
        kind=kind,
        method=_deserialize_method(payload.get("method")),
        script_name=str(payload["script_name"]) if isinstance(payload.get("script_name"), str) else None,
        script_path=str(payload["script_path"]) if isinstance(payload.get("script_path"), str) else None,
        template_id=str(payload["template_id"]) if isinstance(payload.get("template_id"), str) else None,
        template_name=str(payload["template_name"]) if isinstance(payload.get("template_name"), str) else None,
        plugin_id=str(payload["plugin_id"]) if isinstance(payload.get("plugin_id"), str) else None,
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


def _deserialize_plan(payload: object) -> HookPlan:
    if not isinstance(payload, dict):
        return HookPlan(items=())
    items_payload = payload.get("items", [])
    if not isinstance(items_payload, list):
        items_payload = []
    return HookPlan(
        items=tuple(
            item
            for item in (_deserialize_plan_item(entry) for entry in items_payload)
            if item is not None
        )
    )


def _default_live_traffic_capture_state() -> TrafficLiveCaptureState:
    return TrafficLiveCaptureState(status="idle")


@dataclass(frozen=True, slots=True)
class ExecutionHistoryEntry:
    history_id: str
    run_id: str | None = None
    execution_mode: str | None = None
    executed_backend_key: str | None = None
    status: str | None = None
    stage: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    event_count: int | None = None
    db_path: Path | None = None
    bundle_path: Path | None = None
    started_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


def _serialize_execution_history_entry(entry: ExecutionHistoryEntry) -> dict[str, object]:
    return {
        "history_id": entry.history_id,
        "run_id": entry.run_id,
        "execution_mode": entry.execution_mode,
        "executed_backend_key": entry.executed_backend_key,
        "status": entry.status,
        "stage": entry.stage,
        "error_code": entry.error_code,
        "error_message": entry.error_message,
        "event_count": entry.event_count,
        "db_path": str(entry.db_path) if entry.db_path else None,
        "bundle_path": str(entry.bundle_path) if entry.bundle_path else None,
        "started_at": entry.started_at,
        "updated_at": entry.updated_at,
    }


def _deserialize_execution_history_entry(payload: object) -> ExecutionHistoryEntry | None:
    if not isinstance(payload, dict):
        return None
    history_id = payload.get("history_id")
    if not isinstance(history_id, str):
        return None
    return ExecutionHistoryEntry(
        history_id=history_id,
        run_id=str(payload["run_id"]) if isinstance(payload.get("run_id"), str) else None,
        execution_mode=(
            str(payload["execution_mode"])
            if isinstance(payload.get("execution_mode"), str)
            else None
        ),
        executed_backend_key=(
            str(payload["executed_backend_key"])
            if isinstance(payload.get("executed_backend_key"), str)
            else None
        ),
        status=str(payload["status"]) if isinstance(payload.get("status"), str) else None,
        stage=str(payload["stage"]) if isinstance(payload.get("stage"), str) else None,
        error_code=str(payload["error_code"]) if isinstance(payload.get("error_code"), str) else None,
        error_message=(
            str(payload["error_message"])
            if isinstance(payload.get("error_message"), str)
            else None
        ),
        event_count=payload.get("event_count") if isinstance(payload.get("event_count"), int) else None,
        db_path=normalize_path(payload.get("db_path")),
        bundle_path=normalize_path(payload.get("bundle_path")),
        started_at=str(payload.get("started_at", _now_iso())),
        updated_at=str(payload.get("updated_at", payload.get("started_at", _now_iso()))),
    )


@dataclass(frozen=True, slots=True)
class WorkspaceRuntimeState:
    case_id: str
    workspace_root: Path
    updated_at: str
    selected_hook_sources: tuple[HookPlanSource, ...]
    rendered_hook_plan: HookPlan
    current_execution_history_id: str | None = None
    execution_history: tuple[ExecutionHistoryEntry, ...] = ()
    execution_count: int = 0
    last_execution_run_id: str | None = None
    last_execution_mode: str | None = None
    last_executed_backend_key: str | None = None
    last_execution_status: str | None = None
    last_execution_stage: str | None = None
    last_execution_error_code: str | None = None
    last_execution_error_message: str | None = None
    last_execution_event_count: int | None = None
    last_execution_result_path: Path | None = None
    last_execution_db_path: Path | None = None
    last_execution_bundle_path: Path | None = None
    last_report_path: Path | None = None
    traffic_capture_source_path: Path | None = None
    traffic_capture_summary_path: Path | None = None
    traffic_capture_flow_count: int | None = None
    traffic_capture_suspicious_count: int | None = None
    live_traffic_capture: TrafficLiveCaptureState = field(default_factory=_default_live_traffic_capture_state)


def build_default_runtime_state(case_id: str, workspace_root: Path) -> WorkspaceRuntimeState:
    return WorkspaceRuntimeState(
        case_id=case_id,
        workspace_root=workspace_root,
        updated_at=_now_iso(),
        selected_hook_sources=(),
        rendered_hook_plan=HookPlan(items=()),
    )


def load_workspace_runtime_state(
    *,
    case_id: str,
    workspace_root: Path,
    path: Path,
    hook_plan_service: HookPlanService,
) -> WorkspaceRuntimeState:
    if not path.exists():
        return build_default_runtime_state(case_id, workspace_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return build_default_runtime_state(case_id, workspace_root)
    if not isinstance(payload, dict):
        return build_default_runtime_state(case_id, workspace_root)

    selected_hook_sources = tuple(
        source
        for source in (_deserialize_source(entry) for entry in payload.get("selected_hook_sources", []))
        if source is not None
    )
    persisted_plan = _deserialize_plan(payload.get("rendered_hook_plan"))
    return WorkspaceRuntimeState(
        case_id=case_id,
        workspace_root=workspace_root,
        updated_at=str(payload.get("updated_at", _now_iso())),
        selected_hook_sources=selected_hook_sources,
        rendered_hook_plan=hook_plan_service.plan_for_sources(
            list(selected_hook_sources),
            previous_plan=persisted_plan,
        ),
        current_execution_history_id=(
            str(payload["current_execution_history_id"])
            if isinstance(payload.get("current_execution_history_id"), str)
            else None
        ),
        execution_history=tuple(
            entry
            for entry in (
                _deserialize_execution_history_entry(item)
                for item in payload.get("execution_history", [])
            )
            if entry is not None
        ),
        execution_count=int(payload.get("execution_count", 0)),
        last_execution_run_id=payload.get("last_execution_run_id"),
        last_execution_mode=payload.get("last_execution_mode"),
        last_executed_backend_key=payload.get("last_executed_backend_key"),
        last_execution_status=payload.get("last_execution_status"),
        last_execution_stage=payload.get("last_execution_stage"),
        last_execution_error_code=payload.get("last_execution_error_code"),
        last_execution_error_message=payload.get("last_execution_error_message"),
        last_execution_event_count=payload.get("last_execution_event_count"),
        last_execution_result_path=normalize_path(payload.get("last_execution_result_path")),
        last_execution_db_path=normalize_path(payload.get("last_execution_db_path")),
        last_execution_bundle_path=normalize_path(payload.get("last_execution_bundle_path")),
        last_report_path=normalize_path(payload.get("last_report_path")),
        traffic_capture_source_path=normalize_path(payload.get("traffic_capture_source_path")),
        traffic_capture_summary_path=normalize_path(payload.get("traffic_capture_summary_path")),
        traffic_capture_flow_count=payload.get("traffic_capture_flow_count"),
        traffic_capture_suspicious_count=payload.get("traffic_capture_suspicious_count"),
        live_traffic_capture=TrafficLiveCaptureState(
            status=str(payload.get("live_traffic_capture_status", "idle") or "idle"),
            session_id=(
                str(payload["live_traffic_capture_session_id"])
                if isinstance(payload.get("live_traffic_capture_session_id"), str)
                else None
            ),
            output_path=normalize_path(payload.get("live_traffic_capture_output_path")),
            preview_path=normalize_path(payload.get("live_traffic_capture_preview_path")),
            message=(
                str(payload["live_traffic_capture_message"])
                if isinstance(payload.get("live_traffic_capture_message"), str)
                else None
            ),
        ),
    )


def save_workspace_runtime_state(state: WorkspaceRuntimeState, path: Path) -> WorkspaceRuntimeState:
    payload = {
        "case_id": state.case_id,
        "updated_at": _now_iso(),
        "selected_hook_sources": [_serialize_source(source) for source in state.selected_hook_sources],
        "rendered_hook_plan": _serialize_plan(state.rendered_hook_plan),
        "current_execution_history_id": state.current_execution_history_id,
        "execution_history": [
            _serialize_execution_history_entry(entry)
            for entry in state.execution_history
        ],
        "execution_count": state.execution_count,
        "last_execution_run_id": state.last_execution_run_id,
        "last_execution_mode": state.last_execution_mode,
        "last_executed_backend_key": state.last_executed_backend_key,
        "last_execution_status": state.last_execution_status,
        "last_execution_stage": state.last_execution_stage,
        "last_execution_error_code": state.last_execution_error_code,
        "last_execution_error_message": state.last_execution_error_message,
        "last_execution_event_count": state.last_execution_event_count,
        "last_execution_result_path": str(state.last_execution_result_path) if state.last_execution_result_path else None,
        "last_execution_db_path": str(state.last_execution_db_path) if state.last_execution_db_path else None,
        "last_execution_bundle_path": str(state.last_execution_bundle_path) if state.last_execution_bundle_path else None,
        "last_report_path": str(state.last_report_path) if state.last_report_path else None,
        "traffic_capture_source_path": str(state.traffic_capture_source_path) if state.traffic_capture_source_path else None,
        "traffic_capture_summary_path": (
            str(state.traffic_capture_summary_path) if state.traffic_capture_summary_path else None
        ),
        "traffic_capture_flow_count": state.traffic_capture_flow_count,
        "traffic_capture_suspicious_count": state.traffic_capture_suspicious_count,
        "live_traffic_capture_status": state.live_traffic_capture.status,
        "live_traffic_capture_session_id": state.live_traffic_capture.session_id,
        "live_traffic_capture_output_path": (
            str(state.live_traffic_capture.output_path) if state.live_traffic_capture.output_path else None
        ),
        "live_traffic_capture_preview_path": (
            str(state.live_traffic_capture.preview_path) if state.live_traffic_capture.preview_path else None
        ),
        "live_traffic_capture_message": state.live_traffic_capture.message,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return replace(state, updated_at=payload["updated_at"])
