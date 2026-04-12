from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.execution_presets import build_execution_preset_statuses
from apk_hacker.application.services.execution_presets import resolve_real_device_backend
from apk_hacker.interfaces.api_fastapi.schemas import EnvironmentResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionPresetStatusResponse
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.schemas import HealthResponse
from apk_hacker.interfaces.api_fastapi.schemas import StartupSettingsResponse
from apk_hacker.interfaces.api_fastapi.schemas import ToolStatusResponse


def _load_workspace_metadata(workspace_root: Path | None) -> tuple[str | None, str | None]:
    if workspace_root is None:
        return (None, None)

    workspace_json = workspace_root / "workspace.json"
    if not workspace_json.exists():
        return (None, None)

    try:
        payload = json.loads(workspace_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return (None, None)
    if not isinstance(payload, dict):
        return (None, None)

    case_id = payload.get("case_id")
    title = payload.get("title")
    normalized_case_id = case_id.strip() if isinstance(case_id, str) else None
    normalized_title = title.strip() if isinstance(title, str) else None
    return (
        normalized_case_id or None,
        normalized_title or None,
    )


def build_settings_router(
    *,
    environment_service: EnvironmentService,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> APIRouter:
    router = APIRouter(prefix="/api/settings", tags=["settings"])

    @router.get("/startup", response_model=StartupSettingsResponse)
    def get_startup_settings() -> StartupSettingsResponse:
        registry = registry_service.load()
        last_workspace_root = registry.last_opened_workspace
        case_id, title = _load_workspace_metadata(last_workspace_root)
        launch_view = "workspace" if case_id is not None and title is not None else "queue"
        return StartupSettingsResponse(
            launch_view=launch_view,
            last_workspace_root=str(last_workspace_root) if last_workspace_root is not None else None,
            case_id=case_id,
            title=title,
        )

    @router.get("/health", response_model=HealthResponse)
    def get_health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="local-api",
            default_workspace_root=str(default_workspace_root),
        )

    @router.get("/environment", response_model=EnvironmentResponse)
    def get_environment() -> EnvironmentResponse:
        snapshot = environment_service.inspect()
        preset_statuses = build_execution_preset_statuses(snapshot)
        return EnvironmentResponse(
            summary=snapshot.summary,
            recommended_execution_mode=resolve_real_device_backend(preset_statuses),
            tools=[
                ToolStatusResponse(
                    name=tool.name,
                    label=tool.label,
                    available=tool.available,
                    path=tool.path,
                )
                for tool in snapshot.tools
            ],
            execution_presets=[
                ExecutionPresetStatusResponse(
                    key=status.key,
                    label=status.label,
                    available=status.available,
                    detail=status.detail,
                )
                for status in preset_statuses
            ],
        )

    return router
