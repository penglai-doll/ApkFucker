from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    category: str
    severity: str
    title: str
    summary: str
    confidence: float
    evidence_ids: tuple[str, ...]
    tags: tuple[str, ...]
