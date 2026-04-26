from __future__ import annotations

import time

from apk_hacker.application.services.live_capture_runtime import build_live_capture_preview_path
from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.traffic_capture_service import LIVE_CAPTURE_PROVENANCE_KIND
from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.domain.models.traffic import TrafficFlow
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState
from apk_hacker.interfaces.api_fastapi.schemas import LiveTrafficCaptureResponse
from apk_hacker.interfaces.api_fastapi.schemas import LiveTrafficPreviewResponse
from apk_hacker.interfaces.api_fastapi.schemas import TrafficCaptureResponse
from apk_hacker.interfaces.api_fastapi.schemas import TrafficFlowSummaryResponse
from apk_hacker.interfaces.api_fastapi.schemas import TrafficImportRequest
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceTrafficResponse
from apk_hacker.interfaces.api_fastapi.traffic_capture_dispatcher import TrafficCaptureDispatcher
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub

LIVE_CAPTURE_ARTIFACT_POLL_INTERVAL_SECONDS = 0.1
LIVE_CAPTURE_ARTIFACT_POLL_ATTEMPTS = 40
LIVE_CAPTURE_PREVIEW_DEFAULT_LIMIT = 8


def _to_flow_response(flow: TrafficFlow) -> TrafficFlowSummaryResponse:
    return TrafficFlowSummaryResponse(**flow.to_payload())


def _to_capture_response(case_id: str, capture: TrafficCapture) -> TrafficCaptureResponse:
    return TrafficCaptureResponse(case_id=case_id, **capture.to_payload())


def _to_live_capture_response(case_id: str, live_capture: TrafficLiveCaptureState) -> LiveTrafficCaptureResponse:
    return LiveTrafficCaptureResponse(
        case_id=case_id,
        status=live_capture.status,
        session_id=live_capture.session_id,
        artifact_path=str(live_capture.output_path) if live_capture.output_path else None,
        output_path=str(live_capture.output_path) if live_capture.output_path else None,
        preview_path=str(live_capture.preview_path) if live_capture.preview_path else None,
        message=live_capture.message,
    )


def _live_event_payload(case_id: str, live_capture: TrafficLiveCaptureState) -> dict[str, object]:
    return {
        "type": "traffic.live.updated",
        "case_id": case_id,
        "status": live_capture.status,
        "session_id": live_capture.session_id,
        "artifact_path": str(live_capture.output_path) if live_capture.output_path else None,
        "output_path": str(live_capture.output_path) if live_capture.output_path else None,
        "preview_path": str(live_capture.preview_path) if live_capture.preview_path else None,
        "message": live_capture.message,
    }


