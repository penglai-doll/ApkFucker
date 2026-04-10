from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    case_id: str
    title: str
    workspace_root: Path
    sample_path: Path
    workspace_version: int
    created_at: str
    updated_at: str
    sample_filename: str
