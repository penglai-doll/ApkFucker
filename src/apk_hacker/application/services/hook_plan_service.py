from __future__ import annotations

from uuid import uuid4

from apk_hacker.application.plugins.builtin.method_hook import MethodHookPlugin
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry


class HookPlanService:
    def __init__(self) -> None:
        self._method_hook = MethodHookPlugin()

    def plan_for_methods(self, methods: list[MethodIndexEntry]) -> HookPlan:
        items: list[HookPlanItem] = []
        for inject_order, method in enumerate(methods, start=1):
            script = self._method_hook.build(
                method.class_name,
                method.method_name,
                method.parameter_types,
            )
            target = MethodHookTarget(
                target_id=str(uuid4()),
                class_name=method.class_name,
                method_name=method.method_name,
                parameter_types=method.parameter_types,
                return_type=method.return_type,
                source_origin="method_index",
            )
            items.append(
                HookPlanItem(
                    item_id=str(uuid4()),
                    kind=script.kind,
                    enabled=True,
                    inject_order=inject_order,
                    target=target,
                    render_context=script.render_context,
                    plugin_id=script.plugin_id,
                )
            )
        return HookPlan(items=tuple(items))
