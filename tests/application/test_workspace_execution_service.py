from dataclasses import replace
import json
from pathlib import Path
from threading import Event

import pytest

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import StaticWorkspaceBundle
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.application.services.workspace_execution_service import WorkspaceExecutionService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.infrastructure.execution.backend import ExecutionCancelled


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
    workspace_root = tmp_path / "case-execution"
    workspace_root.mkdir(parents=True)
    return WorkspaceInspectionRecord(
        case_id="case-execution",
        title="执行案件",
        workspace_root=workspace_root,
        sample_path=sample_path,
        bundle=bundle,
        custom_scripts=(),
    )


def _event() -> HookEvent:
    return HookEvent(
        timestamp="2026-04-24T00:00:00Z",
        job_id="job-demo",
        event_type="method_call",
        source="fake",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        arguments=("demo",),
        return_value="https://demo.example/upload",
        stacktrace="",
        raw_payload={},
    )


class _CancellingBackend:
    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        assert request.cancellation_event is not None
        request.cancellation_event.set()
        return (_event(),)


class _SingleEventBackend:
    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        return (_event(),)


def test_workspace_execution_service_records_successful_run_metadata(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    method = _method()
    state = replace(
        build_default_runtime_state(record.case_id, record.workspace_root),
        rendered_hook_plan=HookPlanService().plan_for_methods([method]),
    )

    result = WorkspaceExecutionService().execute(
        state,
        record,
        execution_mode="fake_backend",
    )

    assert result.execution_mode == "fake_backend"
    assert result.executed_backend_key == "fake_backend"
    assert result.run_id == "run-1"
    assert result.event_count == 1
    assert result.db_path == record.workspace_root / "executions" / "run-1" / "hook-events.sqlite3"
    assert result.bundle_path == record.workspace_root / "executions" / "run-1"
    assert result.db_path.exists()
    manifest_path = result.bundle_path / "artifact-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "artifact-manifest.v1"
    assert manifest["case_id"] == record.case_id
    artifact_by_kind = {item["kind"]: item for item in manifest["artifacts"]}
    assert artifact_by_kind["dynamic.hook_events_sqlite"]["path"] == str(result.db_path.resolve())
    assert artifact_by_kind["dynamic.hook_events_sqlite"]["metadata"]["event_count"] == 1
    assert artifact_by_kind["dynamic.hook_events_sqlite"]["metadata"]["schema"] == "dynamic-event.v1"
    assert result.state.execution_count == 1
    assert result.state.last_execution_status == "completed"
    assert result.state.last_execution_stage == "completed"
    assert result.state.last_execution_run_id == "run-1"
    assert result.state.last_execution_db_path == result.db_path
    assert result.state.last_execution_bundle_path == result.bundle_path
    assert result.state.last_execution_event_count == 1
    assert len(result.state.execution_history) == 1
    assert result.state.execution_history[0].run_id == "run-1"
    assert result.state.execution_history[0].status == "completed"
    assert result.state.execution_history[0].db_path == result.db_path
    assert len(result.events) == 1
    assert result.events[0].class_name == method.class_name
    assert result.events[0].method_name == method.method_name


def test_workspace_execution_service_raises_when_backend_finishes_after_cancellation(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    state = replace(
        build_default_runtime_state(record.case_id, record.workspace_root),
        rendered_hook_plan=HookPlanService().plan_for_methods([_method()]),
    )
    cancellation_event = Event()
    service = WorkspaceExecutionService(backend_builder=lambda *_args, **_kwargs: _CancellingBackend())

    with pytest.raises(ExecutionCancelled):
        service.execute(
            state,
            record,
            execution_mode="fake_backend",
            cancellation_event=cancellation_event,
        )


def test_workspace_execution_service_labels_explicit_backend_override(tmp_path: Path) -> None:
    record = _build_record(tmp_path)
    state = replace(
        build_default_runtime_state(record.case_id, record.workspace_root),
        rendered_hook_plan=HookPlanService().plan_for_methods([_method()]),
    )
    service = WorkspaceExecutionService(backend_builder=lambda *_args, **_kwargs: _SingleEventBackend())

    result = service.execute(
        state,
        record,
        execution_mode="real_device",
        executed_backend_key="real_frida_session",
    )

    assert result.executed_backend_key == "real_frida_session"
    assert result.executed_backend_label == "Frida Session"
