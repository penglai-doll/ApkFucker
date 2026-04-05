from __future__ import annotations

from collections.abc import Callable

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.backend import ExecutionBackend, ExecutionBackendUnavailable


class RealExecutionBackend(ExecutionBackend):
    def __init__(
        self,
        runner: Callable[[str, HookPlan], tuple[HookEvent, ...]] | None = None,
    ) -> None:
        self._runner = runner

    def execute(self, job_id: str, plan: HookPlan) -> tuple[HookEvent, ...]:
        if self._runner is None:
            raise ExecutionBackendUnavailable(
                "Real device execution is not available because the backend is not configured."
            )
        return self._runner(job_id, plan)
