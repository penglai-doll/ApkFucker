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


class ExecutionStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str


class ReportExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    report_path: str


class StartupSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    launch_view: str
    last_workspace_root: str | None = None
    case_id: str | None = None
    title: str | None = None
