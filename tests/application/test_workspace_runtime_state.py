import json
from pathlib import Path

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
from apk_hacker.application.services.workspace_runtime_state import load_workspace_runtime_state
from apk_hacker.application.services.workspace_runtime_state import save_workspace_runtime_state
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndexEntry


def test_build_default_runtime_state_starts_empty(tmp_path: Path) -> None:
    state = build_default_runtime_state(case_id="case-001", workspace_root=tmp_path / "case-001")

    assert state == WorkspaceRuntimeState(
        case_id="case-001",
        workspace_root=tmp_path / "case-001",
        updated_at=state.updated_at,
        selected_hook_sources=(),
        rendered_hook_plan=HookPlanService().plan_for_sources([]),
    )


def test_workspace_runtime_state_round_trips_through_json_file(tmp_path: Path) -> None:
    workspace_root = tmp_path / "case-002"
    workspace_root.mkdir(parents=True)
    state_path = workspace_root / "workspace-runtime.json"
    scripts_root = workspace_root / "scripts"
    scripts_root.mkdir(parents=True)
    (scripts_root / "trace_login.js").write_text("send('trace');\n", encoding="utf-8")
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="sources/com/demo/net/Config.java",
        line_hint=4,
    )
    sources = (
        HookPlanSource.from_method(method),
        HookPlanSource.from_custom_script("trace_login", str(scripts_root / "trace_login.js")),
    )
    initial_state = WorkspaceRuntimeState(
        case_id="case-002",
        workspace_root=workspace_root,
        updated_at="2026-04-13T15:00:00+00:00",
        selected_hook_sources=sources,
        rendered_hook_plan=HookPlanService().plan_for_sources(list(sources)),
        execution_count=2,
        last_execution_run_id="run-2",
        last_execution_mode="fake_backend",
        last_executed_backend_key="fake_backend",
        last_execution_status="completed",
        last_execution_stage="completed",
        last_execution_error_code="frida_session_error",
        last_execution_error_message="Frida 会话初始化失败。",
        last_execution_event_count=7,
        last_execution_result_path=workspace_root / "executions" / "run-2",
        last_execution_db_path=workspace_root / "executions" / "run-2" / "hook-events.sqlite3",
        last_execution_bundle_path=workspace_root / "executions" / "run-2",
        last_report_path=workspace_root / "reports" / "case-002-report.md",
        traffic_capture_source_path=workspace_root / "captures" / "sample.har",
        traffic_capture_summary_path=workspace_root / "evidence" / "traffic" / "traffic-capture.json",
        traffic_capture_flow_count=2,
        traffic_capture_suspicious_count=1,
    )

    saved_state = save_workspace_runtime_state(initial_state, state_path)
    reloaded_state = load_workspace_runtime_state(
        case_id="case-002",
        workspace_root=workspace_root,
        path=state_path,
        hook_plan_service=HookPlanService(),
    )
    persisted_payload = json.loads(state_path.read_text(encoding="utf-8"))

    assert saved_state.updated_at != "2026-04-13T15:00:00+00:00"
    assert persisted_payload["last_execution_error_code"] == "frida_session_error"
    assert persisted_payload["last_execution_error_message"] == "Frida 会话初始化失败。"
    assert reloaded_state.case_id == "case-002"
    assert reloaded_state.workspace_root == workspace_root
    assert reloaded_state.selected_hook_sources == sources
    assert reloaded_state.execution_count == 2
    assert reloaded_state.last_execution_run_id == "run-2"
    assert reloaded_state.last_execution_mode == "fake_backend"
    assert reloaded_state.last_executed_backend_key == "fake_backend"
    assert reloaded_state.last_execution_status == "completed"
    assert reloaded_state.last_execution_stage == "completed"
    assert reloaded_state.last_execution_error_code == "frida_session_error"
    assert reloaded_state.last_execution_error_message == "Frida 会话初始化失败。"
    assert reloaded_state.last_execution_event_count == 7
    assert reloaded_state.last_execution_db_path == workspace_root / "executions" / "run-2" / "hook-events.sqlite3"
    assert reloaded_state.last_report_path == workspace_root / "reports" / "case-002-report.md"
    assert reloaded_state.traffic_capture_flow_count == 2
    assert reloaded_state.traffic_capture_suspicious_count == 1
    assert len(reloaded_state.rendered_hook_plan.items) == 2
