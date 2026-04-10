from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.interfaces.api_fastapi.schemas import CaseListResponse, case_summary_from_item


def build_cases_router(*, workspace_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["cases"])
    case_queue_service = CaseQueueService()

    @router.get("", response_model=CaseListResponse)
    def list_cases() -> CaseListResponse:
        items = [case_summary_from_item(item) for item in case_queue_service.list_cases(workspace_root)]
        return CaseListResponse(items=items)

    return router
