from pathlib import Path

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.workspace_hook_plan_service import WorkspaceHookPlanService
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
from apk_hacker.application.services.workspace_state_service import WorkspaceStateService
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndexEntry


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


def test_workspace_hook_plan_service_adds_method_source_and_rerenders_plan(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(
        state_service=WorkspaceStateService(),
        hook_plan_service=HookPlanService(),
    )
    state = build_default_runtime_state("case-001", tmp_path / "case-001")

    updated = service.add_method_source(state, _method())

    assert len(updated.selected_hook_sources) == 1
    assert len(updated.rendered_hook_plan.items) == 1
    assert updated.rendered_hook_plan.items[0].source_kind == "selected_method"
    assert updated.rendered_hook_plan.items[0].target is not None
    assert updated.rendered_hook_plan.items[0].target.class_name == "com.demo.net.Config"


def test_workspace_hook_plan_service_removes_plan_item_and_preserves_unrenderable_sources(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(
        state_service=WorkspaceStateService(),
        hook_plan_service=HookPlanService(),
    )
    hidden_source = HookPlanSource(
        source_id="custom_script:/tmp/missing.js",
        kind="custom_script",
        script_name="broken-script",
    )
    state = service.rerender(
        build_default_runtime_state("case-002", tmp_path / "case-002")
    )
    state = service.add_method_source(state, _method())
    state = service.replace_sources(
        state,
        (*state.selected_hook_sources, hidden_source),
    )

    updated = service.remove_item(state, state.rendered_hook_plan.items[0].item_id)

    assert updated.rendered_hook_plan.items == ()
    assert len(updated.selected_hook_sources) == 1
    assert updated.selected_hook_sources[0].source_id == "custom_script:/tmp/missing.js"


def test_workspace_hook_plan_service_rerender_preserves_item_state_and_refreshes_scripts(tmp_path: Path) -> None:
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    script_path = scripts_root / "trace_login.js"
    script_path.write_text("send('before');\n", encoding="utf-8")
    service = WorkspaceHookPlanService(
        state_service=WorkspaceStateService(),
        hook_plan_service=HookPlanService(),
    )
    state = service.replace_sources(
        build_default_runtime_state("case-003", tmp_path / "case-003"),
        (HookPlanSource.from_custom_script("trace_login", str(script_path)),),
    )
    item_id = state.rendered_hook_plan.items[0].item_id
    state = service.update_item(state, item_id, enabled=False)
    script_path.write_text("send('after');\n", encoding="utf-8")

    updated = service.rerender(state)

    assert updated.rendered_hook_plan.items[0].item_id == item_id
    assert updated.rendered_hook_plan.items[0].enabled is False
    assert updated.rendered_hook_plan.items[0].render_context["rendered_script"] == "send('after');\n"
