from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from apk_hacker.domain.models.hook_plan import HookPlan


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    job_id: str
    plan: HookPlan
    package_name: str | None = None
    sample_path: Path | None = None
    runtime_env: dict[str, str] = field(default_factory=dict)
