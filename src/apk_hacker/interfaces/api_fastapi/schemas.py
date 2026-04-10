from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from apk_hacker.application.services.workbench_settings_service import WorkbenchSettings
from apk_hacker.domain.models.case_queue import CaseQueueItem
from apk_hacker.domain.models.workspace import WorkspaceRecord


class CaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    workspace_root: str


class CaseListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CaseSummary] = Field(default_factory=list)


class WorkspaceImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_path: Path
    workspace_root: Path
    title: str | None = None


class WorkspaceImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    workspace_root: str
    sample_path: str
    workspace_version: int
    created_at: str
    updated_at: str
    sample_filename: str


class WorkspaceDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    workspace_root: str
    sample_path: str
    workspace_version: int
    created_at: str
    updated_at: str
    sample_filename: str


class ExecutionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "fake_backend"


class ExecutionCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: str
    mode: str
    job_id: str


class ReportExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    report_path: str


class StartupSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    launch_view: str
    last_workspace_root: str | None
    last_case_id: str | None
    sample_path: str | None = None
    execution_mode: str = "fake_backend"
    device_serial: str = ""
    frida_server_binary_path: str = ""
    frida_server_remote_path: str = ""
    frida_session_seconds: str = ""


def case_summary_from_item(item: CaseQueueItem) -> CaseSummary:
    return CaseSummary(
        case_id=item.case_id,
        title=item.title,
        workspace_root=str(item.workspace_root),
    )


def workspace_import_response_from_record(record: WorkspaceRecord) -> WorkspaceImportResponse:
    return WorkspaceImportResponse(
        case_id=record.case_id,
        title=record.title,
        workspace_root=str(record.workspace_root),
        sample_path=str(record.sample_path),
        workspace_version=record.workspace_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        sample_filename=record.sample_filename,
    )


def workspace_detail_response_from_record(record: WorkspaceRecord) -> WorkspaceDetailResponse:
    return WorkspaceDetailResponse(
        case_id=record.case_id,
        title=record.title,
        workspace_root=str(record.workspace_root),
        sample_path=str(record.sample_path),
        workspace_version=record.workspace_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        sample_filename=record.sample_filename,
    )


def startup_settings_response(
    *,
    settings: WorkbenchSettings,
    last_workspace_root: Path | None,
) -> StartupSettingsResponse:
    return StartupSettingsResponse(
        launch_view="workspace" if last_workspace_root is not None else "queue",
        last_workspace_root=str(last_workspace_root) if last_workspace_root is not None else None,
        last_case_id=last_workspace_root.name if last_workspace_root is not None else None,
        sample_path=settings.sample_path or None,
        execution_mode=settings.execution_mode,
        device_serial=settings.device_serial,
        frida_server_binary_path=settings.frida_server_binary_path,
        frida_server_remote_path=settings.frida_server_remote_path,
        frida_session_seconds=settings.frida_session_seconds,
    )
