from __future__ import annotations

from fastapi import APIRouter

from apk_hacker.interfaces.api_fastapi.schemas import CaseListResponse


def build_cases_router() -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["cases"])

    @router.get("", response_model=CaseListResponse)
    def list_cases() -> CaseListResponse:
        return CaseListResponse(items=[])

    return router
