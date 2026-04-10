from __future__ import annotations

from fastapi import APIRouter


def build_settings_router() -> APIRouter:
    router = APIRouter(prefix="/api/settings", tags=["settings"])
    return router
