from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TrafficFlowSummary:
    flow_id: str
    method: str
    url: str
    status_code: int | None
    mime_type: str | None
    request_preview: str
    response_preview: str
    matched_indicators: tuple[str, ...]
    suspicious: bool


@dataclass(frozen=True, slots=True)
class TrafficCapture:
    source_path: Path
    flow_count: int
    suspicious_count: int
    flows: tuple[TrafficFlowSummary, ...]
