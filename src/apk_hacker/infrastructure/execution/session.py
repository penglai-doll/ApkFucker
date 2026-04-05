from __future__ import annotations

from dataclasses import dataclass

from apk_hacker.domain.models.hook_event import HookEvent


@dataclass(frozen=True, slots=True)
class ExecutionSession:
    job_id: str
    events: tuple[HookEvent, ...]

    def collect_events(self) -> tuple[HookEvent, ...]:
        return self.events
