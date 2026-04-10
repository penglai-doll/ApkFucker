from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from apk_hacker.application.services.workbench_settings_service import WorkbenchSettingsService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.schemas import StartupSettingsResponse, startup_settings_response


def build_settings_router(*, db_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/settings", tags=["settings"])
    settings_service = WorkbenchSettingsService(db_root / "workbench-settings.json")
    registry_service = WorkspaceRegistryService(db_root / "workspace-registry.json")

    @router.get("/startup", response_model=StartupSettingsResponse)
    def get_startup_settings() -> StartupSettingsResponse:
        registry = registry_service.load()
        settings = settings_service.load()
        return startup_settings_response(
            settings=settings,
            last_workspace_root=registry.last_opened_workspace,
        )

    return router
