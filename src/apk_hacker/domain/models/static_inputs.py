from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ArtifactPaths


@dataclass(frozen=True, slots=True)
class StaticInputs:
    sample_path: Path
    package_name: str
    technical_tags: tuple[str, ...]
    dangerous_permissions: tuple[str, ...]
    callback_endpoints: tuple[str, ...]
    callback_clues: tuple[str, ...]
    crypto_signals: tuple[str, ...]
    packer_hints: tuple[str, ...]
    limitations: tuple[str, ...]
    artifact_paths: ArtifactPaths

