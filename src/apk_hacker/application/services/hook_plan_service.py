from __future__ import annotations

from uuid import uuid4

from apk_hacker.application.services.custom_script_service import CustomScriptRecord
from apk_hacker.application.plugins.builtin.method_hook import MethodHookPlugin
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry


class HookPlanService:
    def __init__(self) -> None:
        self._method_hook = MethodHookPlugin()

    def plan_for_methods(self, methods: list[MethodIndexEntry]) -> HookPlan:
        return self.plan_for_selection(methods, [])

    def plan_for_selection(
        self,
        methods: list[MethodIndexEntry],
        custom_scripts: list[CustomScriptRecord],
    ) -> HookPlan:
        items: list[HookPlanItem] = []
        for inject_order, method in enumerate(methods, start=1):
            items.append(self._build_method_item(method, inject_order))
        for offset, script in enumerate(custom_scripts, start=len(items) + 1):
            items.append(self._build_custom_script_item(script, offset))
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
    def _build_custom_script_item(record: CustomScriptRecord, inject_order: int) -> HookPlanItem:
        return HookPlanItem(
            item_id=str(uuid4()),
            kind="custom_script",
            enabled=True,
            inject_order=inject_order,
            target=None,
            render_context={
                "script_name": record.name,
                "script_path": str(record.script_path),
            },
            plugin_id="custom.local-script",
        )
