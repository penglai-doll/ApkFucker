from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.device_inventory_service import DeviceInventoryService
from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import JobService, SupportsStaticAnalyze
from apk_hacker.application.services.live_capture_runtime import resolve_live_capture_runtime
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.workbench_settings_service import WorkbenchSettingsService
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_registry_service import default_workspace_registry_path
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.infrastructure.integrations.jadx_launcher import open_in_jadx
from apk_hacker.infrastructure.integrations.jadx_launcher import resolve_jadx_gui_path
from apk_hacker.infrastructure.integrations.path_launcher import open_local_path
from apk_hacker.interfaces.api_fastapi.routes_cases import build_cases_router
from apk_hacker.interfaces.api_fastapi.routes_execution import build_execution_router
from apk_hacker.interfaces.api_fastapi.routes_reports import build_reports_router
from apk_hacker.interfaces.api_fastapi.routes_settings import build_settings_router
from apk_hacker.interfaces.api_fastapi.routes_traffic import build_traffic_router
from apk_hacker.interfaces.api_fastapi.routes_workspace import build_workspace_router
from apk_hacker.interfaces.api_fastapi.traffic_capture_dispatcher import TrafficCaptureDispatcher
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def build_app(
    *,
    default_workspace_root: Path | None = None,
    registry_path: Path | None = None,
    static_analyzer: SupportsStaticAnalyze | None = None,
    custom_scripts_root: Path | None = None,
    traffic_capture_command: str | None = None,
    environment_service: EnvironmentService | None = None,
    device_inventory_service: DeviceInventoryService | None = None,
    jadx_gui_resolver: Callable[[str | None], str | None] | None = None,
    jadx_opener: Callable[[str, Path], object] | None = None,
    path_opener: Callable[[Path], object] | None = None,
) -> FastAPI:
    hub = WebSocketHub()
    repo_root = Path(__file__).resolve().parents[4]
    workspace_root = default_workspace_root or repo_root / "workspaces"
    resolved_registry_path = registry_path or default_workspace_registry_path(workspace_root.parent)
    registry_service = WorkspaceRegistryService(resolved_registry_path)
    settings_service = WorkbenchSettingsService(resolved_registry_path.parent / "workbench-settings.json")
    queue_service = CaseQueueService()
    scripts_root = custom_scripts_root or workspace_root.parent / "custom-scripts"
    custom_script_service = CustomScriptService(scripts_root)
    job_service = JobService(static_analyzer=static_analyzer) if static_analyzer is not None else JobService()
    resolved_environment_service = environment_service or EnvironmentService()
    resolved_device_inventory_service = device_inventory_service or DeviceInventoryService()
    hook_plan_service = HookPlanService()
    report_export_service = ReportExportService()
    inspection_service = WorkspaceInspectionService(
        registry_service=registry_service,
        default_workspace_root=workspace_root,
        job_service=job_service,
        case_queue_service=queue_service,
        custom_script_service=custom_script_service,
        jadx_gui_resolver=jadx_gui_resolver or resolve_jadx_gui_path,
        jadx_opener=jadx_opener or open_in_jadx,
    )
    runtime_service = WorkspaceRuntimeService(
        registry_service=registry_service,
        default_workspace_root=workspace_root,
        inspection_service=inspection_service,
        custom_script_service=custom_script_service,
        hook_plan_service=hook_plan_service,
        report_export_service=report_export_service,
        case_queue_service=queue_service,
        environment_service=resolved_environment_service,
        device_inventory_service=resolved_device_inventory_service,
    )
    def resolve_current_live_capture_runtime():
        current_settings = settings_service.load()
        return resolve_live_capture_runtime(
            command_template=traffic_capture_command,
            resolver=resolved_environment_service.resolve_binary,
            listen_host=current_settings.live_capture_listen_host,
            listen_port=current_settings.live_capture_listen_port,
        )
    traffic_capture_dispatcher = TrafficCaptureDispatcher(
        command_template=traffic_capture_command,
        resolver=resolved_environment_service.resolve_binary,
        runtime_resolver=resolve_current_live_capture_runtime,
    )

    app = FastAPI(
        title="APKHacker Local API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(
        build_cases_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
            case_queue_service=queue_service,
            workspace_inspection_service=inspection_service,
        )
    )
    app.include_router(
        build_workspace_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
            case_queue_service=queue_service,
            workspace_inspection_service=inspection_service,
            workspace_runtime_service=runtime_service,
        )
    )
    app.include_router(
        build_execution_router(
            hub=hub,
            workspace_runtime_service=runtime_service,
        )
    )
    app.include_router(
        build_reports_router(
            workspace_runtime_service=runtime_service,
        )
    )
    app.include_router(
        build_traffic_router(
            hub=hub,
            workspace_runtime_service=runtime_service,
            traffic_capture_dispatcher=traffic_capture_dispatcher,
        )
    )
    app.include_router(
        build_settings_router(
            environment_service=resolved_environment_service,
            device_inventory_service=resolved_device_inventory_service,
            registry_service=registry_service,
            settings_service=settings_service,
            default_workspace_root=workspace_root,
            path_opener=path_opener or open_local_path,
            traffic_capture_command_template=traffic_capture_command,
        )
    )
    app.state.websocket_hub = hub
    app.state.workspace_registry_service = registry_service
    app.state.workspace_inspection_service = inspection_service
    app.state.traffic_capture_dispatcher = traffic_capture_dispatcher

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    return app
