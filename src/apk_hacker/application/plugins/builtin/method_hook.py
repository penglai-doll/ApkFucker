from __future__ import annotations

from apk_hacker.application.plugins.contracts import HookStrategyPlugin, PlannedScript


class MethodHookPlugin(HookStrategyPlugin):
    plugin_id = "builtin.method-hook"

    def build(self, class_name: str, method_name: str, parameter_types: tuple[str, ...]) -> PlannedScript:
        return PlannedScript(
            plugin_id=self.plugin_id,
            kind="method_hook",
            render_context={
                "className": class_name,
                "methodName": method_name,
                "paramTypes": list(parameter_types),
            },
        )
