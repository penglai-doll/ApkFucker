from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from fastapi import HTTPException
from fastapi import APIRouter
from fastapi import status

from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.environment_service import build_live_capture_network_summary
from apk_hacker.application.services.environment_service import build_ssl_hook_guidance
from apk_hacker.application.services.device_inventory_service import DeviceInventoryService
from apk_hacker.application.services.execution_presets import build_execution_preset_statuses
from apk_hacker.application.services.execution_presets import resolve_real_device_backend
from apk_hacker.application.services.live_capture_runtime import resolve_live_capture_runtime
from apk_hacker.application.services.workbench_settings_service import WorkbenchSettings
from apk_hacker.application.services.workbench_settings_service import WorkbenchSettingsService
from apk_hacker.interfaces.api_fastapi.schemas import EnvironmentResponse
from apk_hacker.interfaces.api_fastapi.schemas import ConnectedDeviceResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionPresetStatusResponse
from apk_hacker.interfaces.api_fastapi.schemas import GuidanceStepResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanSourceSummary
from apk_hacker.interfaces.api_fastapi.schemas import LiveCaptureRuntimeResponse
from apk_hacker.interfaces.api_fastapi.schemas import LiveCaptureNetworkSummaryResponse
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.schemas import HealthResponse
from apk_hacker.interfaces.api_fastapi.schemas import OpenPathRequest
from apk_hacker.interfaces.api_fastapi.schemas import OpenPathResponse
from apk_hacker.interfaces.api_fastapi.schemas import RuntimeSettingsResponse
from apk_hacker.interfaces.api_fastapi.schemas import RuntimeSettingsUpdateRequest
from apk_hacker.interfaces.api_fastapi.schemas import SuggestedHookTemplateResponse
from apk_hacker.interfaces.api_fastapi.schemas import SslHookGuidanceResponse
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


def _to_runtime_settings_response(settings: WorkbenchSettings) -> RuntimeSettingsResponse:
    return RuntimeSettingsResponse(
        execution_mode=settings.execution_mode,
        device_serial=settings.device_serial,
        frida_server_binary_path=settings.frida_server_binary_path,
        frida_server_remote_path=settings.frida_server_remote_path,
        frida_session_seconds=settings.frida_session_seconds,
        live_capture_listen_host=settings.live_capture_listen_host,
        live_capture_listen_port=settings.live_capture_listen_port,
    )


def _step_to_text(title: str, detail: str) -> str:
    return f"{title}：{detail}"


def _to_guidance_step_response(step) -> GuidanceStepResponse:
    return GuidanceStepResponse(
        key=step.key,
        title=step.title,
        detail=step.detail,
        emphasis=step.emphasis,
    )


