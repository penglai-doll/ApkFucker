from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.interfaces.api_fastapi.schemas import CaseListResponse
from apk_hacker.interfaces.api_fastapi.schemas import CaseSummary
from apk_hacker.interfaces.api_fastapi.schemas import ImportCaseRequest
from apk_hacker.interfaces.api_fastapi.schemas import ImportedCaseResponse


def build_cases_router(
    *,
    case_queue_service: CaseQueueService | None = None,
    workspace_service: WorkspaceService | None = None,
    default_workspace_root: Path | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["cases"])
    queue_service = case_queue_service or CaseQueueService()
    create_workspace_service = workspace_service or WorkspaceService()
    workspace_root = default_workspace_root or Path.cwd() / "workspaces"

    @router.get("", response_model=CaseListResponse)
    def list_cases() -> CaseListResponse:
        items = queue_service.list_cases(workspace_root)
        return CaseListResponse(
            items=[
                CaseSummary(
                    case_id=item.case_id,
                    title=item.title,
                    workspace_root=str(item.workspace_root),
                )
                for item in items
            ]
        )

    @router.post("/import", response_model=ImportedCaseResponse, status_code=status.HTTP_201_CREATED)
    def import_case(payload: ImportCaseRequest) -> ImportedCaseResponse:
        nonlocal workspace_root

        target_root = Path(payload.workspace_root).expanduser()
        record = create_workspace_service.create_workspace(
            sample_path=Path(payload.sample_path).expanduser(),
            workspace_root=target_root,
            title=payload.title,
        )
        workspace_root = target_root
        return ImportedCaseResponse(
            case_id=record.case_id,
            title=record.title,
            workspace_root=str(record.workspace_root),
            sample_path=str(record.sample_path),
        )

    return router
