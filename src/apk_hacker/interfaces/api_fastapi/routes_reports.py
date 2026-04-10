from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.report_export_service import ExportableReport, ReportExportService
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.interfaces.api_fastapi.schemas import ReportExportResponse


def build_reports_router(*, workspace_root: Path, db_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["reports"])
    case_queue_service = CaseQueueService()
    report_export_service = ReportExportService()

    @router.post("/{case_id}/reports/export", response_model=ReportExportResponse)
    def export_report(case_id: str) -> ReportExportResponse:
        for item in case_queue_service.list_cases(workspace_root):
            if item.case_id != case_id:
                continue
            output_path = db_root / "reports" / f"{case_id}-merged-report.md"
            exportable = ExportableReport(
                job_id=None,
                summary_text=f"Report exported for case {case_id}.",
                sample_path=item.workspace_root / "sample" / "original.apk",
                static_inputs=None,
                hook_plan=HookPlan(items=()),
                hook_events=(),
                traffic_capture=None,
            )
            exported_path = report_export_service.export_markdown(exportable, output_path)
            return ReportExportResponse(case_id=case_id, report_path=str(exported_path))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case workspace not found.")

    return router
