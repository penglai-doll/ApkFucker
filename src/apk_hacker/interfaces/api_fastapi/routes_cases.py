from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.interfaces.api_fastapi.schemas import CaseListResponse
from apk_hacker.interfaces.api_fastapi.schemas import CaseSummary
from apk_hacker.interfaces.api_fastapi.schemas import ImportCaseRequest
from apk_hacker.interfaces.api_fastapi.schemas import ImportedCaseResponse


def _known_workspace_roots(
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> tuple[Path, ...]:
    registry = registry_service.load()
    roots: list[Path] = []
    seen: set[Path] = set()

    for root in (default_workspace_root, *registry.known_workspace_roots):
        normalized_root = root.expanduser()
        if normalized_root in seen:
            continue
        seen.add(normalized_root)
        roots.append(normalized_root)

    return tuple(roots)


def build_cases_router(
    *,
    case_queue_service: CaseQueueService | None = None,
    workspace_service: WorkspaceService | None = None,
    workspace_inspection_service: WorkspaceInspectionService | None = None,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["cases"])
    queue_service = case_queue_service or CaseQueueService()
    create_workspace_service = workspace_service or WorkspaceService()
    inspection_service = workspace_inspection_service

    @router.get("", response_model=CaseListResponse)
    def list_cases() -> CaseListResponse:
        items_by_case_id: dict[str, CaseSummary] = {}
        for workspace_root in _known_workspace_roots(registry_service, default_workspace_root):
            items = queue_service.list_cases(workspace_root)
            for item in items:
                if item.case_id in items_by_case_id:
                    continue
                items_by_case_id[item.case_id] = CaseSummary(
                    case_id=item.case_id,
                    title=item.title,
                    workspace_root=str(item.workspace_root),
                )
        return CaseListResponse(
            items=list(items_by_case_id.values())
        )

    @router.post("/import", response_model=ImportedCaseResponse, status_code=status.HTTP_201_CREATED)
    def import_case(payload: ImportCaseRequest) -> ImportedCaseResponse:
        sample_path = Path(payload.sample_path).expanduser()
        if not sample_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample file not found")

        target_root = Path(payload.workspace_root).expanduser()
        record = create_workspace_service.create_workspace(
            sample_path=sample_path,
            workspace_root=target_root,
            title=payload.title,
        )
        if inspection_service is not None:
            try:
                inspection_service.get_detail(record.case_id)
            except Exception:
                # Import should remain available even when the first static pass fails.
                # The workspace can still be reopened later after the environment or sample is fixed.
                pass
        registry_service.remember_workspace_root(target_root)
        registry_service.set_last_opened_workspace(record.workspace_root)
        return ImportedCaseResponse(
            case_id=record.case_id,
            title=record.title,
            workspace_root=str(record.workspace_root),
            sample_path=str(record.sample_path),
        )

    return router
