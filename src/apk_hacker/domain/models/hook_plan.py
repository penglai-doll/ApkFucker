from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MethodHookTarget:
    target_id: str
    class_name: str
    method_name: str
    parameter_types: tuple[str, ...]
    return_type: str
    source_origin: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class HookPlanItem:
    item_id: str
    kind: str
    enabled: bool
    inject_order: int
    target: MethodHookTarget | None
    render_context: dict[str, object]
    plugin_id: str | None = None


@dataclass(frozen=True, slots=True)
class HookPlan:
    items: tuple[HookPlanItem, ...]
