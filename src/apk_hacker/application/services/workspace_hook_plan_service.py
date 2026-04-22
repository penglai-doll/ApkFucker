from __future__ import annotations

from dataclasses import replace

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.hook_plan_service import stable_hook_item_id
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndexEntry


class WorkspaceHookPlanService:
    def __init__(self, hook_plan_service: HookPlanService | None = None) -> None:
        self._hook_plan_service = hook_plan_service or HookPlanService()

    def rerender(self, state: WorkspaceRuntimeState) -> WorkspaceRuntimeState:
        return replace(
            state,
            rendered_hook_plan=self._hook_plan_service.plan_for_sources(
                list(state.selected_hook_sources),
                previous_plan=state.rendered_hook_plan,
            ),
        )

    def rerender_if_source_selected(self, state: WorkspaceRuntimeState, *, source_path: str) -> WorkspaceRuntimeState:
        if any(source.kind == "custom_script" and source.script_path == source_path for source in state.selected_hook_sources):
            return self.rerender(state)
        return state

    def add_method_source(self, state: WorkspaceRuntimeState, method: MethodIndexEntry) -> WorkspaceRuntimeState:
        return self.add_source(state, HookPlanSource.from_method(method))

    def add_source(self, state: WorkspaceRuntimeState, source: HookPlanSource) -> WorkspaceRuntimeState:
        if any(existing.source_id == source.source_id for existing in state.selected_hook_sources):
            return state
        return self.replace_sources(state, (*state.selected_hook_sources, source))

    def replace_sources(
        self,
        state: WorkspaceRuntimeState,
        selected_hook_sources: tuple[HookPlanSource, ...],
    ) -> WorkspaceRuntimeState:
        return self.rerender(replace(state, selected_hook_sources=selected_hook_sources))

    def replace_custom_script_source(
        self,
        state: WorkspaceRuntimeState,
        *,
        old_script_path: str,
        new_script_name: str,
        new_script_path: str,
    ) -> WorkspaceRuntimeState:
        if not any(source.kind == "custom_script" and source.script_path == old_script_path for source in state.selected_hook_sources):
            return state
        selected_hook_sources = tuple(
            HookPlanSource.from_custom_script(new_script_name, new_script_path)
            if source.kind == "custom_script" and source.script_path == old_script_path
            else source
            for source in state.selected_hook_sources
        )
        return self.replace_sources(state, selected_hook_sources)

    def remove_custom_script_source(self, state: WorkspaceRuntimeState, *, script_path: str) -> WorkspaceRuntimeState:
        selected_hook_sources = tuple(
            source
            for source in state.selected_hook_sources
            if not (source.kind == "custom_script" and source.script_path == script_path)
        )
        if len(selected_hook_sources) == len(state.selected_hook_sources):
            return state
        return self.replace_sources(state, selected_hook_sources)

    def remove_item(self, state: WorkspaceRuntimeState, item_id: str) -> WorkspaceRuntimeState:
        remaining = tuple(
            source for source in state.selected_hook_sources if stable_hook_item_id(source.source_id) != item_id
        )
        if len(remaining) == len(state.selected_hook_sources):
            raise KeyError(item_id)
        return self.replace_sources(state, remaining)

    def clear(self, state: WorkspaceRuntimeState) -> WorkspaceRuntimeState:
        return replace(
            state,
            selected_hook_sources=(),
            rendered_hook_plan=HookPlan(items=()),
        )

    def update_item(
        self,
        state: WorkspaceRuntimeState,
        item_id: str,
        *,
        enabled: bool | None = None,
        inject_order: int | None = None,
    ) -> WorkspaceRuntimeState:
        if enabled is None and inject_order is None:
            raise ValueError("At least one hook plan field must be updated.")

        current_items = list(state.rendered_hook_plan.items)
        current_index = next((index for index, item in enumerate(current_items) if item.item_id == item_id), None)
        if current_index is None:
            raise KeyError(item_id)
        if inject_order is not None and not 1 <= inject_order <= len(current_items):
            raise ValueError("Hook plan order is out of range.")

        updated_item = current_items[current_index]
        if enabled is not None:
            updated_item = replace(updated_item, enabled=enabled)
        current_items[current_index] = updated_item

        visible_source_indices = [
            index for index, source in enumerate(state.selected_hook_sources) if _source_is_plannable(source)
        ]
        if len(visible_source_indices) < len(current_items):
            visible_source_indices = visible_source_indices[: len(current_items)]
        visible_sources = [state.selected_hook_sources[index] for index in visible_source_indices]

        if inject_order is not None:
            target_index = inject_order - 1
            moved_item = current_items.pop(current_index)
            current_items.insert(target_index, moved_item)
            if current_index < len(visible_sources):
                source = visible_sources.pop(current_index)
                visible_sources.insert(target_index, source)

        normalized_items = tuple(
            replace(item, inject_order=index)
            for index, item in enumerate(current_items, start=1)
        )

        selected_hook_sources = list(state.selected_hook_sources)
        for slot, source in zip(visible_source_indices, visible_sources, strict=False):
            selected_hook_sources[slot] = source

        return replace(
            state,
            selected_hook_sources=tuple(selected_hook_sources),
            rendered_hook_plan=self._hook_plan_service.render_existing_plan(HookPlan(items=normalized_items)),
        )


def _source_is_plannable(source: HookPlanSource) -> bool:
    if source.method is not None:
        return True
    if source.kind == "template_hook" and source.template_id is not None and source.template_name is not None:
        return True
    return source.kind == "custom_script" and source.script_name is not None and source.script_path is not None
