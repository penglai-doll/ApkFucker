from __future__ import annotations

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
    tags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    is_constructor: bool = False
    overload_count: int = 1


class HookPlanRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str


class HookPlanCustomScriptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script_id: str


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


class HookPlanItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    kind: str
    enabled: bool
    inject_order: int
    target: HookPlanTargetSummary | None = None
    render_context: dict[str, object] = Field(default_factory=dict)
    plugin_id: str | None = None


class HookPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    updated_at: str
    selected_hook_sources: list[HookPlanSourceSummary] = Field(default_factory=list)
    items: list[HookPlanItemResponse] = Field(default_factory=list)
    execution_count: int = 0
    last_execution_run_id: str | None = None
    last_execution_mode: str | None = None
    last_execution_status: str | None = None
    last_execution_event_count: int | None = None
    last_execution_result_path: str | None = None
    last_execution_db_path: str | None = None
    last_execution_bundle_path: str | None = None
    last_report_path: str | None = None


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
    tags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class WorkspaceMethodsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkspaceMethodSummary] = Field(default_factory=list)
    total: int = 0


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


class WorkspaceRecommendationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[HookRecommendationSummary] = Field(default_factory=list)


class OpenJadxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str


class ExecutionStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: str | None = None


class ExecutionStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str
    execution_mode: str | None = None
    run_id: str | None = None
    event_count: int | None = None
    db_path: str | None = None
    bundle_path: str | None = None
    executed_backend_label: str | None = None


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


class EnvironmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    recommended_execution_mode: str | None = None
    tools: list[ToolStatusResponse] = Field(default_factory=list)
    execution_presets: list[ExecutionPresetStatusResponse] = Field(default_factory=list)
