from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from apk_hacker.application.services.report_export_service import ExportableReport, ReportExportService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


@dataclass(frozen=True, slots=True)
class ReportExportResult:
    state: WorkspaceRuntimeState
    report_path: Path
    static_report_path: Path | None


class WorkspaceReportService:
    def __init__(
        self,
        report_export_service: ReportExportService | None = None,
        hook_log_store_factory: Callable[[Path], HookLogStore] | None = None,
    ) -> None:
        self._report_export_service = report_export_service or ReportExportService()
        self._hook_log_store_factory = hook_log_store_factory or HookLogStore

    def export(
        self,
        record: WorkspaceInspectionRecord,
        state: WorkspaceRuntimeState,
        *,
        traffic_capture: TrafficCapture | None = None,
    ) -> ReportExportResult:
        events = self._load_events(record, state)
        static_report_path = record.bundle.static_inputs.artifact_paths.static_markdown_report
        summary_text = (
            f"当前 Hook Plan 共 {len(state.rendered_hook_plan.items)} 项，"
            f"最近一次执行产生 {len(events)} 条事件。"
        )
        report = ExportableReport(
            job_id=record.bundle.job.job_id,
            summary_text=summary_text,
            sample_path=record.sample_path,
            static_inputs=record.bundle.static_inputs,
            hook_plan=state.rendered_hook_plan,
            hook_events=events,
            traffic_capture=traffic_capture,
            last_execution_db_path=state.last_execution_db_path,
            last_execution_bundle_path=state.last_execution_bundle_path,
            last_execution_status=state.last_execution_status,
            last_execution_mode=state.last_execution_mode,
            last_executed_backend_key=state.last_executed_backend_key,
            last_execution_error_code=state.last_execution_error_code,
            last_execution_error_message=state.last_execution_error_message,
        )
        report_path = record.workspace_root / "reports" / f"{record.case_id}-report.md"
        exported_path = self._report_export_service.export_markdown(report, report_path)
        return ReportExportResult(
            state=replace(state, last_report_path=exported_path),
            report_path=exported_path,
            static_report_path=static_report_path,
        )

    def _load_events(
        self,
        record: WorkspaceInspectionRecord,
        state: WorkspaceRuntimeState,
    ) -> tuple[HookEvent, ...]:
        if state.last_execution_db_path is None or not state.last_execution_db_path.exists():
            return ()
        return tuple(self._hook_log_store_factory(state.last_execution_db_path).list_for_job(record.bundle.job.job_id))
