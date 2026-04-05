from __future__ import annotations

from abc import ABC, abstractmethod

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan


class ExecutionBackend(ABC):
    @abstractmethod
    def execute(self, job_id: str, plan: HookPlan) -> tuple[HookEvent, ...]:
        raise NotImplementedError
