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
    static_markdown_report: Path | None = None
    static_docx_report: Path | None = None
    artifact_manifest: Path | None = None
    static_result: Path | None = None
    findings_jsonl: Path | None = None
    evidence_jsonl: Path | None = None
    method_index_jsonl: Path | None = None
    class_index_jsonl: Path | None = None


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
        static_markdown_report=_coerce_path(artifact_paths.get("static_markdown_report")),
        static_docx_report=_coerce_path(artifact_paths.get("static_docx_report")),
        artifact_manifest=_coerce_path(artifact_paths.get("artifact_manifest")),
        static_result=_coerce_path(artifact_paths.get("static_result")),
        findings_jsonl=_coerce_path(artifact_paths.get("findings_jsonl")),
        evidence_jsonl=_coerce_path(artifact_paths.get("evidence_jsonl")),
        method_index_jsonl=_coerce_path(artifact_paths.get("method_index_jsonl")),
        class_index_jsonl=_coerce_path(artifact_paths.get("class_index_jsonl")),
    )
