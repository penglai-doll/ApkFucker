from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

from apk_hacker.domain.models.hook_plan import HookPlan


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    job_id: str
    plan: HookPlan
    package_name: str | None = None
    sample_path: Path | None = None
    runtime_env: dict[str, str] = field(default_factory=dict)
    cancellation_event: Event | None = None


@dataclass(frozen=True, slots=True)
class ExecutionRuntimeOptions:
    device_serial: str = ""
    frida_server_binary_path: str = ""
    frida_server_remote_path: str = ""
    frida_session_seconds: str = ""
