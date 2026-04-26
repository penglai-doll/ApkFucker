from __future__ import annotations

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
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState
from apk_hacker.domain.models.traffic import traffic_capture_id_for_path
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
        capture = TrafficCapture.from_payload(
            payload,
            provenance_factory=lambda source_path: build_traffic_capture_provenance(
                infer_traffic_capture_provenance_kind(source_path),
                source_path,
            ),
        )
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
            json.dumps(capture.to_payload(), ensure_ascii=False, indent=2),
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
        return traffic_capture_id_for_path(source_path)
