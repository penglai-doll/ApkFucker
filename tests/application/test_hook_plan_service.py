from pathlib import Path
from hashlib import sha1

from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndexEntry


def _stable_item_id(source_id: str) -> str:
    return f"hook-{sha1(source_id.encode('utf-8')).hexdigest()}"


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
    assert result.items[0].item_id == _stable_item_id(
        "method:com.demo.net.Config:buildUploadUrl:String:tests/fixtures/jadx_sources/com/demo/net/Config.java"
    )
    assert result.items[0].target.target_id == result.items[0].item_id
    assert result.items[0].plugin_id == "builtin.method-hook"
    assert result.items[0].render_context["methodName"] == "buildUploadUrl"
    assert result.items[0].render_context["paramTypes"] == ["String"]
    assert "rendered_script" in result.items[0].render_context
    assert "buildUploadUrl" in str(result.items[0].render_context["rendered_script"])


def test_custom_script_service_discovers_local_frida_scripts(tmp_path: Path) -> None:
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")

    result = CustomScriptService(tmp_path).discover()

    assert [item.name for item in result] == ["trace_login"]


def test_custom_script_service_saves_and_reads_local_frida_script(tmp_path: Path) -> None:
    service = CustomScriptService(tmp_path)

    record = service.save_script("trace_login", "send('trace');\n")

    assert record.name == "trace_login"
    assert record.script_path.read_text(encoding="utf-8") == "send('trace');\n"
    assert service.read_script(record) == "send('trace');\n"


def test_hook_plan_service_combines_methods_and_custom_scripts(tmp_path: Path) -> None:
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")
    record = CustomScriptService(tmp_path).discover()[0]
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=2,
        source_path="tests/fixtures/jadx_sources/com/demo/net/Config.java",
        line_hint=4,
    )

    result = HookPlanService().plan_for_sources(
        [
            HookPlanSource.from_custom_script(record.name, str(record.script_path)),
            HookPlanSource.from_method(method),
        ]
    )

    assert [item.kind for item in result.items] == ["custom_script", "method_hook"]
    assert [item.inject_order for item in result.items] == [1, 2]
    assert result.items[0].item_id == _stable_item_id(f"custom_script:{script_path}")
    assert result.items[0].plugin_id == "custom.local-script"
    assert result.items[0].render_context == {
        "script_name": "trace_login",
        "script_path": str(script_path),
        "rendered_script": "send('trace');\n",
    }


def test_hook_plan_service_builds_template_hook_items() -> None:
    result = HookPlanService().plan_for_sources(
        [
            HookPlanSource.from_template(
                template_id="ssl.okhttp3_unpin",
                template_name="OkHttp3 SSL Unpinning",
                plugin_id="builtin.ssl-okhttp3-unpin",
            )
        ]
    )

    assert len(result.items) == 1
    assert result.items[0].kind == "template_hook"
    assert result.items[0].inject_order == 1
    assert result.items[0].item_id == _stable_item_id("template:builtin.ssl-okhttp3-unpin:ssl.okhttp3_unpin")
    assert result.items[0].target is None
    assert result.items[0].plugin_id == "builtin.ssl-okhttp3-unpin"
    assert result.items[0].render_context == {
        "template_id": "ssl.okhttp3_unpin",
        "template_name": "OkHttp3 SSL Unpinning",
        "rendered_script": str(result.items[0].render_context["rendered_script"]),
    }
    assert "OkHttp3 SSL unpinning template loaded" in str(result.items[0].render_context["rendered_script"])
