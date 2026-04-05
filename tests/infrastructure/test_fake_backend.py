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


def test_fake_backend_skips_disabled_and_targetless_items() -> None:
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
                kind="custom_script",
                enabled=True,
                inject_order=2,
                target=None,
                render_context={"script_path": "/tmp/demo.js"},
                plugin_id="custom.local-script",
            ),
        )
    )

    assert FakeExecutionBackend().execute("job-1", plan) == ()
