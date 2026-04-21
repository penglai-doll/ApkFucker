from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.domain.models.execution import ExecutionRuntimeOptions
from apk_hacker.interfaces.api_fastapi.execution_dispatcher import ExecutionConflictError
from apk_hacker.interfaces.api_fastapi.execution_dispatcher import ExecutionDispatcher
from apk_hacker.interfaces.api_fastapi.execution_dispatcher import ExecutionNotRunningError
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionCancelResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionHistoryEntryResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionHistoryResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionPreflightRequest
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionPreflightResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionStartRequest
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionStartResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceEventResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceEventsResponse
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def build_execution_router(
    *,
    hub: WebSocketHub,
    workspace_runtime_service: WorkspaceRuntimeService,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["execution"])
    dispatcher = ExecutionDispatcher(
        hub=hub,
        workspace_runtime_service=workspace_runtime_service,
    )

    def _to_workspace_event(case_id: str, event) -> WorkspaceEventResponse:
        message_parts = [f"{event.class_name}.{event.method_name}"]
        if event.return_value:
            message_parts.append(event.return_value)
        return WorkspaceEventResponse(
            type="execution.event",
            case_id=case_id,
            timestamp=event.timestamp,
            message=" · ".join(message_parts),
            payload={
                "event_type": event.event_type,
                "source": event.source,
                "class_name": event.class_name,
                "method_name": event.method_name,
                "arguments": list(event.arguments),
                "return_value": event.return_value,
                "stacktrace": event.stacktrace,
                "raw_payload": dict(event.raw_payload),
            },
        )

    @router.post(
        "/{case_id}/executions/preflight",
        response_model=ExecutionPreflightResponse,
    )
    def preflight_execution(
        case_id: str,
        payload: ExecutionPreflightRequest | None = None,
    ) -> ExecutionPreflightResponse:
        runtime_options = (
            ExecutionRuntimeOptions(
                device_serial=payload.device_serial or "",
                frida_server_binary_path=payload.frida_server_binary_path or "",
                frida_server_remote_path=payload.frida_server_remote_path or "",
                frida_session_seconds=payload.frida_session_seconds or "",
            )
            if payload is not None
            else ExecutionRuntimeOptions()
        )
        try:
            result = workspace_runtime_service.build_execution_preflight(
                case_id,
                execution_mode=payload.execution_mode if payload is not None else None,
                runtime_options=runtime_options,
            )
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        return ExecutionPreflightResponse(
            case_id=result.case_id,
            ready=result.ready,
            execution_mode=result.execution_mode,
            executed_backend_key=result.executed_backend_key,
            executed_backend_label=result.executed_backend_label,
            detail=result.detail,
        )

    @router.get(
        "/{case_id}/executions/history",
        response_model=ExecutionHistoryResponse,
    )
    def get_execution_history(case_id: str, limit: int = 20) -> ExecutionHistoryResponse:
        try:
            items = workspace_runtime_service.get_execution_history(case_id, limit=limit)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        return ExecutionHistoryResponse(
            case_id=case_id,
            items=[
                ExecutionHistoryEntryResponse(
                    history_id=item.history_id,
                    run_id=item.run_id,
                    execution_mode=item.execution_mode,
                    executed_backend_key=item.executed_backend_key,
                    status=item.status,
                    stage=item.stage,
                    error_code=item.error_code,
                    error_message=item.error_message,
                    event_count=item.event_count,
                    db_path=str(item.db_path) if item.db_path else None,
                    bundle_path=str(item.bundle_path) if item.bundle_path else None,
                    started_at=item.started_at,
                    updated_at=item.updated_at,
                )
                for item in items
            ],
        )

    @router.get(
        "/{case_id}/executions/history/{history_id}/events",
        response_model=WorkspaceEventsResponse,
    )
    def get_execution_history_events(case_id: str, history_id: str, limit: int = 20) -> WorkspaceEventsResponse:
        try:
            events = workspace_runtime_service.get_execution_events(case_id, limit=limit, history_id=history_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution history not found") from exc
        return WorkspaceEventsResponse(
            case_id=case_id,
            items=[_to_workspace_event(case_id, event) for event in events],
        )

    @router.post(
        "/{case_id}/executions",
        response_model=ExecutionStartResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def start_execution(
        case_id: str,
        payload: ExecutionStartRequest | None = None,
    ) -> ExecutionStartResponse:
        execution_mode = payload.execution_mode if payload is not None else None
        runtime_options = (
            ExecutionRuntimeOptions(
                device_serial=payload.device_serial or "",
                frida_server_binary_path=payload.frida_server_binary_path or "",
                frida_server_remote_path=payload.frida_server_remote_path or "",
                frida_session_seconds=payload.frida_session_seconds or "",
            )
            if payload is not None
            else ExecutionRuntimeOptions()
        )
        resolved_mode = execution_mode or "fake_backend"
        try:
            workspace_runtime_service.validate_execution_ready(
                case_id,
                execution_mode=resolved_mode,
                runtime_options=runtime_options,
            )
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        try:
            return await dispatcher.start_execution(case_id, resolved_mode, runtime_options)
        except ExecutionConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post(
        "/{case_id}/executions/cancel",
        response_model=ExecutionCancelResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def cancel_execution(case_id: str) -> ExecutionCancelResponse:
        try:
            workspace_runtime_service.get_state(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        try:
            return await dispatcher.cancel_execution(case_id)
        except ExecutionNotRunningError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return router
