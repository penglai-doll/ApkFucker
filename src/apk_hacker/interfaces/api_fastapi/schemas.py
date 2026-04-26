from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    workspace_root: str


class CaseListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CaseSummary] = Field(default_factory=list)


class ImportCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_path: str
    workspace_root: str
    title: str | None = None


class ImportedCaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    workspace_root: str
    sample_path: str


class WorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    view: str = "workspace"


class CustomScriptSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str
    name: str
    script_path: str


class CustomScriptCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    content: str


class CustomScriptUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    content: str


class CustomScriptContentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str
    name: str
    script_path: str
    content: str


class CustomScriptListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CustomScriptSummary] = Field(default_factory=list)


class HookPlanMethodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: str
    method_name: str
    parameter_types: list[str] = Field(default_factory=list)
    return_type: str
    source_path: str
    line_hint: int | None = None
    declaration: str | None = None
    source_preview: str | None = None
    tags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    is_constructor: bool = False
    overload_count: int = 1


class HookPlanRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str


class HookPlanTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    template_name: str
    plugin_id: str


class HookPlanCustomScriptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str


class HookPlanItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    inject_order: int | None = Field(default=None, ge=1)


class HookPlanItemMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction: str


class HookPlanTargetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    class_name: str
    method_name: str
    parameter_types: list[str] = Field(default_factory=list)
    return_type: str
    source_origin: str
    notes: str = ""


class HookPlanSourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    kind: str
    method: WorkspaceMethodSummary | None = None
    script_name: str | None = None
    script_path: str | None = None
    template_id: str | None = None
    template_name: str | None = None
    plugin_id: str | None = None
    reason: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    source_signals: list[str] = Field(default_factory=list)
    template_event_types: list[str] = Field(default_factory=list)
    template_category: str | None = None
    requires_root: bool = False
    supports_offline: bool = True


class HookPlanItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    kind: str
    enabled: bool
    inject_order: int
    source: HookPlanSourceSummary | None = None
    target: HookPlanTargetSummary | None = None
    render_context: dict[str, object] = Field(default_factory=dict)
    plugin_id: str | None = None
    template_id: str | None = None
    reason: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    source_signals: list[str] = Field(default_factory=list)
    template_event_types: list[str] = Field(default_factory=list)
    template_category: str | None = None
    requires_root: bool = False
    supports_offline: bool = True


class WorkspaceRuntimeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_count: int = 0
    last_execution_run_id: str | None = None
    last_execution_mode: str | None = None
    last_executed_backend_key: str | None = None
    last_execution_status: str | None = None
    last_execution_stage: str | None = None
    last_execution_error_code: str | None = None
    last_execution_error_message: str | None = None
    last_execution_event_count: int | None = None
    last_execution_result_path: str | None = None
    last_execution_db_path: str | None = None
    last_execution_bundle_path: str | None = None
    last_report_path: str | None = None
    traffic_capture_source_path: str | None = None
    traffic_capture_summary_path: str | None = None
    traffic_capture_flow_count: int | None = None
    traffic_capture_suspicious_count: int | None = None
    live_traffic_status: str | None = None
    live_traffic_session_id: str | None = None
    live_traffic_artifact_path: str | None = None
    live_traffic_output_path: str | None = None
    live_traffic_preview_path: str | None = None
    live_traffic_message: str | None = None


class HookPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    updated_at: str
    selected_hook_sources: list[HookPlanSourceSummary] = Field(default_factory=list)
    items: list[HookPlanItemResponse] = Field(default_factory=list)
    execution_count: int = 0
    last_execution_run_id: str | None = None
    last_execution_mode: str | None = None
    last_executed_backend_key: str | None = None
    last_execution_status: str | None = None
    last_execution_stage: str | None = None
    last_execution_error_code: str | None = None
    last_execution_error_message: str | None = None
    last_execution_event_count: int | None = None
    last_execution_result_path: str | None = None
    last_execution_db_path: str | None = None
    last_execution_bundle_path: str | None = None
    last_report_path: str | None = None


class WorkspaceEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    case_id: str | None = None
    status: str | None = None
    artifact_path: str | None = None
    stage: str | None = None
    run_id: str | None = None
    execution_mode: str | None = None
    executed_backend_key: str | None = None
    event_count: int | None = None
    db_path: str | None = None
    bundle_path: str | None = None
    executed_backend_label: str | None = None
    error_code: str | None = None
    message: str | None = None
    timestamp: str | None = None
    schema_version: str | None = None
    job_id: str | None = None
    session_id: str | None = None
    event_type: str | None = None
    hook_type: str | None = None
    source: str | None = None
    source_script: str | None = None
    class_name: str | None = None
    method_name: str | None = None
    arguments: list[str] = Field(default_factory=list)
    return_value: str | None = None
    stacktrace: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class WorkspaceEventsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    items: list[WorkspaceEventResponse] = Field(default_factory=list)


class ExecutionPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: str | None = None
    device_serial: str | None = None
    frida_server_binary_path: str | None = None
    frida_server_remote_path: str | None = None
    frida_session_seconds: str | None = None


class ExecutionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    ready: bool
    execution_mode: str
    executed_backend_key: str | None = None
    executed_backend_label: str | None = None
    detail: str


class ConnectedDeviceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serial: str
    state: str
    model: str | None = None
    product: str | None = None
    device: str | None = None
    transport_id: str | None = None
    abi: str | None = None
    rooted: bool | None = None
    frida_visible: bool | None = None
    package_installed: bool | None = None
    is_emulator: bool = False


class ExecutionHistoryEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    history_id: str
    run_id: str | None = None
    execution_mode: str | None = None
    executed_backend_key: str | None = None
    status: str | None = None
    stage: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    event_count: int | None = None
    db_path: str | None = None
    bundle_path: str | None = None
    started_at: str
    updated_at: str


class ExecutionHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    items: list[ExecutionHistoryEntryResponse] = Field(default_factory=list)


class WorkspaceDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    package_name: str
    technical_tags: list[str] = Field(default_factory=list)
    dangerous_permissions: list[str] = Field(default_factory=list)
    callback_endpoints: list[str] = Field(default_factory=list)
    callback_clues: list[str] = Field(default_factory=list)
    crypto_signals: list[str] = Field(default_factory=list)
    packer_hints: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    custom_scripts: list[CustomScriptSummary] = Field(default_factory=list)
    can_open_in_jadx: bool
    has_method_index: bool
    method_count: int
    runtime: WorkspaceRuntimeSummary


class WorkspaceMethodSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: str
    method_name: str
    parameter_types: list[str] = Field(default_factory=list)
    return_type: str
    is_constructor: bool
    overload_count: int
    source_path: str
    line_hint: int | None = None
    declaration: str | None = None
    source_preview: str | None = None
    tags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


WorkspaceMethodScope = Literal["first_party", "related_candidates", "all"]


class WorkspaceMethodsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkspaceMethodSummary] = Field(default_factory=list)
    total: int = 0
    scope: WorkspaceMethodScope = "first_party"
    available_scopes: list[WorkspaceMethodScope] = Field(
        default_factory=lambda: ["first_party", "related_candidates", "all"]
    )


class HookRecommendationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    kind: str
    title: str
    reason: str
    score: int
    matched_terms: list[str] = Field(default_factory=list)
    method: WorkspaceMethodSummary | None = None
    template_id: str | None = None
    template_name: str | None = None
    plugin_id: str | None = None
    source_signals: list[str] = Field(default_factory=list)
    template_event_types: list[str] = Field(default_factory=list)
    template_category: str | None = None
    requires_root: bool = False
    supports_offline: bool = True


class WorkspaceRecommendationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[HookRecommendationSummary] = Field(default_factory=list)


class TrafficImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    har_path: str


class TrafficHeaderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str


class TrafficFlowSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "traffic-flow.v1"
    capture_id: str
    flow_id: str
    timestamp: str | None = None
    method: str
    url: str
    scheme: str = ""
    host: str = ""
    path: str = ""
    status_code: int | None = None
    mime_type: str | None = None
    request_headers: list[TrafficHeaderResponse] = Field(default_factory=list)
    response_headers: list[TrafficHeaderResponse] = Field(default_factory=list)
    request_preview: str
    response_preview: str
    request_body_size: int | None = None
    response_body_size: int | None = None
    matched_indicators: list[str] = Field(default_factory=list)
    suspicious: bool
    raw_payload: dict[str, object] = Field(default_factory=dict)


class TrafficCaptureProvenanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    label: str


class TrafficHostSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    flow_count: int
    suspicious_count: int
    https_flow_count: int


class TrafficCaptureSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    https_flow_count: int = 0
    matched_indicator_count: int = 0
    top_hosts: list[TrafficHostSummaryResponse] = Field(default_factory=list)
    suspicious_hosts: list[TrafficHostSummaryResponse] = Field(default_factory=list)


class TrafficCaptureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    flow_schema: str = "traffic-flow.v1"
    source_path: str
    provenance: TrafficCaptureProvenanceResponse
    flow_count: int
    suspicious_count: int
    https_flow_count: int = 0
    matched_indicator_count: int = 0
    top_hosts: list[TrafficHostSummaryResponse] = Field(default_factory=list)
    suspicious_hosts: list[TrafficHostSummaryResponse] = Field(default_factory=list)
    summary: TrafficCaptureSummaryResponse
    flows: list[TrafficFlowSummaryResponse] = Field(default_factory=list)


class WorkspaceTrafficResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    capture: TrafficCaptureResponse | None = None


class LiveTrafficCaptureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str
    session_id: str | None = None
    artifact_path: str | None = None
    output_path: str | None = None
    preview_path: str | None = None
    message: str | None = None


class LiveTrafficPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str
    preview_path: str | None = None
    truncated: bool = False
    items: list[TrafficFlowSummaryResponse] = Field(default_factory=list)


class OpenJadxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str


class ExecutionStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: str | None = None
    device_serial: str | None = None
    frida_server_binary_path: str | None = None
    frida_server_remote_path: str | None = None
    frida_session_seconds: str | None = None


class ExecutionStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str
    execution_mode: str | None = None
    executed_backend_key: str | None = None
    stage: str | None = None
    run_id: str | None = None
    event_count: int | None = None
    db_path: str | None = None
    bundle_path: str | None = None
    executed_backend_label: str | None = None


class ExecutionCancelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str
    execution_mode: str | None = None
    executed_backend_key: str | None = None
    stage: str | None = None


class ReportExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    report_path: str
    static_report_path: str | None = None
    last_execution_db_path: str | None = None
    last_execution_bundle_path: str | None = None


class StartupSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    launch_view: str
    last_workspace_root: str | None = None
    case_id: str | None = None
    title: str | None = None


class RuntimeSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: str
    device_serial: str
    frida_server_binary_path: str
    frida_server_remote_path: str
    frida_session_seconds: str
    live_capture_listen_host: str
    live_capture_listen_port: str


class RuntimeSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: str | None = None
    device_serial: str | None = None
    frida_server_binary_path: str | None = None
    frida_server_remote_path: str | None = None
    frida_session_seconds: str | None = None
    live_capture_listen_host: str | None = None
    live_capture_listen_port: str | None = None


class OpenPathRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str


class OpenPathResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    status: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    default_workspace_root: str


class ToolStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    available: bool
    path: str | None = None


class ExecutionPresetStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    available: bool
    detail: str


class GuidanceStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    detail: str
    emphasis: str


class SuggestedHookTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: str
    template_name: str
    plugin_id: str


class LiveCaptureNetworkSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supports_https_intercept: bool
    supports_packet_capture: bool
    supports_ssl_hooking: bool
    proxy_ready: bool
    certificate_ready: bool
    https_capture_ready: bool


class SslHookGuidanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended: bool
    summary: str
    reason: str
    suggested_templates: list[str] = Field(default_factory=list)
    suggested_template_entries: list[SuggestedHookTemplateResponse] = Field(default_factory=list)
    suggested_terms: list[str] = Field(default_factory=list)


class LiveCaptureRuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    source: str
    detail: str
    listen_host: str
    listen_port: int
    help_text: str | None = None
    proxy_address_hint: str | None = None
    install_url: str | None = None
    certificate_path: str | None = None
    certificate_directory_path: str | None = None
    certificate_exists: bool = False
    certificate_help_text: str | None = None
    proxy_ready: bool = False
    certificate_ready: bool = False
    https_capture_ready: bool = False
    setup_steps: list[str] = Field(default_factory=list)
    proxy_steps: list[str] = Field(default_factory=list)
    certificate_steps: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    setup_step_details: list[GuidanceStepResponse] = Field(default_factory=list)
    proxy_step_details: list[GuidanceStepResponse] = Field(default_factory=list)
    certificate_step_details: list[GuidanceStepResponse] = Field(default_factory=list)
    network_summary: LiveCaptureNetworkSummaryResponse
    ssl_hook_guidance: SslHookGuidanceResponse


class EnvironmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    recommended_execution_mode: str | None = None
    recommended_device_serial: str | None = None
    tools: list[ToolStatusResponse] = Field(default_factory=list)
    connected_devices: list[ConnectedDeviceResponse] = Field(default_factory=list)
    live_capture: LiveCaptureRuntimeResponse
    execution_presets: list[ExecutionPresetStatusResponse] = Field(default_factory=list)
