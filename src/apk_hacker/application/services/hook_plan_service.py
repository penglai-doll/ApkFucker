from __future__ import annotations

from dataclasses import replace
from hashlib import sha1

from apk_hacker.application.plugins.builtin.method_hook import MethodHookPlugin
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, HookPlanSource, MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.infrastructure.templates.script_renderer import ScriptRenderer


def stable_hook_item_id(source_id: str) -> str:
    digest = sha1(source_id.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"hook-{digest}"


class HookPlanService:
    def __init__(self, renderer: ScriptRenderer | None = None) -> None:
        self._method_hook = MethodHookPlugin()
        self._renderer = renderer or ScriptRenderer()

    def plan_for_methods(self, methods: list[MethodIndexEntry]) -> HookPlan:
        return self.plan_for_sources([HookPlanSource.from_method(method) for method in methods])

    def plan_for_sources(self, sources: list[HookPlanSource], previous_plan: HookPlan | None = None) -> HookPlan:
        items: list[HookPlanItem] = []
        for inject_order, source in enumerate(sources, start=1):
            if source.method is not None:
                items.append(self._build_method_item(source, inject_order))
                continue
            if source.kind == "template_hook" and source.template_id is not None and source.template_name is not None:
                items.append(
                    self._build_template_item(
                        source=source,
                        template_id=source.template_id,
                        template_name=source.template_name,
                        plugin_id=source.plugin_id or f"builtin.{source.template_id}",
                        inject_order=inject_order,
                    )
                )
                continue
            if source.kind != "custom_script" or source.script_name is None or source.script_path is None:
                continue
            items.append(
                self._build_custom_script_item(
                    source=source,
                    script_name=source.script_name,
                    script_path=source.script_path,
                    inject_order=inject_order,
                )
            )
        if previous_plan is not None:
            previous_by_id = {item.item_id: item for item in previous_plan.items}
            items = [
                replace(
                    item,
                    enabled=previous_item.enabled,
                    inject_order=previous_item.inject_order,
                )
                if (previous_item := previous_by_id.get(item.item_id)) is not None
                else item
                for item in items
            ]
            items = [
                replace(item, inject_order=inject_order)
                for inject_order, item in enumerate(
                    sorted(items, key=lambda candidate: candidate.inject_order),
                    start=1,
                )
            ]
        return self.render_existing_plan(HookPlan(items=tuple(items)))

    def render_existing_plan(self, plan: HookPlan) -> HookPlan:
        return self._renderer.render_plan(plan)

    def _build_method_item(self, source: HookPlanSource, inject_order: int) -> HookPlanItem:
        method = source.method
        if method is None:
            raise ValueError("Hook source does not reference a method.")
        script = self._method_hook.build(
            method.class_name,
            method.method_name,
            method.parameter_types,
        )
        source_id = HookPlanSource.from_method(method).source_id
        item_id = stable_hook_item_id(source_id)
        target = MethodHookTarget(
            target_id=item_id,
            class_name=method.class_name,
            method_name=method.method_name,
            parameter_types=method.parameter_types,
            return_type=method.return_type,
            source_origin="method_index",
        )
        return HookPlanItem(
            item_id=item_id,
            kind=script.kind,
            source_kind=source.source_kind or "selected_method",
            enabled=True,
            inject_order=inject_order,
            target=target,
            render_context=script.render_context,
            plugin_id=script.plugin_id,
            evidence_ids=method.evidence,
            tags=method.tags,
        )

    @staticmethod
    def _build_custom_script_item(
        *,
        source: HookPlanSource,
        script_name: str,
        script_path: str,
        inject_order: int,
    ) -> HookPlanItem:
        source_id = source.source_id
        item_id = stable_hook_item_id(source_id)
        return HookPlanItem(
            item_id=item_id,
            kind="custom_script",
            source_kind=source.source_kind or "custom_script",
            enabled=True,
            inject_order=inject_order,
            target=None,
            render_context={
                "script_name": script_name,
                "script_path": script_path,
            },
            plugin_id="custom.local-script",
        )

    @staticmethod
    def _build_template_item(
        *,
        source: HookPlanSource,
        template_id: str,
        template_name: str,
        plugin_id: str,
        inject_order: int,
    ) -> HookPlanItem:
        source_id = source.source_id
        item_id = stable_hook_item_id(source_id)
        return HookPlanItem(
            item_id=item_id,
            kind="template_hook",
            source_kind=source.source_kind or "framework_plugin",
            enabled=True,
            inject_order=inject_order,
            target=None,
            render_context={
                "template_id": template_id,
                "template_name": template_name,
            },
            plugin_id=plugin_id,
            template_id=template_id,
        )
