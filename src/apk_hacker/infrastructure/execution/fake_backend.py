from __future__ import annotations

from datetime import datetime, timezone

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.backend import ExecutionBackend


class FakeExecutionBackend(ExecutionBackend):
    def execute(self, job_id: str, plan: HookPlan) -> tuple[HookEvent, ...]:
        events: list[HookEvent] = []

        for item in plan.items:
            if not item.enabled or item.target is None:
                continue

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

        return tuple(events)
