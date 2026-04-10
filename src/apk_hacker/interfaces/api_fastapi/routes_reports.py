from __future__ import annotations

from fastapi import APIRouter


def build_reports_router() -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["reports"])
    return router
