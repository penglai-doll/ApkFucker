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

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", tuple(str(value) for value in self.tags))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "path": self.path,
            "line": self.line,
            "excerpt": self.excerpt,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "Evidence | None":
        if not isinstance(payload, dict):
            return None
        evidence_id = payload.get("evidence_id")
        source_type = payload.get("source_type")
        if not isinstance(evidence_id, str) or not isinstance(source_type, str):
            return None
        line = payload.get("line")
        metadata = payload.get("metadata", {})
        return cls(
            evidence_id=evidence_id,
            source_type=source_type,
            path=str(payload["path"]) if isinstance(payload.get("path"), str) else None,
            line=int(line) if isinstance(line, int) else None,
            excerpt=str(payload["excerpt"]) if isinstance(payload.get("excerpt"), str) else None,
            tags=_tuple_of_text(payload.get("tags", [])),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
        )


def _tuple_of_text(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, (list, tuple)):
        return ()
    return tuple(str(value) for value in payload)
