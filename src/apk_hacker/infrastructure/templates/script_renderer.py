from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem


class ScriptRenderer:
    def __init__(self, templates_root: Path | None = None) -> None:
        self._templates_root = templates_root or Path(__file__).resolve().parents[4] / "templates"
        self._environment = Environment(
            loader=FileSystemLoader(str(self._templates_root)),
            autoescape=False,
            keep_trailing_newline=True,
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def render_plan(self, plan: HookPlan) -> HookPlan:
        return HookPlan(items=tuple(self._render_item(item) for item in plan.items))

    def _render_item(self, item: HookPlanItem) -> HookPlanItem:
        context = dict(item.render_context)
        context["rendered_script"] = self.render_item(item)
        return replace(item, render_context=context)

    def render_item(self, item: HookPlanItem) -> str:
        if item.kind == "custom_script":
            script_path = Path(str(item.render_context.get("script_path", ""))).expanduser().resolve()
            return script_path.read_text(encoding="utf-8")
        if item.kind == "method_hook":
            return self._environment.get_template("generic/method_hook.js.j2").render(item.render_context)
        if item.kind == "template_hook":
            template_id = str(item.render_context.get("template_id", "")).strip()
            if not template_id:
                raise ValueError("template_hook plan item is missing template_id")
            template_path = f"{template_id.replace('.', '/')}.js.j2"
            return self._environment.get_template(template_path).render(item.render_context)
        return ""
