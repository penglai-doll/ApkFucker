from __future__ import annotations

from fastapi import APIRouter


def build_execution_router() -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["execution"])
    return router
