from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

from apk_hacker.application.services.traffic_capture_service import build_traffic_capture_provenance
from apk_hacker.application.services.traffic_capture_service import infer_traffic_capture_provenance_kind
from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.domain.models.traffic import TrafficCaptureProvenance
from apk_hacker.domain.models.traffic import TrafficCaptureSummary
from apk_hacker.domain.models.traffic import TrafficFlowSummary
from apk_hacker.domain.models.traffic import TrafficHostSummary
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState
from apk_hacker.infrastructure.persistence.traffic_flow_store import TrafficFlowStore


class WorkspaceTrafficService:
    def __init__(
        self,
        traffic_capture_service: TrafficCaptureService | None = None,
        traffic_flow_store_factory: Callable[[Path], TrafficFlowStore] | None = None,
    ) -> None:
        self._traffic_capture_service = traffic_capture_service or TrafficCaptureService()
        self._traffic_flow_store_factory = traffic_flow_store_factory or TrafficFlowStore

    def get_capture(self, state: WorkspaceRuntimeState) -> TrafficCapture | None:
        if state.traffic_capture_summary_path is None or not state.traffic_capture_summary_path.exists():
            return None
        try:
            payload = json.loads(state.traffic_capture_summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return None
        capture = _deserialize_traffic_capture(payload)
        if capture is None:
            return None
        store_path = self.traffic_flow_store_path(state.workspace_root)
        if not store_path.exists():
            return capture
        flow_store = self._traffic_flow_store_factory(store_path)
        capture_id = self.capture_id_for_path(capture.source_path)
        flows = tuple(flow_store.list_for_capture(capture_id))
        if not flows:
            return capture
        return TrafficCapture(
            source_path=capture.source_path,
            provenance=capture.provenance,
            flow_count=capture.flow_count,
            suspicious_count=capture.suspicious_count,
            summary=capture.summary,
            flows=flows,
        )

    def import_har(
        self,
        state: WorkspaceRuntimeState,
        har_path: Path,
        static_inputs: StaticInputs,
        *,
        provenance_kind: str | None = None,
    ) -> tuple[WorkspaceRuntimeState, TrafficCapture]:
        candidate_path = har_path.expanduser()
        if not candidate_path.exists():
            raise FileNotFoundError(f"HAR file not found: {candidate_path}")
        capture = self._traffic_capture_service.load_har(
            candidate_path,
            static_inputs,
            provenance_kind=provenance_kind,
        )
        summary_path = self.traffic_capture_summary_path(state.workspace_root)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(_serialize_traffic_capture(capture), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        flow_store = self._traffic_flow_store_factory(self.traffic_flow_store_path(state.workspace_root))
        flow_store.replace_capture(self.capture_id_for_path(capture.source_path), capture.flows)
        return (
            replace(
                state,
                traffic_capture_source_path=capture.source_path,
                traffic_capture_summary_path=summary_path,
                traffic_capture_flow_count=capture.flow_count,
                traffic_capture_suspicious_count=capture.suspicious_count,
            ),
            capture,
        )

    def save_live_capture_state(
        self,
        state: WorkspaceRuntimeState,
        live_capture: TrafficLiveCaptureState,
    ) -> WorkspaceRuntimeState:
        return replace(state, live_traffic_capture=live_capture)

    def get_live_capture_state(self, state: WorkspaceRuntimeState) -> TrafficLiveCaptureState:
        return state.live_traffic_capture

    def build_live_capture_output_path(self, workspace_root: Path, session_id: str) -> Path:
        return workspace_root / "evidence" / "traffic" / "live" / f"{session_id}.har"

    def traffic_capture_summary_path(self, workspace_root: Path) -> Path:
        return workspace_root / "evidence" / "traffic" / "traffic-capture.json"

    def traffic_flow_store_path(self, workspace_root: Path) -> Path:
        return workspace_root / "evidence" / "traffic" / "traffic-flows.sqlite3"

    def capture_id_for_path(self, source_path: Path) -> str:
        normalized = str(source_path.expanduser().resolve())
        digest = hashlib.sha1(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"capture-{digest}"


def _serialize_traffic_capture(capture: TrafficCapture) -> dict[str, object]:
    summary_payload = {
        "https_flow_count": capture.https_flow_count,
        "matched_indicator_count": capture.matched_indicator_count,
        "top_hosts": [
            {
                "host": host.host,
                "flow_count": host.flow_count,
                "suspicious_count": host.suspicious_count,
                "https_flow_count": host.https_flow_count,
            }
            for host in capture.top_hosts
        ],
        "suspicious_hosts": [
            {
                "host": host.host,
                "flow_count": host.flow_count,
                "suspicious_count": host.suspicious_count,
                "https_flow_count": host.https_flow_count,
            }
            for host in capture.suspicious_hosts
        ],
    }
    return {
        "source_path": str(capture.source_path),
        "provenance": {
            "kind": capture.provenance.kind,
            "label": capture.provenance.label,
        },
        "flow_count": capture.flow_count,
        "suspicious_count": capture.suspicious_count,
        "https_flow_count": capture.https_flow_count,
        "matched_indicator_count": capture.matched_indicator_count,
        "top_hosts": summary_payload["top_hosts"],
        "suspicious_hosts": summary_payload["suspicious_hosts"],
        "summary": summary_payload,
    }


def _deserialize_traffic_capture(payload: object) -> TrafficCapture | None:
    if not isinstance(payload, dict):
        return None
    source_path_raw = payload.get("source_path")
    flow_count = payload.get("flow_count")
    suspicious_count = payload.get("suspicious_count")
    if not isinstance(source_path_raw, str) or not isinstance(flow_count, int) or not isinstance(suspicious_count, int):
        return None
    source_path = Path(source_path_raw)
    summary_payload = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    https_flow_count = summary_payload.get("https_flow_count", payload.get("https_flow_count", 0))
    matched_indicator_count = summary_payload.get("matched_indicator_count", payload.get("matched_indicator_count", 0))
    top_hosts_payload = summary_payload.get("top_hosts", payload.get("top_hosts", []))
    suspicious_hosts_payload = summary_payload.get("suspicious_hosts", payload.get("suspicious_hosts", []))
    provenance_payload = payload.get("provenance")
    if isinstance(provenance_payload, dict):
        kind = provenance_payload.get("kind")
        label = provenance_payload.get("label")
        if isinstance(kind, str) and isinstance(label, str):
            provenance = TrafficCaptureProvenance(kind=kind, label=label)
        else:
            provenance = build_traffic_capture_provenance(infer_traffic_capture_provenance_kind(source_path), source_path)
    else:
        provenance = build_traffic_capture_provenance(infer_traffic_capture_provenance_kind(source_path), source_path)

    def _host_summary(item: object) -> TrafficHostSummary | None:
        if not isinstance(item, dict):
            return None
        host = item.get("host")
        flow_count_value = item.get("flow_count")
        suspicious_count_value = item.get("suspicious_count")
        https_flow_count_value = item.get("https_flow_count", 0)
        if not isinstance(host, str) or not isinstance(flow_count_value, int) or not isinstance(suspicious_count_value, int):
            return None
        if not isinstance(https_flow_count_value, int):
            https_flow_count_value = 0
        return TrafficHostSummary(
            host=host,
            flow_count=flow_count_value,
            suspicious_count=suspicious_count_value,
            https_flow_count=https_flow_count_value,
        )

    top_hosts = tuple(host for host in (_host_summary(item) for item in top_hosts_payload or []) if host is not None)
    suspicious_hosts = tuple(host for host in (_host_summary(item) for item in suspicious_hosts_payload or []) if host is not None)
    flows_payload = payload.get("flows", [])
    flows = tuple(
        TrafficFlowSummary(
            flow_id=str(item["flow_id"]),
            method=str(item["method"]),
            url=str(item["url"]),
            status_code=item.get("status_code") if isinstance(item.get("status_code"), int) else None,
            mime_type=item.get("mime_type") if isinstance(item.get("mime_type"), str) else None,
            request_preview=str(item.get("request_preview", "")),
            response_preview=str(item.get("response_preview", "")),
            matched_indicators=tuple(str(value) for value in item.get("matched_indicators", []) or []),
            suspicious=bool(item.get("suspicious", False)),
        )
        for item in flows_payload
        if isinstance(item, dict)
        and isinstance(item.get("flow_id"), str)
        and isinstance(item.get("method"), str)
        and isinstance(item.get("url"), str)
    )
    return TrafficCapture(
        source_path=source_path,
        provenance=provenance,
        flow_count=flow_count,
        suspicious_count=suspicious_count,
        summary=TrafficCaptureSummary(
            https_flow_count=https_flow_count if isinstance(https_flow_count, int) else 0,
            matched_indicator_count=matched_indicator_count if isinstance(matched_indicator_count, int) else 0,
            top_hosts=top_hosts,
            suspicious_hosts=suspicious_hosts,
        ),
        flows=flows,
    )
