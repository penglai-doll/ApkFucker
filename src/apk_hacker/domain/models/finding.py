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

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", tuple(str(value) for value in self.evidence_ids))
        object.__setattr__(self, "tags", tuple(str(value) for value in self.tags))

    def to_payload(self) -> dict[str, object]:
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "tags": list(self.tags),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "Finding | None":
        if not isinstance(payload, dict):
            return None
        required_text = (
            payload.get("finding_id"),
            payload.get("category"),
            payload.get("severity"),
            payload.get("title"),
            payload.get("summary"),
        )
        confidence = payload.get("confidence")
        if not all(isinstance(value, str) for value in required_text) or not isinstance(confidence, (int, float)):
            return None
        return cls(
            finding_id=str(payload["finding_id"]),
            category=str(payload["category"]),
            severity=str(payload["severity"]),
            title=str(payload["title"]),
            summary=str(payload["summary"]),
            confidence=float(confidence),
            evidence_ids=_tuple_of_text(payload.get("evidence_ids", [])),
            tags=_tuple_of_text(payload.get("tags", [])),
        )


def _tuple_of_text(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, (list, tuple)):
        return ()
    return tuple(str(value) for value in payload)