def build_traffic_router(
    *,
    hub: WebSocketHub,
    workspace_runtime_service: WorkspaceRuntimeService,
    traffic_capture_dispatcher: TrafficCaptureDispatcher,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["traffic"])
    preview_service = TrafficCaptureService()

    @router.get("/{case_id}/traffic", response_model=WorkspaceTrafficResponse)
    def get_traffic_capture(case_id: str) -> WorkspaceTrafficResponse:
        try:
            capture = workspace_runtime_service.get_traffic_capture(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        return WorkspaceTrafficResponse(
            case_id=case_id,
            capture=_to_capture_response(case_id, capture) if capture is not None else None,
        )

    @router.post("/{case_id}/traffic/import", response_model=TrafficCaptureResponse)
    def import_traffic_capture(case_id: str, payload: TrafficImportRequest) -> TrafficCaptureResponse:
        try:
            capture = workspace_runtime_service.import_traffic_capture(case_id, payload.har_path)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return _to_capture_response(case_id, capture)

    @router.get("/{case_id}/traffic/live", response_model=LiveTrafficCaptureResponse)
    def get_live_traffic_capture(case_id: str) -> LiveTrafficCaptureResponse:
        try:
            persisted_state = workspace_runtime_service.get_live_traffic_capture_state(case_id)
            live_capture = traffic_capture_dispatcher.snapshot(case_id=case_id, persisted_state=persisted_state)
            if live_capture != persisted_state:
                workspace_runtime_service.save_live_traffic_capture_state(case_id, live_capture)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        return _to_live_capture_response(case_id, live_capture)

    @router.post("/{case_id}/traffic/live/start", response_model=LiveTrafficCaptureResponse)
    async def start_live_traffic_capture(case_id: str) -> LiveTrafficCaptureResponse:
        try:
            persisted_state = workspace_runtime_service.get_live_traffic_capture_state(case_id)
            current = traffic_capture_dispatcher.snapshot(case_id=case_id, persisted_state=persisted_state)
            if current != persisted_state:
                workspace_runtime_service.save_live_traffic_capture_state(case_id, current)
            if current.status == "running":
                return _to_live_capture_response(case_id, current)
            if current.status == "unavailable":
                saved_state = workspace_runtime_service.save_live_traffic_capture_state(case_id, current)
                return _to_live_capture_response(case_id, saved_state.live_traffic_capture)

            session_id = traffic_capture_dispatcher.new_session_id()
            output_path = workspace_runtime_service.build_live_traffic_capture_output_path(case_id, session_id)
            try:
                started = traffic_capture_dispatcher.start(case_id=case_id, output_path=output_path)
            except OSError as exc:
                started = TrafficLiveCaptureState(
                    status="stopped",
                    session_id=session_id,
                    output_path=output_path,
                    message=f"启动实时抓包失败：{exc}",
                )
            saved_state = workspace_runtime_service.save_live_traffic_capture_state(case_id, started)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc

        await hub.broadcast(_live_event_payload(case_id, saved_state.live_traffic_capture))
        return _to_live_capture_response(case_id, saved_state.live_traffic_capture)

    @router.get("/{case_id}/traffic/live/preview", response_model=LiveTrafficPreviewResponse)
    def get_live_traffic_preview(case_id: str, limit: int = LIVE_CAPTURE_PREVIEW_DEFAULT_LIMIT) -> LiveTrafficPreviewResponse:
        try:
            persisted_state = workspace_runtime_service.get_live_traffic_capture_state(case_id)
            live_capture = traffic_capture_dispatcher.snapshot(case_id=case_id, persisted_state=persisted_state)
            if live_capture != persisted_state:
                workspace_runtime_service.save_live_traffic_capture_state(case_id, live_capture)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc

        preview_path = build_live_capture_preview_path(live_capture.output_path) if live_capture.output_path else None
        items = ()
        truncated = False
        if preview_path is not None and preview_path.exists():
            items, truncated = preview_service.load_live_preview(preview_path, limit=limit)
        return LiveTrafficPreviewResponse(
            case_id=case_id,
            status=live_capture.status,
            preview_path=str(preview_path) if preview_path is not None else None,
            truncated=truncated,
            items=[_to_flow_response(item) for item in items],
        )

    @router.post("/{case_id}/traffic/live/stop", response_model=LiveTrafficCaptureResponse)
    async def stop_live_traffic_capture(case_id: str) -> LiveTrafficCaptureResponse:
        try:
            persisted_state = workspace_runtime_service.get_live_traffic_capture_state(case_id)
            stopped = traffic_capture_dispatcher.stop(case_id=case_id, persisted_state=persisted_state)
            finalized = stopped
            if stopped.output_path is not None:
                for _ in range(LIVE_CAPTURE_ARTIFACT_POLL_ATTEMPTS):
                    if stopped.output_path.exists():
                        break
                    time.sleep(LIVE_CAPTURE_ARTIFACT_POLL_INTERVAL_SECONDS)
                if stopped.output_path.exists():
                    workspace_runtime_service.import_traffic_capture(
                        case_id,
                        str(stopped.output_path),
                        provenance_kind=LIVE_CAPTURE_PROVENANCE_KIND,
                    )
                    finalized = TrafficLiveCaptureState(
                        status="stopped",
                        session_id=stopped.session_id,
                        output_path=stopped.output_path,
                        message="已停止实时抓包，产物已保存。",
                    )
                else:
                    finalized = TrafficLiveCaptureState(
                        status="stopped",
                        session_id=stopped.session_id,
                        output_path=stopped.output_path,
                        message="已停止实时抓包，但未找到预期产物文件。",
                    )
            elif stopped.status == "stopped" and stopped.message is None:
                finalized = TrafficLiveCaptureState(
                    status="stopped",
                    session_id=stopped.session_id,
                    output_path=None,
                    message="已停止实时抓包。",
                )
            saved_state = workspace_runtime_service.save_live_traffic_capture_state(case_id, finalized)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        await hub.broadcast(_live_event_payload(case_id, saved_state.live_traffic_capture))
        return _to_live_capture_response(case_id, saved_state.live_traffic_capture)

    return router
