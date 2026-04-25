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


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    schema_version: str
    case_id: str
    sample_path: str
    artifacts: tuple[ArtifactRef, ...]
