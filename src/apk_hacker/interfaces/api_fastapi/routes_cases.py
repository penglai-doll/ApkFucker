from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.interfaces.api_fastapi.schemas import (
    CaseListResponse,
    WorkspaceImportRequest,
    WorkspaceImportResponse,
    case_summary_from_item,
    workspace_import_response_from_record,
)


def build_cases_router(*, workspace_root: Path, db_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["cases"])
    case_queue_service = CaseQueueService()
    workspace_service = WorkspaceService()
    registry_service = WorkspaceRegistryService(db_root / "workspace-registry.json")

    @router.get("", response_model=CaseListResponse)
    def list_cases() -> CaseListResponse:
        items = [case_summary_from_item(item) for item in case_queue_service.list_cases(workspace_root)]
        return CaseListResponse(items=items)

    @router.post("/import", response_model=WorkspaceImportResponse, status_code=status.HTTP_201_CREATED)
    def import_case(payload: WorkspaceImportRequest) -> WorkspaceImportResponse:
        if not payload.sample_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample file not found.")
        created = workspace_service.create_workspace(
            sample_path=payload.sample_path,
            workspace_root=payload.workspace_root,
            title=payload.title,
        )
        registry_service.set_last_opened_workspace(created.workspace_root)
        return workspace_import_response_from_record(created)

    return router
