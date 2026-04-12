from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptRecord, CustomScriptService
from apk_hacker.application.services.job_service import JobService, StaticWorkspaceBundle
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.domain.models.case_queue import CaseQueueItem
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.workspace import WorkspaceRecord
from apk_hacker.domain.models.indexes import MethodIndex


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    workspace: WorkspaceRecord
    job: AnalysisJob
    static_inputs: StaticInputs
    method_index: MethodIndex
    case_queue: tuple[CaseQueueItem, ...]
    custom_scripts: tuple[CustomScriptRecord, ...]
    summary_text: str


class WorkspaceController:
    def __init__(
        self,
        db_root: Path,
        scripts_root: Path,
        job_service: JobService | None = None,
        workspace_service: WorkspaceService | None = None,
        case_queue_service: CaseQueueService | None = None,
        custom_script_service: CustomScriptService | None = None,
        report_export_service: ReportExportService | None = None,
        workspace_registry_service: WorkspaceRegistryService | None = None,
    ) -> None:
        self._db_root = db_root
        self._scripts_root = scripts_root
        self._job_service = job_service or JobService()
        self._workspace_service = workspace_service or WorkspaceService()
        self._case_queue_service = case_queue_service or CaseQueueService()
        self._custom_script_service = custom_script_service or CustomScriptService(scripts_root)
        self._report_export_service = report_export_service or ReportExportService()
        self._workspace_registry_service = workspace_registry_service or WorkspaceRegistryService(
            db_root / "workspace-registry.json"
        )

    @property
    def db_root(self) -> Path:
        return self._db_root

    @property
    def scripts_root(self) -> Path:
        return self._scripts_root

    def initialize_workspace(
        self,
        sample_path: Path,
        workspace_root: Path,
        title: str | None = None,
    ) -> WorkspaceState:
        workspace = self._workspace_service.create_workspace(sample_path, workspace_root, title=title)
        bundle = self._job_service.load_static_workspace_bundle(
            workspace.sample_path,
            output_dir=workspace.workspace_root / "static",
        )
        case_queue = self._case_queue_service.list_cases(workspace_root)
        custom_scripts = self._custom_script_service.discover_records()
        self._workspace_registry_service.remember_workspace_root(workspace_root)
        self._workspace_registry_service.set_last_opened_workspace(workspace.workspace_root)
        summary_text = self._report_export_service.build_workspace_summary(
            workspace_title=workspace.title,
            sample_path=workspace.sample_path,
            method_count=len(bundle.method_index.methods),
            script_count=len(custom_scripts),
            case_count=len(case_queue),
        )
        return WorkspaceState(
            workspace=workspace,
            job=bundle.job,
            static_inputs=bundle.static_inputs,
            method_index=bundle.method_index,
            case_queue=case_queue,
            custom_scripts=custom_scripts,
            summary_text=summary_text,
        )

    def list_case_queue(self, workspace_root: Path) -> tuple[CaseQueueItem, ...]:
        return self._case_queue_service.list_cases(workspace_root)

    def discover_custom_scripts(self) -> tuple[CustomScriptRecord, ...]:
        return self._custom_script_service.discover_records()

    def export_report(self, state: WorkspaceState, output_path: Path) -> Path:
        from apk_hacker.application.services.report_export_service import ExportableReport
        from apk_hacker.domain.models.hook_plan import HookPlan

        report = ExportableReport(
            job_id=state.job.job_id,
            summary_text=state.summary_text,
            sample_path=state.workspace.sample_path,
            static_inputs=state.static_inputs,
            hook_plan=HookPlan(items=()),
            hook_events=(),
            traffic_capture=None,
        )
        return self._report_export_service.export_markdown(report, output_path)

    def load_static_workspace(self, sample_path: Path, output_dir: Path | None = None) -> StaticWorkspaceBundle:
        return self._job_service.load_static_workspace_bundle(sample_path, output_dir=output_dir)
