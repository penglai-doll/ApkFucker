from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _coerce_path(value: object | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return Path(value).expanduser().resolve()


@dataclass(frozen=True, slots=True)
class ArtifactPaths:
    analysis_report: Path | None = None
    callback_config: Path | None = None
    noise_log: Path | None = None
    jadx_sources: Path | None = None
    jadx_project: Path | None = None


def coerce_artifact_paths(artifact_paths: Mapping[str, object] | ArtifactPaths | None) -> ArtifactPaths:
    if artifact_paths is None:
        return ArtifactPaths()
    if isinstance(artifact_paths, ArtifactPaths):
        return artifact_paths

    return ArtifactPaths(
        analysis_report=_coerce_path(artifact_paths.get("analysis_report")),
        callback_config=_coerce_path(artifact_paths.get("callback_config")),
        noise_log=_coerce_path(artifact_paths.get("noise_log")),
        jadx_sources=_coerce_path(artifact_paths.get("jadx_sources")),
        jadx_project=_coerce_path(artifact_paths.get("jadx_project")),
    )

