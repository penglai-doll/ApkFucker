from pathlib import Path
from dataclasses import replace
import json

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import StaticWorkspaceBundle
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_report_service import WorkspaceReportService
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def _method() -> MethodIndexEntry:
    return MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="tests/fixtures/jadx_sources/com/demo/net/Config.java",
        line_hint=4,
    )


def _build_record(tmp_path: Path) -> WorkspaceInspectionRecord:
    fixture_root = Path("tests/fixtures/static_outputs")
    analysis = json.loads((fixture_root / "sample_analysis.json").read_text(encoding="utf-8"))
    callback = json.loads((fixture_root / "sample_callback-config.json").read_text(encoding="utf-8"))
    static_report_path = tmp_path / "sample-report.md"
    static_report_path.write_text("## Legacy Static Narrative\n\n静态报告正文。\n", encoding="utf-8")
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    static_inputs = StaticAdapter().adapt(
        sample_path=sample_path,
        analysis_report=analysis,
        callback_config=callback,
        artifact_paths={
            "analysis_report": fixture_root / "sample_analysis.json",
            "static_markdown_report": static_report_path,
        },
    )
    bundle = StaticWorkspaceBundle(
        job=AnalysisJob.queued(str(sample_path)),
        static_inputs=static_inputs,
        method_index=MethodIndex(classes=(), methods=(_method(),)),
    )
    workspace_root = tmp_path / "case-report"
    workspace_root.mkdir(parents=True)
    return WorkspaceInspectionRecord(
        case_id="case-report",
        title="报告案件",
        workspace_root=workspace_root,
        sample_path=sample_path,
        bundle=bundle,
        custom_scripts=(),
    )


def test_workspace_report_service_exports_workspace_report_and_updates_state(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    method = _method()
    plan = HookPlanService().plan_for_methods([method])
    db_path = record.workspace_root / "runs" / "last.sqlite3"
    event = HookEvent(
        timestamp="2026-04-22T00:00:00Z",
        job_id=record.bundle.job.job_id,
        event_type="call",
        source="fake_backend",
        class_name=method.class_name,
        method_name=method.method_name,
        arguments=("https://demo-c2.example/api/upload",),
        return_value="ok",
        stacktrace="stack",
        raw_payload={"event": "call"},
    )
    HookLogStore(db_path).insert(event)
    state = replace(
        build_default_runtime_state(record.case_id, record.workspace_root),
        rendered_hook_plan=plan,
        last_execution_db_path=db_path,
        last_execution_status="completed",
        last_execution_mode="fake_backend",
        last_executed_backend_key="fake_backend",
    )
    traffic_capture = TrafficCaptureService().load_har(
        Path("tests/fixtures/traffic/sample.har"),
        record.bundle.static_inputs,
    )

    result = WorkspaceReportService(report_export_service=ReportExportService()).export(
        record,
        state,
        traffic_capture=traffic_capture,
    )
    content = result.report_path.read_text(encoding="utf-8")

    assert result.report_path == record.workspace_root / "reports" / "case-report-report.md"
    assert result.state.last_report_path == result.report_path
    assert result.static_report_path == record.bundle.static_inputs.artifact_paths.static_markdown_report
    assert "当前 Hook Plan 共 1 项，最近一次执行产生 1 条事件。" in content
    assert "buildUploadUrl" in content
    assert "demo-c2.example/api/upload" in content
    assert "demo-c2.example" in content


def test_workspace_report_service_handles_missing_execution_log(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    state = build_default_runtime_state(record.case_id, record.workspace_root)

    result = WorkspaceReportService().export(record, state)
    content = result.report_path.read_text(encoding="utf-8")

    assert result.state.last_report_path == result.report_path
    assert "当前 Hook Plan 共 0 项，最近一次执行产生 0 条事件。" in content
    assert "- No HAR capture loaded." in content
