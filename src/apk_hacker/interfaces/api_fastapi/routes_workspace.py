from __future__ import annotations

from fastapi import APIRouter


def build_workspace_router() -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["workspace"])
    return router
