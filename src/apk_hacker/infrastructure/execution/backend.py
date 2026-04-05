from __future__ import annotations

from abc import ABC, abstractmethod

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent


class ExecutionBackendUnavailable(RuntimeError):
    pass


class ExecutionBackend(ABC):
    @abstractmethod
    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        raise NotImplementedError
