from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _load_plan() -> dict[str, object]:
    plan_path = os.environ.get("APKHACKER_PLAN_PATH", "")
    if not plan_path:
        raise RuntimeError("APKHACKER_PLAN_PATH is required")
    return json.loads(Path(plan_path).read_text(encoding="utf-8"))


def _event_for_item(item: dict[str, object], scripts_dir: Path) -> dict[str, object]:
    kind = str(item.get("kind", "unknown"))
    target = item.get("target")
    render_context = item.get("render_context", {})
    package_name = os.environ.get("APKHACKER_TARGET_PACKAGE", "")
    if not isinstance(render_context, dict):
        render_context = {}

    method_name = kind
    class_name = "demo.real"
    arguments: list[str] = []

    if isinstance(target, dict):
        class_name = str(target.get("class_name", class_name))
        method_name = str(target.get("method_name", method_name))
        arguments = [path.name for path in sorted(scripts_dir.glob("*.js"))]
        if package_name:
            arguments.append(package_name)
        return_value = "demo-real-method"
        event_type = "method_call"
    elif kind == "template_hook":
        class_name = "demo.template"
        method_name = str(render_context.get("template_name", kind))
        arguments = [str(render_context.get("template_id", ""))]
        return_value = "demo-real-template"
        event_type = "template_loaded"
    else:
        class_name = "demo.script"
        method_name = str(render_context.get("script_name", kind))
        arguments = [str(render_context.get("script_path", ""))]
        return_value = "demo-real-script"
        event_type = "script_loaded"

    return {
        "event_type": event_type,
        "class_name": class_name,
        "method_name": method_name,
        "arguments": arguments,
        "return_value": return_value,
        "stacktrace": f"{class_name}.{method_name}:1",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-demo-real-backend",
        description="Demo command bridge for APKHacker real backend integration.",
    )
    parser.parse_args()

    plan = _load_plan()
    scripts_dir = Path(os.environ.get("APKHACKER_SCRIPTS_DIR", ".")).expanduser().resolve()
    for item in plan.get("items", []):
        if not isinstance(item, dict):
            continue
        print(json.dumps(_event_for_item(item, scripts_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
