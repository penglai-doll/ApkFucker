from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent


def _normalize_failure_message(message: str) -> str:
    prefix = "Real device execution failed: "
    return message[len(prefix) :] if message.startswith(prefix) else message


class ExecutionBackendUnavailable(RuntimeError):
    def __init__(self, message: str, *, error_code: str = "backend_unavailable") -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = _normalize_failure_message(message)


class ExecutionCancelled(RuntimeError):
    pass


ExecutionProgressCallback = Callable[[str], None]


class ExecutionBackend(ABC):
    @abstractmethod
    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        raise NotImplementedError
