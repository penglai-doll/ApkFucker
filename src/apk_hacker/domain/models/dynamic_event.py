from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apk_hacker.domain.models.hook_event import HookEvent


@dataclass(frozen=True, slots=True)
class DynamicEvent:
    timestamp: str
    job_id: str
    session_id: str | None
    event_type: str
    hook_type: str
    source: str
    source_script: str | None
    class_name: str
    method_name: str
    arguments: tuple[str, ...]
    return_value: str | None
    stacktrace: str
    raw_payload: dict[str, Any]
    schema_version: str = "dynamic-event.v1"

    @classmethod
    def from_hook_event(cls, event: HookEvent) -> "DynamicEvent":
        raw_payload = dict(event.raw_payload)
        hook_type = _first_text(raw_payload, "hook_type", "category") or _infer_hook_type(event.event_type)
        return cls(
            timestamp=event.timestamp,
            job_id=event.job_id,
            session_id=_first_text(raw_payload, "session_id"),
            event_type=event.event_type,
            hook_type=hook_type,
            source=event.source,
            source_script=_first_text(raw_payload, "source_script", "script_name"),
            class_name=event.class_name,
            method_name=event.method_name,
            arguments=event.arguments,
            return_value=event.return_value,
            stacktrace=event.stacktrace,
            raw_payload=raw_payload,
        )

    @property
    def message(self) -> str:
        parts = [f"{self.class_name}.{self.method_name}"]
        if self.return_value:
            parts.append(self.return_value)
        return " -> ".join(parts)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "job_id": self.job_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "hook_type": self.hook_type,
            "source": self.source,
            "source_script": self.source_script,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "arguments": list(self.arguments),
            "return_value": self.return_value,
            "stacktrace": self.stacktrace,
            "raw_payload": dict(self.raw_payload),
        }


def _first_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _infer_hook_type(event_type: str) -> str:
    if event_type.startswith("crypto_"):
        return "crypto"
    if event_type.startswith("ssl_"):
        return "ssl_unpinning"
    if event_type.startswith("frida_"):
        return "frida"
    if event_type.startswith("app_install"):
        return "app_install"
    if event_type.startswith("device_"):
        return "device"
    if event_type in {"method_call", "method_return", "method_error"}:
        return "method"
    if event_type == "template_loaded":
        return "template"
    return "runtime"
