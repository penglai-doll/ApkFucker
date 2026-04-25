from pathlib import Path

from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, MethodHookTarget
from apk_hacker.infrastructure.templates.script_renderer import ScriptRenderer


def test_script_renderer_renders_method_hook_template() -> None:
    target = MethodHookTarget(
        target_id="target-1",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("java.lang.String",),
        return_type="String",
        source_origin="method_index",
    )
    item = HookPlanItem(
        item_id="item-1",
        kind="method_hook",
        source_kind="selected_method",
        enabled=True,
        inject_order=1,
        target=target,
        render_context={
            "className": target.class_name,
            "methodName": target.method_name,
            "paramTypes": ["java.lang.String"],
        },
        plugin_id="builtin.method-hook",
    )

    plan = ScriptRenderer().render_plan(HookPlan(items=(item,)))
    rendered = str(plan.items[0].render_context["rendered_script"])

    assert 'Java.use("com.demo.net.Config")' in rendered
    assert "TargetClass[methodName]" in rendered
    assert "method_return" in rendered
    assert "overloads.forEach" in rendered


def test_script_renderer_renders_template_hook_template() -> None:
    item = HookPlanItem(
        item_id="item-1",
        kind="template_hook",
        source_kind="framework_plugin",
        enabled=True,
        inject_order=1,
        target=None,
        render_context={
            "template_id": "ssl.okhttp3_unpin",
            "template_name": "OkHttp3 SSL Unpinning",
        },
        plugin_id="builtin.ssl-okhttp3-unpin",
    )

    plan = ScriptRenderer().render_plan(HookPlan(items=(item,)))
    rendered = str(plan.items[0].render_context["rendered_script"])

    assert "ssl.okhttp3_unpin" in rendered
    assert "ssl_unpinning_bypass" in rendered
    assert "OkHttp3 SSL unpinning hooks installed" in rendered


def test_script_renderer_loads_custom_script_content(tmp_path: Path) -> None:
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")
    item = HookPlanItem(
        item_id="item-1",
        kind="custom_script",
        source_kind="custom_script",
        enabled=True,
        inject_order=1,
        target=None,
        render_context={
            "script_name": "trace_login",
            "script_path": str(script_path),
        },
        plugin_id="custom.local-script",
    )

    plan = ScriptRenderer().render_plan(HookPlan(items=(item,)))

    assert plan.items[0].render_context["rendered_script"] == "send('trace');\n"
