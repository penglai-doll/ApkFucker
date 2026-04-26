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

    def to_payload(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "job_id": self.job_id,
            "event_type": self.event_type,
            "source": self.source,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "arguments": list(self.arguments),
            "return_value": self.return_value,
            "stacktrace": self.stacktrace,
            "raw_payload": dict(self.raw_payload),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "HookEvent | None":
        if not isinstance(payload, dict):
            return None
        required_text = (
            payload.get("timestamp"),
            payload.get("job_id"),
            payload.get("event_type"),
            payload.get("source"),
            payload.get("class_name"),
            payload.get("method_name"),
            payload.get("stacktrace"),
        )
        if not all(isinstance(value, str) for value in required_text):
            return None
        arguments_payload = payload.get("arguments", [])
        raw_payload = payload.get("raw_payload", {})
        return cls(
            timestamp=str(payload["timestamp"]),
            job_id=str(payload["job_id"]),
            event_type=str(payload["event_type"]),
            source=str(payload["source"]),
            class_name=str(payload["class_name"]),
            method_name=str(payload["method_name"]),
            arguments=(
                tuple(str(argument) for argument in arguments_payload)
                if isinstance(arguments_payload, (list, tuple))
                else ()
            ),
            return_value=str(payload["return_value"]) if payload.get("return_value") is not None else None,
            stacktrace=str(payload["stacktrace"]),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else {},
        )
