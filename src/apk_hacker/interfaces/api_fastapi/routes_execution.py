from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.routes_cases import _known_workspace_roots
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionStartResponse
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def _find_case_workspace(
    case_id: str,
    *,
    case_queue_service: CaseQueueService,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> Path | None:
    for workspace_root in _known_workspace_roots(registry_service, default_workspace_root):
        for item in case_queue_service.list_cases(workspace_root):
            if item.case_id == case_id:
                return item.workspace_root
    return None


def build_execution_router(
    *,
    hub: WebSocketHub,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
    case_queue_service: CaseQueueService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["execution"])
    queue_service = case_queue_service or CaseQueueService()

    @router.post(
        "/{case_id}/executions",
        response_model=ExecutionStartResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def start_execution(case_id: str) -> ExecutionStartResponse:
        workspace_root = _find_case_workspace(
            case_id,
            case_queue_service=queue_service,
            registry_service=registry_service,
            default_workspace_root=default_workspace_root,
        )
        if workspace_root is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

        event = {
            "type": "execution.started",
            "case_id": case_id,
            "status": "started",
        }
        await hub.broadcast(event)
        registry_service.set_last_opened_workspace(workspace_root)
        return ExecutionStartResponse(case_id=case_id, status="started")

    return router
