from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TrafficCaptureProvenance:
    kind: str
    label: str


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
class TrafficHostSummary:
    host: str
    flow_count: int
    suspicious_count: int
    https_flow_count: int


@dataclass(frozen=True, slots=True)
class TrafficCaptureSummary:
    https_flow_count: int
    matched_indicator_count: int
    top_hosts: tuple[TrafficHostSummary, ...]
    suspicious_hosts: tuple[TrafficHostSummary, ...]


@dataclass(frozen=True, slots=True)
class TrafficCapture:
    source_path: Path
    provenance: TrafficCaptureProvenance
    flow_count: int
    suspicious_count: int
    summary: TrafficCaptureSummary
    flows: tuple[TrafficFlowSummary, ...]

    @property
    def https_flow_count(self) -> int:
        return self.summary.https_flow_count

    @property
    def matched_indicator_count(self) -> int:
        return self.summary.matched_indicator_count

    @property
    def top_hosts(self) -> tuple[TrafficHostSummary, ...]:
        return self.summary.top_hosts

    @property
    def suspicious_hosts(self) -> tuple[TrafficHostSummary, ...]:
        return self.summary.suspicious_hosts


@dataclass(frozen=True, slots=True)
class LiveTrafficCaptureStatus:
    case_id: str
    status: str
    artifact_path: Path | None
    message: str | None


@dataclass(frozen=True, slots=True)
class LiveTrafficCaptureContext:
    case_id: str
    workspace_root: Path
    artifact_path: Path
    sample_path: Path
    package_name: str
    callback_endpoints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TrafficLiveCaptureState:
    status: str
    session_id: str | None = None
    output_path: Path | None = None
    preview_path: Path | None = None
    message: str | None = None
