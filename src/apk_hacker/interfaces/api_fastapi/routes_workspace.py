from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.routes_cases import _known_workspace_roots
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceSummary


def _load_workspace_title(workspace_root: Path, case_id: str) -> str | None:
    workspace_json = workspace_root / case_id / "workspace.json"
    if not workspace_json.exists():
        return None

    try:
        payload = json.loads(workspace_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    title = payload.get("title")
    if not isinstance(title, str):
        return None

    normalized = title.strip()
    return normalized or None


def build_workspace_router(
    *,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["workspace"])

    @router.get("/{case_id}/workspace", response_model=WorkspaceSummary)
    def get_workspace(case_id: str) -> WorkspaceSummary:
        for workspace_root in _known_workspace_roots(registry_service, default_workspace_root):
            title = _load_workspace_title(workspace_root, case_id)
            if title is not None:
                return WorkspaceSummary(case_id=case_id, title=title)

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return router
