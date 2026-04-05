from pathlib import Path

from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.indexes import MethodIndexEntry


def test_hook_plan_service_turns_method_selection_into_plan_item() -> None:
    methods = [
        MethodIndexEntry(
            class_name="com.demo.net.Config",
            method_name="buildUploadUrl",
            parameter_types=("String",),
            return_type="String",
            is_constructor=False,
            overload_count=2,
            source_path="tests/fixtures/jadx_sources/com/demo/net/Config.java",
            line_hint=4,
        ),
        MethodIndexEntry(
            class_name="com.demo.entry.MainActivity",
            method_name="onCreate",
            parameter_types=("Object",),
            return_type="void",
            is_constructor=False,
            overload_count=1,
            source_path="tests/fixtures/jadx_sources/com/demo/entry/MainActivity.java",
            line_hint=4,
        ),
    ]

    result = HookPlanService().plan_for_methods(methods)

    assert len(result.items) == 2
    assert [item.kind for item in result.items] == ["method_hook", "method_hook"]
    assert [item.inject_order for item in result.items] == [1, 2]
    assert result.items[0].target is not None
    assert result.items[0].target.class_name == "com.demo.net.Config"
    assert result.items[0].plugin_id == "builtin.method-hook"
    assert result.items[0].render_context["methodName"] == "buildUploadUrl"
    assert result.items[0].render_context["paramTypes"] == ["String"]


def test_custom_script_service_discovers_local_frida_scripts(tmp_path: Path) -> None:
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")

    result = CustomScriptService(tmp_path).discover()

    assert [item.name for item in result] == ["trace_login"]


def test_hook_plan_service_combines_methods_and_custom_scripts(tmp_path: Path) -> None:
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")
    record = CustomScriptService(tmp_path).discover()[0]
    methods = [
        MethodIndexEntry(
            class_name="com.demo.net.Config",
            method_name="buildUploadUrl",
            parameter_types=("String",),
            return_type="String",
            is_constructor=False,
            overload_count=2,
            source_path="tests/fixtures/jadx_sources/com/demo/net/Config.java",
            line_hint=4,
        )
    ]

    result = HookPlanService().plan_for_selection(methods, [record])

    assert [item.kind for item in result.items] == ["method_hook", "custom_script"]
    assert [item.inject_order for item in result.items] == [1, 2]
    assert result.items[1].plugin_id == "custom.local-script"
    assert result.items[1].render_context == {
        "script_name": "trace_login",
        "script_path": str(script_path),
    }
