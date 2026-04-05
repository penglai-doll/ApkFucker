from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, MethodHookTarget
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend


def test_fake_backend_emits_hook_events() -> None:
    target = MethodHookTarget(
        target_id="target-1",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        source_origin="method_index",
    )
    plan = HookPlan(
        items=(
            HookPlanItem(
                item_id="item-1",
                kind="method_hook",
                enabled=True,
                inject_order=1,
                target=target,
                render_context={},
                plugin_id="builtin.method-hook",
            ),
        )
    )

    events = FakeExecutionBackend().execute("job-1", plan)

    assert events[0].class_name == "com.demo.net.Config"
    assert events[0].method_name == "buildUploadUrl"


def test_fake_backend_skips_disabled_and_unsupported_targetless_items() -> None:
    target = MethodHookTarget(
        target_id="target-1",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        source_origin="method_index",
    )
    plan = HookPlan(
        items=(
            HookPlanItem(
                item_id="item-1",
                kind="method_hook",
                enabled=False,
                inject_order=1,
                target=target,
                render_context={},
                plugin_id="builtin.method-hook",
            ),
            HookPlanItem(
                item_id="item-2",
                kind="placeholder",
                enabled=True,
                inject_order=2,
                target=None,
                render_context={"script_path": "/tmp/demo.js"},
                plugin_id="placeholder.plugin",
            ),
        )
    )

    assert FakeExecutionBackend().execute("job-1", plan) == ()


def test_fake_backend_emits_custom_script_events() -> None:
    plan = HookPlan(
        items=(
            HookPlanItem(
                item_id="item-1",
                kind="custom_script",
                enabled=True,
                inject_order=1,
                target=None,
                render_context={
                    "script_name": "trace_login",
                    "script_path": "/tmp/trace_login.js",
                },
                plugin_id="custom.local-script",
            ),
        )
    )

    events = FakeExecutionBackend().execute("job-1", plan)

    assert len(events) == 1
    assert events[0].event_type == "script_loaded"
    assert events[0].class_name == "custom.script"
    assert events[0].method_name == "trace_login"


def test_fake_backend_respects_inject_order_when_plan_items_are_unsorted() -> None:
    target = MethodHookTarget(
        target_id="target-1",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        source_origin="method_index",
    )
    plan = HookPlan(
        items=(
            HookPlanItem(
                item_id="item-2",
                kind="method_hook",
                enabled=True,
                inject_order=2,
                target=target,
                render_context={},
                plugin_id="builtin.method-hook",
            ),
            HookPlanItem(
                item_id="item-1",
                kind="custom_script",
                enabled=True,
                inject_order=1,
                target=None,
                render_context={
                    "script_name": "trace_login",
                    "script_path": "/tmp/trace_login.js",
                },
                plugin_id="custom.local-script",
            ),
        )
    )

    events = FakeExecutionBackend().execute("job-1", plan)

    assert [event.event_type for event in events] == ["script_loaded", "method_call"]
    assert [event.method_name for event in events] == ["trace_login", "buildUploadUrl"]


def test_fake_backend_emits_template_hook_events() -> None:
    plan = HookPlan(
        items=(
            HookPlanItem(
                item_id="item-1",
                kind="template_hook",
                enabled=True,
                inject_order=1,
                target=None,
                render_context={
                    "template_id": "ssl.okhttp3_unpin",
                    "template_name": "OkHttp3 SSL Unpinning",
                },
                plugin_id="builtin.ssl-okhttp3-unpin",
            ),
        )
    )

    events = FakeExecutionBackend().execute("job-1", plan)

    assert len(events) == 1
    assert events[0].event_type == "template_loaded"
    assert events[0].class_name == "builtin.template"
    assert events[0].method_name == "OkHttp3 SSL Unpinning"
