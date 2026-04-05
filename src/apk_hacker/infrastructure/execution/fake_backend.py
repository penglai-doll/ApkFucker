from __future__ import annotations

from datetime import datetime, timezone

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.backend import ExecutionBackend


class FakeExecutionBackend(ExecutionBackend):
    def execute(self, job_id: str, plan: HookPlan) -> tuple[HookEvent, ...]:
        events: list[HookEvent] = []

        for item in sorted(plan.items, key=lambda plan_item: plan_item.inject_order):
            if not item.enabled:
                continue

            if item.target is not None:
                events.append(
                    HookEvent(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        job_id=job_id,
                        event_type="method_call",
                        source="fake",
                        class_name=item.target.class_name,
                        method_name=item.target.method_name,
                        arguments=item.target.parameter_types,
                        return_value="fake-return",
                        stacktrace=f"{item.target.class_name}.{item.target.method_name}:1",
                        raw_payload={"plugin_id": item.plugin_id or ""},
                    )
                )
                continue

            if item.kind != "custom_script":
                continue

            script_name = str(item.render_context.get("script_name", "custom_script"))
            script_path = str(item.render_context.get("script_path", ""))
            events.append(
                HookEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    job_id=job_id,
                    event_type="script_loaded",
                    source="fake",
                    class_name="custom.script",
                    method_name=script_name,
                    arguments=(script_path,),
                    return_value="script-ready",
                    stacktrace=f"custom.script.{script_name}:1",
                    raw_payload={
                        "plugin_id": item.plugin_id or "",
                        "script_path": script_path,
                    },
                )
            )

        return tuple(events)
