from pathlib import Path

import pytest

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.workspace_hook_plan_service import WorkspaceHookPlanService
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
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
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    state = build_default_runtime_state("case-001", tmp_path / "case-001")

    updated = service.add_method_source(state, _method())

    assert len(updated.selected_hook_sources) == 1
    assert len(updated.rendered_hook_plan.items) == 1
    assert updated.rendered_hook_plan.items[0].source_kind == "selected_method"
    assert updated.rendered_hook_plan.items[0].target is not None
    assert updated.rendered_hook_plan.items[0].target.class_name == "com.demo.net.Config"


def test_workspace_hook_plan_service_add_source_is_noop_for_duplicate_source(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    state = build_default_runtime_state("case-dup", tmp_path / "case-dup")
    source = HookPlanSource.from_method(_method())

    updated = service.add_source(service.add_source(state, source), source)

    assert len(updated.selected_hook_sources) == 1
    assert len(updated.rendered_hook_plan.items) == 1


def test_workspace_hook_plan_service_removes_plan_item_and_preserves_unrenderable_sources(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
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


def test_workspace_hook_plan_service_clear_resets_selected_sources_and_plan(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    state = service.add_method_source(build_default_runtime_state("case-clear", tmp_path / "case-clear"), _method())

    cleared = service.clear(state)

    assert cleared.selected_hook_sources == ()
    assert cleared.rendered_hook_plan.items == ()


def test_workspace_hook_plan_service_rerender_preserves_item_state_and_refreshes_scripts(tmp_path: Path) -> None:
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    script_path = scripts_root / "trace_login.js"
    script_path.write_text("send('before');\n", encoding="utf-8")
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
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


def test_workspace_hook_plan_service_update_item_reorders_plan(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    first = HookPlanSource.from_method(_method())
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")
    second = HookPlanSource.from_custom_script("trace_login", str(script_path))
    state = service.replace_sources(
        build_default_runtime_state("case-order", tmp_path / "case-order"),
        (first, second),
    )
    moved_item_id = state.rendered_hook_plan.items[1].item_id

    updated = service.update_item(state, moved_item_id, inject_order=1)

    assert [item.item_id for item in updated.rendered_hook_plan.items] == [
        moved_item_id,
        state.rendered_hook_plan.items[0].item_id,
    ]
    assert updated.rendered_hook_plan.items[0].inject_order == 1
    assert updated.rendered_hook_plan.items[1].inject_order == 2


def test_workspace_hook_plan_service_update_item_rejects_invalid_requests(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    state = service.add_method_source(build_default_runtime_state("case-invalid", tmp_path / "case-invalid"), _method())
    item_id = state.rendered_hook_plan.items[0].item_id

    with pytest.raises(ValueError, match="At least one hook plan field"):
        service.update_item(state, item_id)
    with pytest.raises(ValueError, match="out of range"):
        service.update_item(state, item_id, inject_order=3)
    with pytest.raises(KeyError):
        service.update_item(state, "hook-missing", enabled=False)


def test_workspace_hook_plan_service_replaces_custom_script_source(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    old_path = tmp_path / "old.js"
    new_path = tmp_path / "new.js"
    old_path.write_text("send('old');\n", encoding="utf-8")
    new_path.write_text("send('new');\n", encoding="utf-8")
    state = service.replace_sources(
        build_default_runtime_state("case-script", tmp_path / "case-script"),
        (HookPlanSource.from_custom_script("trace_old", str(old_path)),),
    )

    updated = service.replace_custom_script_source(
        state,
        old_script_path=str(old_path),
        new_script_name="trace_new",
        new_script_path=str(new_path),
    )

    assert updated.selected_hook_sources[0].script_name == "trace_new"
    assert updated.selected_hook_sources[0].script_path == str(new_path)


def test_workspace_hook_plan_service_removes_custom_script_source(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(hook_plan_service=HookPlanService())
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")
    state = service.replace_sources(
        build_default_runtime_state("case-script-remove", tmp_path / "case-script-remove"),
        (HookPlanSource.from_custom_script("trace_login", str(script_path)),),
    )

    updated = service.remove_custom_script_source(state, script_path=str(script_path))

    assert updated.selected_hook_sources == ()
    assert updated.rendered_hook_plan.items == ()
