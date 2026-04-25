from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    source_type: str
    path: str | None
    line: int | None
    excerpt: str | None
    tags: tuple[str, ...]
    metadata: dict[str, object]
