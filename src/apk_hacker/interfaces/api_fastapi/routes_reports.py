from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.routes_cases import _known_workspace_roots
from apk_hacker.interfaces.api_fastapi.schemas import ReportExportResponse


def _find_case_workspace(
    case_id: str,
    *,
    case_queue_service: CaseQueueService,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> Path | None:
    for workspace_root in _known_workspace_roots(registry_service, default_workspace_root):
        for item in case_queue_service.list_cases(workspace_root):
            if item.case_id == case_id:
                return item.workspace_root
    return None


def build_reports_router(
    *,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
    case_queue_service: CaseQueueService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["reports"])
    queue_service = case_queue_service or CaseQueueService()

    @router.post("/{case_id}/reports/export", response_model=ReportExportResponse)
    def export_report(case_id: str) -> ReportExportResponse:
        workspace_root = _find_case_workspace(
            case_id,
            case_queue_service=queue_service,
            registry_service=registry_service,
            default_workspace_root=default_workspace_root,
        )
        if workspace_root is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

        report_path = workspace_root / "reports" / f"{case_id}-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if not report_path.exists():
            report_path.write_text(
                f"# APKHacker Report\n\n- Case ID: {case_id}\n",
                encoding="utf-8",
            )
        return ReportExportResponse(case_id=case_id, report_path=str(report_path))

    return router
