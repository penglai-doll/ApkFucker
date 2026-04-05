from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    job_id: str
    status: str
    input_target: str
    created_at: str
    updated_at: str
    artifacts: dict[str, str] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def queued(cls, input_target: str) -> "AnalysisJob":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            job_id=str(uuid4()),
            status="queued",
            input_target=input_target,
            created_at=now,
            updated_at=now,
        )
