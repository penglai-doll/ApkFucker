from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HookEvent:
    timestamp: str
    job_id: str
    event_type: str
    source: str
    class_name: str
    method_name: str
    arguments: tuple[str, ...]
    return_value: str | None
    stacktrace: str
    raw_payload: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "arguments",
            tuple(str(argument) for argument in self.arguments),
        )
        object.__setattr__(self, "raw_payload", dict(self.raw_payload))
