from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceDetailResponse


def _load_workspace_record(workspace_root: Path, case_id: str) -> WorkspaceDetailResponse:
    case_queue_service = CaseQueueService()
    for item in case_queue_service.list_cases(workspace_root):
        if item.case_id != case_id:
            continue
        workspace_path = item.workspace_root
        sample_path = workspace_path / "sample" / "original.apk"
        metadata_path = workspace_path / "workspace.json"
        metadata = {}
        if metadata_path.exists():
            import json

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return WorkspaceDetailResponse(
            case_id=item.case_id,
            title=item.title,
            workspace_root=str(workspace_path),
            sample_path=str(sample_path),
            workspace_version=int(metadata.get("workspace_version", 1)),
            created_at=str(metadata.get("created_at", "")),
            updated_at=str(metadata.get("updated_at", "")),
            sample_filename=str(metadata.get("sample_filename", sample_path.name)),
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case workspace not found.")


def build_workspace_router(*, workspace_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["workspace"])

    @router.get("/{case_id}/workspace", response_model=WorkspaceDetailResponse)
    def get_workspace(case_id: str) -> WorkspaceDetailResponse:
        return _load_workspace_record(workspace_root, case_id)

    return router