def build_settings_router(
    *,
    environment_service: EnvironmentService,
    device_inventory_service: DeviceInventoryService,
    registry_service: WorkspaceRegistryService,
    settings_service: WorkbenchSettingsService,
    default_workspace_root: Path,
    path_opener: Callable[[Path], object],
    traffic_capture_command_template: str | None = None,
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

    @router.get("/runtime", response_model=RuntimeSettingsResponse)
    def get_runtime_settings() -> RuntimeSettingsResponse:
        return _to_runtime_settings_response(settings_service.load())

    @router.put("/runtime", response_model=RuntimeSettingsResponse)
    def update_runtime_settings(payload: RuntimeSettingsUpdateRequest) -> RuntimeSettingsResponse:
        current = settings_service.load()
        updated = WorkbenchSettings(
            sample_path=current.sample_path,
            execution_mode=str(payload.execution_mode or current.execution_mode or "fake_backend"),
            device_serial=str(payload.device_serial if payload.device_serial is not None else current.device_serial),
            frida_server_binary_path=str(
                payload.frida_server_binary_path
                if payload.frida_server_binary_path is not None
                else current.frida_server_binary_path
            ),
            frida_server_remote_path=str(
                payload.frida_server_remote_path
                if payload.frida_server_remote_path is not None
                else current.frida_server_remote_path
            ),
            frida_session_seconds=str(
                payload.frida_session_seconds
                if payload.frida_session_seconds is not None
                else current.frida_session_seconds
            ),
            live_capture_listen_host=str(
                payload.live_capture_listen_host
                if payload.live_capture_listen_host is not None
                else current.live_capture_listen_host
            ),
            live_capture_listen_port=str(
                payload.live_capture_listen_port
                if payload.live_capture_listen_port is not None
                else current.live_capture_listen_port
            ),
        )
        settings_service.save(updated)
        return _to_runtime_settings_response(updated)

    @router.get("/environment", response_model=EnvironmentResponse)
    def get_environment() -> EnvironmentResponse:
        snapshot = environment_service.inspect()
        device_snapshot = device_inventory_service.inspect()
        preset_statuses = build_execution_preset_statuses(snapshot)
        runtime_settings = settings_service.load()
        live_capture_runtime = resolve_live_capture_runtime(
            command_template=traffic_capture_command_template,
            resolver=environment_service.resolve_binary,
            listen_host=runtime_settings.live_capture_listen_host,
            listen_port=runtime_settings.live_capture_listen_port,
        )
        network_summary = build_live_capture_network_summary(snapshot, live_capture_runtime)
        ssl_hook_guidance = build_ssl_hook_guidance(snapshot, live_capture_runtime)
        return EnvironmentResponse(
            summary=snapshot.summary,
            recommended_execution_mode=resolve_real_device_backend(preset_statuses),
            recommended_device_serial=device_snapshot.recommended_serial,
            tools=[
                ToolStatusResponse(
                    name=tool.name,
                    label=tool.label,
                    available=tool.available,
                    path=tool.path,
                )
                for tool in snapshot.tools
            ],
            connected_devices=[
                ConnectedDeviceResponse(
                    serial=device.serial,
                    state=device.state,
                    model=device.model,
                    product=device.product,
                    device=device.device,
                    transport_id=device.transport_id,
                    abi=device.abi,
                    rooted=device.rooted,
                    frida_visible=device.frida_visible,
                    package_installed=device.package_installed,
                    is_emulator=device.is_emulator,
                )
                for device in device_snapshot.devices
            ],
            live_capture=LiveCaptureRuntimeResponse(
                available=live_capture_runtime.available,
                source=live_capture_runtime.source,
                detail=live_capture_runtime.detail,
                listen_host=live_capture_runtime.listen_host,
                listen_port=live_capture_runtime.listen_port,
                help_text=live_capture_runtime.help_text,
                proxy_address_hint=live_capture_runtime.proxy_address_hint,
                install_url=live_capture_runtime.install_url,
                certificate_path=live_capture_runtime.certificate_path,
                certificate_directory_path=live_capture_runtime.certificate_directory_path,
                certificate_exists=live_capture_runtime.certificate_exists,
                certificate_help_text=live_capture_runtime.certificate_help_text,
                proxy_ready=live_capture_runtime.proxy_ready,
                certificate_ready=live_capture_runtime.certificate_ready,
                https_capture_ready=live_capture_runtime.https_capture_ready,
                setup_steps=[_step_to_text(step.title, step.detail) for step in live_capture_runtime.setup_steps],
                proxy_steps=[_step_to_text(step.title, step.detail) for step in live_capture_runtime.proxy_steps],
                certificate_steps=[
                    _step_to_text(step.title, step.detail) for step in live_capture_runtime.certificate_steps
                ],
                recommended_actions=list(live_capture_runtime.recommended_actions),
                setup_step_details=[_to_guidance_step_response(step) for step in live_capture_runtime.setup_steps],
                proxy_step_details=[_to_guidance_step_response(step) for step in live_capture_runtime.proxy_steps],
                certificate_step_details=[
                    _to_guidance_step_response(step) for step in live_capture_runtime.certificate_steps
                ],
                network_summary=LiveCaptureNetworkSummaryResponse(
                    supports_https_intercept=network_summary.supports_https_intercept,
                    supports_packet_capture=network_summary.supports_packet_capture,
                    supports_ssl_hooking=network_summary.supports_ssl_hooking,
                    proxy_ready=network_summary.proxy_ready,
                    certificate_ready=network_summary.certificate_ready,
                    https_capture_ready=network_summary.https_capture_ready,
                ),
                ssl_hook_guidance=SslHookGuidanceResponse(
                    recommended=ssl_hook_guidance.recommended,
                    summary=ssl_hook_guidance.summary,
                    reason=ssl_hook_guidance.reason,
                    suggested_templates=list(ssl_hook_guidance.suggested_templates),
                    suggested_template_entries=[
                        SuggestedHookTemplateResponse(
                            template_id=entry.template_id,
                            template_name=entry.template_name,
                            plugin_id=entry.plugin_id,
                        )
                        for entry in ssl_hook_guidance.suggested_template_entries
                    ],
                    suggested_terms=list(ssl_hook_guidance.suggested_terms),
                ),
            ),
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

    @router.post("/open-path", response_model=OpenPathResponse)
    def open_path(payload: OpenPathRequest) -> OpenPathResponse:
        target_path = Path(payload.path).expanduser()
        if not target_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")
        path_opener(target_path)
        return OpenPathResponse(path=str(target_path), status="opened")

    return router
