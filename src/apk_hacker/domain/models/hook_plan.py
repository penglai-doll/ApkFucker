from __future__ import annotations

from dataclasses import dataclass

from apk_hacker.domain.models.indexes import MethodIndexEntry


@dataclass(frozen=True, slots=True)
class HookPlanSource:
    source_id: str
    kind: str
    method: MethodIndexEntry | None = None
    script_name: str | None = None
    script_path: str | None = None
    template_id: str | None = None
    template_name: str | None = None
    plugin_id: str | None = None

    @classmethod
    def from_method(cls, method: MethodIndexEntry) -> "HookPlanSource":
        signature = ",".join(method.parameter_types)
        return cls(
            source_id=f"method:{method.class_name}:{method.method_name}:{signature}:{method.source_path}",
            kind="method_hook",
            method=method,
        )

    @classmethod
    def from_custom_script(cls, script_name: str, script_path: str) -> "HookPlanSource":
        return cls(
            source_id=f"custom_script:{script_path}",
            kind="custom_script",
            script_name=script_name,
            script_path=script_path,
        )

    @classmethod
    def from_template(cls, template_id: str, template_name: str, plugin_id: str) -> "HookPlanSource":
        return cls(
            source_id=f"template:{plugin_id}:{template_id}",
            kind="template_hook",
            template_id=template_id,
            template_name=template_name,
            plugin_id=plugin_id,
        )


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
