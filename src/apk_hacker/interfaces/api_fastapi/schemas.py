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
