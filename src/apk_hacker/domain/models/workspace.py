from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    case_id: str
    title: str
    workspace_root: Path
    sample_path: Path
