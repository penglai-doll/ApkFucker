from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaseQueueItem:
    case_id: str
    title: str
    workspace_root: str
