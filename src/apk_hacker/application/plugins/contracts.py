from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlannedScript:
    plugin_id: str
    kind: str
    render_context: dict[str, object]


class HookStrategyPlugin:
    plugin_id: str

    def build(self, class_name: str, method_name: str, parameter_types: tuple[str, ...]) -> PlannedScript:
        raise NotImplementedError
