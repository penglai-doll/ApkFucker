from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    path: str
    producer: str
    created_at: str
    metadata: dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "path": self.path,
            "producer": self.producer,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ArtifactRef | None":
        if not isinstance(payload, dict):
            return None
        required_text = (
            payload.get("artifact_id"),
            payload.get("kind"),
            payload.get("path"),
            payload.get("producer"),
            payload.get("created_at"),
        )
        if not all(isinstance(value, str) for value in required_text):
            return None
        metadata = payload.get("metadata", {})
        return cls(
            artifact_id=str(payload["artifact_id"]),
            kind=str(payload["kind"]),
            path=str(payload["path"]),
            producer=str(payload["producer"]),
            created_at=str(payload["created_at"]),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
        )


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    schema_version: str
    case_id: str
    sample_path: str
    artifacts: tuple[ArtifactRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "sample_path": self.sample_path,
            "artifacts": [artifact.to_payload() for artifact in self.artifacts],
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ArtifactManifest | None":
        if not isinstance(payload, dict):
            return None
        schema_version = payload.get("schema_version")
        case_id = payload.get("case_id")
        sample_path = payload.get("sample_path")
        if not all(isinstance(value, str) for value in (schema_version, case_id, sample_path)):
            return None
        artifacts_payload = payload.get("artifacts", [])
        if not isinstance(artifacts_payload, list):
            artifacts_payload = []
        return cls(
            schema_version=str(schema_version),
            case_id=str(case_id),
            sample_path=str(sample_path),
            artifacts=tuple(
                artifact
                for artifact in (ArtifactRef.from_payload(item) for item in artifacts_payload)
                if artifact is not None
            ),
        )
