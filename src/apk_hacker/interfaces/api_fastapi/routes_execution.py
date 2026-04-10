from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionCreateRequest, ExecutionCreateResponse


def build_execution_router(*, workspace_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["execution"])
    case_queue_service = CaseQueueService()

    @router.post("/{case_id}/executions", response_model=ExecutionCreateResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_execution(case_id: str, payload: ExecutionCreateRequest) -> ExecutionCreateResponse:
        if not any(item.case_id == case_id for item in case_queue_service.list_cases(workspace_root)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case workspace not found.")
        return ExecutionCreateResponse(
            case_id=case_id,
            status="started",
            mode=payload.mode,
            job_id=str(uuid4()),
        )

    return router
