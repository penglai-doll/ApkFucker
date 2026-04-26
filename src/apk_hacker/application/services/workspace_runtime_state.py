from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
import json
import time
import uuid

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.hook_plan import HookPlanSource
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

    def to_payload(self) -> dict[str, object]:
        return {
            "history_id": self.history_id,
            "run_id": self.run_id,
            "execution_mode": self.execution_mode,
            "executed_backend_key": self.executed_backend_key,
            "status": self.status,
            "stage": self.stage,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "event_count": self.event_count,
            "db_path": str(self.db_path) if self.db_path else None,
            "bundle_path": str(self.bundle_path) if self.bundle_path else None,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ExecutionHistoryEntry | None":
        if not isinstance(payload, dict):
            return None
        history_id = payload.get("history_id")
        if not isinstance(history_id, str):
            return None
        return cls(
            history_id=history_id,
            run_id=str(payload["run_id"]) if isinstance(payload.get("run_id"), str) else None,
            execution_mode=str(payload["execution_mode"]) if isinstance(payload.get("execution_mode"), str) else None,
            executed_backend_key=(
                str(payload["executed_backend_key"])
                if isinstance(payload.get("executed_backend_key"), str)
                else None
            ),
            status=str(payload["status"]) if isinstance(payload.get("status"), str) else None,
            stage=str(payload["stage"]) if isinstance(payload.get("stage"), str) else None,
            error_code=str(payload["error_code"]) if isinstance(payload.get("error_code"), str) else None,
            error_message=str(payload["error_message"]) if isinstance(payload.get("error_message"), str) else None,
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

    def to_payload(self, *, updated_at: str | None = None) -> dict[str, object]:
        payload_updated_at = updated_at or self.updated_at
        return {
            "case_id": self.case_id,
            "updated_at": payload_updated_at,
            "selected_hook_sources": [source.to_payload() for source in self.selected_hook_sources],
            "rendered_hook_plan": self.rendered_hook_plan.to_payload(),
            "current_execution_history_id": self.current_execution_history_id,
            "execution_history": [
                entry.to_payload()
                for entry in self.execution_history
            ],
            "execution_count": self.execution_count,
            "last_execution_run_id": self.last_execution_run_id,
            "last_execution_mode": self.last_execution_mode,
            "last_executed_backend_key": self.last_executed_backend_key,
            "last_execution_status": self.last_execution_status,
            "last_execution_stage": self.last_execution_stage,
            "last_execution_error_code": self.last_execution_error_code,
            "last_execution_error_message": self.last_execution_error_message,
            "last_execution_event_count": self.last_execution_event_count,
            "last_execution_result_path": str(self.last_execution_result_path) if self.last_execution_result_path else None,
            "last_execution_db_path": str(self.last_execution_db_path) if self.last_execution_db_path else None,
            "last_execution_bundle_path": str(self.last_execution_bundle_path) if self.last_execution_bundle_path else None,
            "last_report_path": str(self.last_report_path) if self.last_report_path else None,
            "traffic_capture_source_path": str(self.traffic_capture_source_path) if self.traffic_capture_source_path else None,
            "traffic_capture_summary_path": (
                str(self.traffic_capture_summary_path) if self.traffic_capture_summary_path else None
            ),
            "traffic_capture_flow_count": self.traffic_capture_flow_count,
            "traffic_capture_suspicious_count": self.traffic_capture_suspicious_count,
            "live_traffic_capture_status": self.live_traffic_capture.status,
            "live_traffic_capture_session_id": self.live_traffic_capture.session_id,
            "live_traffic_capture_output_path": (
                str(self.live_traffic_capture.output_path) if self.live_traffic_capture.output_path else None
            ),
            "live_traffic_capture_preview_path": (
                str(self.live_traffic_capture.preview_path) if self.live_traffic_capture.preview_path else None
            ),
            "live_traffic_capture_message": self.live_traffic_capture.message,
            "live_traffic_capture": self.live_traffic_capture.to_payload(),
        }

    @classmethod
    def from_payload(
        cls,
        *,
        case_id: str,
        workspace_root: Path,
        payload: object,
        hook_plan_service: HookPlanService,
    ) -> "WorkspaceRuntimeState":
        if not isinstance(payload, dict):
            return build_default_runtime_state(case_id, workspace_root)
        selected_hook_sources = tuple(
            source
            for source in (HookPlanSource.from_payload(entry) for entry in payload.get("selected_hook_sources", []))
            if source is not None
        )
        persisted_plan = HookPlan.from_payload(payload.get("rendered_hook_plan"))
        live_traffic_capture_payload = payload.get("live_traffic_capture")
        live_traffic_capture = (
            TrafficLiveCaptureState.from_payload(live_traffic_capture_payload)
            if isinstance(live_traffic_capture_payload, dict)
            else TrafficLiveCaptureState.from_legacy_payload(payload)
        )
        return cls(
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
                    ExecutionHistoryEntry.from_payload(item)
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
            live_traffic_capture=live_traffic_capture,
        )


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

    return WorkspaceRuntimeState.from_payload(
        case_id=case_id,
        workspace_root=workspace_root,
        payload=payload,
        hook_plan_service=hook_plan_service,
    )


def save_workspace_runtime_state(state: WorkspaceRuntimeState, path: Path) -> WorkspaceRuntimeState:
    payload = state.to_payload(updated_at=_now_iso())
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(10):
        try:
            temp_path.replace(path)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.02)
    if temp_path.exists():
        temp_path.unlink(missing_ok=True)
    return replace(state, updated_at=payload["updated_at"])
