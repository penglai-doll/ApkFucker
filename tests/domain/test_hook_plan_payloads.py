from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.hook_plan import MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.domain.models.hook_plan import HookPlanItem


def _method() -> MethodIndexEntry:
    return MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="sources/com/demo/net/Config.java",
        line_hint=4,
        declaration="public String buildUploadUrl(String host)",
        source_preview="return host + \"/upload\";",
        tags=("network",),
        evidence=("evidence-1",),
    )


def test_method_index_entry_payload_round_trips() -> None:
    method = _method()

    assert MethodIndexEntry.from_payload(method.to_payload()) == method


def test_hook_plan_source_payload_round_trips_method_and_template_metadata() -> None:
    method_source = HookPlanSource.from_method(
        _method(),
        reason="Callback URL builder.",
        matched_terms=("upload",),
        source_signals=("callback_clues",),
    )
    template_source = HookPlanSource.from_template(
        template_id="ssl.okhttp3_unpin",
        template_name="OkHttp3 SSL Unpinning",
        plugin_id="builtin.ssl-okhttp3-unpin",
        reason="TLS interception needed.",
        matched_terms=("okhttp3",),
        source_signals=("technical_tags",),
        template_event_types=("ssl_unpinning_bypass",),
        template_category="ssl",
        requires_root=False,
        supports_offline=True,
    )

    assert HookPlanSource.from_payload(method_source.to_payload()) == method_source
    assert HookPlanSource.from_payload(template_source.to_payload()) == template_source


def test_hook_plan_payload_round_trips_items() -> None:
    item = HookPlanItem(
        item_id="hook-1",
        kind="method_hook",
        source_kind="selected_method",
        enabled=True,
        inject_order=10,
        target=MethodHookTarget(
            target_id="target-1",
            class_name="com.demo.net.Config",
            method_name="buildUploadUrl",
            parameter_types=("String",),
            return_type="String",
            source_origin="manual",
            notes="User selected.",
        ),
        render_context={"className": "com.demo.net.Config"},
        plugin_id=None,
        template_id=None,
        evidence_ids=("evidence-1",),
        tags=("network",),
        reason="Trace callback URL construction.",
        matched_terms=("upload",),
        source_signals=("callback_clues",),
    )
    plan = HookPlan(items=(item,))

    assert HookPlan.from_payload(plan.to_payload()) == plan
