from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.interfaces.api_fastapi.schemas import ReportExportResponse


def build_reports_router(
    *,
    workspace_runtime_service: WorkspaceRuntimeService,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["reports"])

    @router.post("/{case_id}/reports/export", response_model=ReportExportResponse)
    def export_report(case_id: str) -> ReportExportResponse:
        try:
            result = workspace_runtime_service.export_report(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found") from exc

        return ReportExportResponse(
            case_id=case_id,
            report_path=str(result.report_path),
            static_report_path=str(result.static_report_path) if result.static_report_path else None,
            last_execution_db_path=(
                str(result.state.last_execution_db_path) if result.state.last_execution_db_path else None
            ),
            last_execution_bundle_path=(
                str(result.state.last_execution_bundle_path) if result.state.last_execution_bundle_path else None
            ),
        )

    return router
