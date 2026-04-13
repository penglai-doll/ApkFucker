from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionStartRequest
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionStartResponse
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def build_execution_router(
    *,
    hub: WebSocketHub,
    workspace_runtime_service: WorkspaceRuntimeService,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["execution"])

    @router.post(
        "/{case_id}/executions",
        response_model=ExecutionStartResponse,
    )
    async def start_execution(
        case_id: str,
        payload: ExecutionStartRequest | None = None,
    ) -> ExecutionStartResponse:
        execution_mode = payload.execution_mode if payload is not None else None
        resolved_mode = execution_mode or "fake_backend"
        try:
            await hub.broadcast(
                {
                    "type": "execution.started",
                    "case_id": case_id,
                    "status": "started",
                    "execution_mode": resolved_mode,
                }
            )
            result = workspace_runtime_service.execute_current_plan(case_id, execution_mode=resolved_mode)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except ExecutionBackendUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        await hub.broadcast(
            {
                "type": "execution.completed",
                "case_id": case_id,
                "status": "completed",
                "execution_mode": result.execution_mode,
                "run_id": result.run_id,
                "event_count": result.event_count,
                "db_path": str(result.db_path),
                "bundle_path": str(result.bundle_path),
                "executed_backend_label": result.executed_backend_label,
            }
        )
        return ExecutionStartResponse(
            case_id=case_id,
            status="completed",
            execution_mode=result.execution_mode,
            run_id=result.run_id,
            event_count=result.event_count,
            db_path=str(result.db_path),
            bundle_path=str(result.bundle_path),
            executed_backend_label=result.executed_backend_label,
        )

    return router
