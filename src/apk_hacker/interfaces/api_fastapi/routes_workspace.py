from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.routes_cases import _known_workspace_roots
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceSummary


def _load_workspace_title(workspace_root: Path, case_id: str) -> str | None:
    for workspace_json in workspace_root.glob("*/workspace.json"):
        try:
            payload = json.loads(workspace_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue

        candidate_case_id = payload.get("case_id")
        title = payload.get("title")
        if not isinstance(candidate_case_id, str) or not isinstance(title, str):
            continue
        if candidate_case_id.strip() != case_id:
            continue

        normalized = title.strip()
        if normalized:
            return normalized

    return None


def build_workspace_router(
    *,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
    case_queue_service: CaseQueueService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["workspace"])
    queue_service = case_queue_service or CaseQueueService()

    @router.get("/{case_id}/workspace", response_model=WorkspaceSummary)
    def get_workspace(case_id: str) -> WorkspaceSummary:
        for workspace_root in _known_workspace_roots(registry_service, default_workspace_root):
            items = queue_service.list_cases(workspace_root)
            for item in items:
                if item.case_id != case_id:
                    continue
                title = _load_workspace_title(workspace_root, case_id)
                if title is not None:
                    return WorkspaceSummary(case_id=case_id, title=title)

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return router
