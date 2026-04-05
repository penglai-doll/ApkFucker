from __future__ import annotations

from uuid import uuid4

from apk_hacker.application.plugins.builtin.method_hook import MethodHookPlugin
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, HookPlanSource, MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry


class HookPlanService:
    def __init__(self) -> None:
        self._method_hook = MethodHookPlugin()

    def plan_for_methods(self, methods: list[MethodIndexEntry]) -> HookPlan:
        return self.plan_for_sources([HookPlanSource.from_method(method) for method in methods])

    def plan_for_sources(self, sources: list[HookPlanSource]) -> HookPlan:
        items: list[HookPlanItem] = []
        for inject_order, source in enumerate(sources, start=1):
            if source.method is not None:
                items.append(self._build_method_item(source.method, inject_order))
                continue
            if source.kind != "custom_script" or source.script_name is None or source.script_path is None:
                continue
            items.append(
                self._build_custom_script_item(
                    script_name=source.script_name,
                    script_path=source.script_path,
                    inject_order=inject_order,
                )
            )
        return HookPlan(items=tuple(items))

    def _build_method_item(self, method: MethodIndexEntry, inject_order: int) -> HookPlanItem:
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
        return HookPlanItem(
            item_id=str(uuid4()),
            kind=script.kind,
            enabled=True,
            inject_order=inject_order,
            target=target,
            render_context=script.render_context,
            plugin_id=script.plugin_id,
        )

    @staticmethod
    def _build_custom_script_item(script_name: str, script_path: str, inject_order: int) -> HookPlanItem:
        return HookPlanItem(
            item_id=str(uuid4()),
            kind="custom_script",
            enabled=True,
            inject_order=inject_order,
            target=None,
            render_context={
                "script_name": script_name,
                "script_path": script_path,
            },
            plugin_id="custom.local-script",
        )
