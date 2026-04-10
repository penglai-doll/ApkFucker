from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

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


def build_workspace_router(*, default_workspace_root: Path | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["workspace"])
    workspace_root = default_workspace_root or Path.cwd() / "workspaces"

    @router.get("/{case_id}/workspace", response_model=WorkspaceSummary)
    def get_workspace(case_id: str) -> WorkspaceSummary:
        title = _load_workspace_title(workspace_root, case_id)
        if title is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        return WorkspaceSummary(case_id=case_id, title=title)

    return router
