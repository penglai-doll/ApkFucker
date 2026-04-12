from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI, WebSocket

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.job_service import JobService, SupportsStaticAnalyze
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_registry_service import default_workspace_registry_path
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.infrastructure.integrations.jadx_launcher import open_in_jadx
from apk_hacker.infrastructure.integrations.jadx_launcher import resolve_jadx_gui_path
from apk_hacker.interfaces.api_fastapi.routes_cases import build_cases_router
from apk_hacker.interfaces.api_fastapi.routes_execution import build_execution_router
from apk_hacker.interfaces.api_fastapi.routes_reports import build_reports_router
from apk_hacker.interfaces.api_fastapi.routes_settings import build_settings_router
from apk_hacker.interfaces.api_fastapi.routes_workspace import build_workspace_router
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def build_app(
    *,
    default_workspace_root: Path | None = None,
    registry_path: Path | None = None,
    static_analyzer: SupportsStaticAnalyze | None = None,
    custom_scripts_root: Path | None = None,
    environment_service: EnvironmentService | None = None,
    jadx_gui_resolver: Callable[[str | None], str | None] | None = None,
    jadx_opener: Callable[[str, Path], object] | None = None,
) -> FastAPI:
    hub = WebSocketHub()
    repo_root = Path(__file__).resolve().parents[4]
    workspace_root = default_workspace_root or repo_root / "workspaces"
    resolved_registry_path = registry_path or default_workspace_registry_path(workspace_root.parent)
    registry_service = WorkspaceRegistryService(resolved_registry_path)
    queue_service = CaseQueueService()
    scripts_root = custom_scripts_root or workspace_root.parent / "custom-scripts"
    custom_script_service = CustomScriptService(scripts_root)
    job_service = JobService(static_analyzer=static_analyzer) if static_analyzer is not None else JobService()
    resolved_environment_service = environment_service or EnvironmentService()
    inspection_service = WorkspaceInspectionService(
        registry_service=registry_service,
        default_workspace_root=workspace_root,
        job_service=job_service,
        case_queue_service=queue_service,
        custom_script_service=custom_script_service,
        jadx_gui_resolver=jadx_gui_resolver or resolve_jadx_gui_path,
        jadx_opener=jadx_opener or open_in_jadx,
    )

    app = FastAPI(
        title="APKHacker Local API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(
        build_cases_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
            case_queue_service=queue_service,
        )
    )
    app.include_router(
        build_workspace_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
            case_queue_service=queue_service,
            workspace_inspection_service=inspection_service,
        )
    )
    app.include_router(
        build_execution_router(
            hub=hub,
            registry_service=registry_service,
            default_workspace_root=workspace_root,
            case_queue_service=queue_service,
        )
    )
    app.include_router(
        build_reports_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
        )
    )
    app.include_router(
        build_settings_router(
            environment_service=resolved_environment_service,
            registry_service=registry_service,
            default_workspace_root=workspace_root,
        )
    )
    app.state.websocket_hub = hub
    app.state.workspace_registry_service = registry_service
    app.state.workspace_inspection_service = inspection_service

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    return app
