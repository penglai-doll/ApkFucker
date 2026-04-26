from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class TrafficCaptureProvenance:
    kind: str
    label: str

    def to_payload(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "label": self.label,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "TrafficCaptureProvenance | None":
        if not isinstance(payload, dict):
            return None
        kind = payload.get("kind")
        label = payload.get("label")
        if not isinstance(kind, str) or not isinstance(label, str):
            return None
        return cls(kind=kind, label=label)


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "method", self.method.upper())
        object.__setattr__(self, "matched_indicators", tuple(str(value) for value in self.matched_indicators))

    def to_payload(self) -> dict[str, object]:
        return {
            "flow_id": self.flow_id,
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "mime_type": self.mime_type,
            "request_preview": self.request_preview,
            "response_preview": self.response_preview,
            "matched_indicators": list(self.matched_indicators),
            "suspicious": self.suspicious,
        }


@dataclass(frozen=True, slots=True)
class TrafficFlow:
    flow_id: str
    method: str
    url: str
    status_code: int | None
    mime_type: str | None
    request_preview: str
    response_preview: str
    matched_indicators: tuple[str, ...]
    suspicious: bool
    capture_id: str
    timestamp: str | None = None
    scheme: str = ""
    host: str = ""
    path: str = ""
    request_headers: tuple[tuple[str, str], ...] = ()
    response_headers: tuple[tuple[str, str], ...] = ()
    request_body_size: int | None = None
    response_body_size: int | None = None
    raw_payload: dict[str, object] | None = None
    schema_version: str = "traffic-flow.v1"

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        scheme = self.scheme or parsed.scheme.lower()
        host = self.host or (parsed.hostname or parsed.netloc or "")
        path = self.path or parsed.path or "/"
        object.__setattr__(self, "method", self.method.upper())
        object.__setattr__(self, "scheme", scheme)
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "matched_indicators", tuple(str(value) for value in self.matched_indicators))
        object.__setattr__(
            self,
            "request_headers",
            tuple((str(name), str(value)) for name, value in self.request_headers),
        )
        object.__setattr__(
            self,
            "response_headers",
            tuple((str(name), str(value)) for name, value in self.response_headers),
        )
        object.__setattr__(self, "raw_payload", dict(self.raw_payload or {}))

    @classmethod
    def from_summary(cls, capture_id: str, summary: TrafficFlowSummary) -> "TrafficFlow":
        parsed = urlparse(summary.url)
        return cls(
            capture_id=capture_id,
            flow_id=summary.flow_id,
            method=summary.method,
            url=summary.url,
            scheme=parsed.scheme.lower(),
            host=parsed.hostname or parsed.netloc or "",
            path=parsed.path or "/",
            status_code=summary.status_code,
            mime_type=summary.mime_type,
            request_preview=summary.request_preview,
            response_preview=summary.response_preview,
            matched_indicators=summary.matched_indicators,
            suspicious=summary.suspicious,
        )

    @property
    def summary(self) -> TrafficFlowSummary:
        return TrafficFlowSummary(
            flow_id=self.flow_id,
            method=self.method,
            url=self.url,
            status_code=self.status_code,
            mime_type=self.mime_type,
            request_preview=self.request_preview,
            response_preview=self.response_preview,
            matched_indicators=self.matched_indicators,
            suspicious=self.suspicious,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capture_id": self.capture_id,
            "flow_id": self.flow_id,
            "timestamp": self.timestamp,
            "method": self.method,
            "url": self.url,
            "scheme": self.scheme,
            "host": self.host,
            "path": self.path,
            "status_code": self.status_code,
            "mime_type": self.mime_type,
            "request_headers": [
                {"name": name, "value": value}
                for name, value in self.request_headers
            ],
            "response_headers": [
                {"name": name, "value": value}
                for name, value in self.response_headers
            ],
            "request_preview": self.request_preview,
            "response_preview": self.response_preview,
            "request_body_size": self.request_body_size,
            "response_body_size": self.response_body_size,
            "matched_indicators": list(self.matched_indicators),
            "suspicious": self.suspicious,
            "raw_payload": dict(self.raw_payload or {}),
        }

    @classmethod
    def from_payload(cls, capture_id: str, payload: object) -> "TrafficFlow | None":
        if not isinstance(payload, dict):
            return None
        flow_id = payload.get("flow_id")
        method = payload.get("method")
        url = payload.get("url")
        if not isinstance(flow_id, str) or not isinstance(method, str) or not isinstance(url, str):
            return None
        matched_indicators = payload.get("matched_indicators", [])
        if not isinstance(matched_indicators, list):
            matched_indicators = []
        raw_payload = payload.get("raw_payload")
        return cls(
            schema_version=str(payload.get("schema_version") or "traffic-flow.v1"),
            capture_id=str(payload.get("capture_id") or capture_id),
            flow_id=flow_id,
            timestamp=str(payload["timestamp"]) if isinstance(payload.get("timestamp"), str) else None,
            method=method,
            url=url,
            scheme=str(payload["scheme"]) if isinstance(payload.get("scheme"), str) else "",
            host=str(payload["host"]) if isinstance(payload.get("host"), str) else "",
            path=str(payload["path"]) if isinstance(payload.get("path"), str) else "",
            status_code=payload.get("status_code") if isinstance(payload.get("status_code"), int) else None,
            mime_type=payload.get("mime_type") if isinstance(payload.get("mime_type"), str) else None,
            request_headers=_headers_from_payload(payload.get("request_headers")),
            response_headers=_headers_from_payload(payload.get("response_headers")),
            request_preview=str(payload.get("request_preview", "")),
            response_preview=str(payload.get("response_preview", "")),
            request_body_size=payload.get("request_body_size") if isinstance(payload.get("request_body_size"), int) else None,
            response_body_size=payload.get("response_body_size") if isinstance(payload.get("response_body_size"), int) else None,
            matched_indicators=tuple(str(value) for value in matched_indicators),
            suspicious=bool(payload.get("suspicious", False)),
            raw_payload=raw_payload if isinstance(raw_payload, dict) else {},
        )


@dataclass(frozen=True, slots=True)
class TrafficHostSummary:
    host: str
    flow_count: int
    suspicious_count: int
    https_flow_count: int

    def to_payload(self) -> dict[str, object]:
        return {
            "host": self.host,
            "flow_count": self.flow_count,
            "suspicious_count": self.suspicious_count,
            "https_flow_count": self.https_flow_count,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "TrafficHostSummary | None":
        if not isinstance(payload, dict):
            return None
        host = payload.get("host")
        flow_count = payload.get("flow_count")
        suspicious_count = payload.get("suspicious_count")
        https_flow_count = payload.get("https_flow_count", 0)
        if not isinstance(host, str) or not isinstance(flow_count, int) or not isinstance(suspicious_count, int):
            return None
        if not isinstance(https_flow_count, int):
            https_flow_count = 0
        return cls(
            host=host,
            flow_count=flow_count,
            suspicious_count=suspicious_count,
            https_flow_count=https_flow_count,
        )


@dataclass(frozen=True, slots=True)
class TrafficCaptureSummary:
    https_flow_count: int
    matched_indicator_count: int
    top_hosts: tuple[TrafficHostSummary, ...]
    suspicious_hosts: tuple[TrafficHostSummary, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "https_flow_count": self.https_flow_count,
            "matched_indicator_count": self.matched_indicator_count,
            "top_hosts": [host.to_payload() for host in self.top_hosts],
            "suspicious_hosts": [host.to_payload() for host in self.suspicious_hosts],
        }

    @classmethod
    def from_payload(
        cls,
        payload: object,
        *,
        fallback_payload: object | None = None,
    ) -> "TrafficCaptureSummary":
        summary_payload = payload if isinstance(payload, dict) else {}
        fallback = fallback_payload if isinstance(fallback_payload, dict) else {}
        https_flow_count = summary_payload.get("https_flow_count", fallback.get("https_flow_count", 0))
        matched_indicator_count = summary_payload.get(
            "matched_indicator_count",
            fallback.get("matched_indicator_count", 0),
        )
        top_hosts_payload = summary_payload.get("top_hosts", fallback.get("top_hosts", []))
        suspicious_hosts_payload = summary_payload.get("suspicious_hosts", fallback.get("suspicious_hosts", []))
        return cls(
            https_flow_count=https_flow_count if isinstance(https_flow_count, int) else 0,
            matched_indicator_count=matched_indicator_count if isinstance(matched_indicator_count, int) else 0,
            top_hosts=tuple(
                host
                for host in (TrafficHostSummary.from_payload(item) for item in top_hosts_payload or [])
                if host is not None
            ),
            suspicious_hosts=tuple(
                host
                for host in (TrafficHostSummary.from_payload(item) for item in suspicious_hosts_payload or [])
                if host is not None
            ),
        )


@dataclass(frozen=True, slots=True)
class TrafficCapture:
    source_path: Path
    provenance: TrafficCaptureProvenance
    flow_count: int
    suspicious_count: int
    summary: TrafficCaptureSummary
    flows: tuple[TrafficFlow, ...]

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

    def to_payload(self) -> dict[str, object]:
        summary_payload = self.summary.to_payload()
        return {
            "flow_schema": "traffic-flow.v1",
            "source_path": str(self.source_path),
            "provenance": self.provenance.to_payload(),
            "flow_count": self.flow_count,
            "suspicious_count": self.suspicious_count,
            "https_flow_count": self.https_flow_count,
            "matched_indicator_count": self.matched_indicator_count,
            "top_hosts": summary_payload["top_hosts"],
            "suspicious_hosts": summary_payload["suspicious_hosts"],
            "summary": summary_payload,
            "flows": [flow.to_payload() for flow in self.flows],
        }

    @classmethod
    def from_payload(
        cls,
        payload: object,
        *,
        provenance_factory: Callable[[Path], TrafficCaptureProvenance] | None = None,
    ) -> "TrafficCapture | None":
        if not isinstance(payload, dict):
            return None
        source_path_raw = payload.get("source_path")
        flow_count = payload.get("flow_count")
        suspicious_count = payload.get("suspicious_count")
        if not isinstance(source_path_raw, str) or not isinstance(flow_count, int) or not isinstance(suspicious_count, int):
            return None
        source_path = Path(source_path_raw)
        provenance = TrafficCaptureProvenance.from_payload(payload.get("provenance"))
        if provenance is None:
            if provenance_factory is None:
                return None
            provenance = provenance_factory(source_path)
        summary = TrafficCaptureSummary.from_payload(payload.get("summary"), fallback_payload=payload)
        capture_id = traffic_capture_id_for_path(source_path)
        flows_payload = payload.get("flows", [])
        flows = tuple(
            flow
            for flow in (TrafficFlow.from_payload(capture_id, item) for item in flows_payload or [])
            if flow is not None
        )
        return cls(
            source_path=source_path,
            provenance=provenance,
            flow_count=flow_count,
            suspicious_count=suspicious_count,
            summary=summary,
            flows=flows,
        )


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

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "session_id": self.session_id,
            "output_path": str(self.output_path) if self.output_path else None,
            "preview_path": str(self.preview_path) if self.preview_path else None,
            "message": self.message,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "TrafficLiveCaptureState":
        if not isinstance(payload, dict):
            return cls(status="idle")
        return cls(
            status=str(payload.get("status", "idle") or "idle"),
            session_id=str(payload["session_id"]) if isinstance(payload.get("session_id"), str) else None,
            output_path=_path_from_payload(payload.get("output_path")),
            preview_path=_path_from_payload(payload.get("preview_path")),
            message=str(payload["message"]) if isinstance(payload.get("message"), str) else None,
        )

    @classmethod
    def from_legacy_payload(cls, payload: dict[str, object]) -> "TrafficLiveCaptureState":
        return cls.from_payload(
            {
                "status": payload.get("live_traffic_capture_status", "idle"),
                "session_id": payload.get("live_traffic_capture_session_id"),
                "output_path": payload.get("live_traffic_capture_output_path"),
                "preview_path": payload.get("live_traffic_capture_preview_path"),
                "message": payload.get("live_traffic_capture_message"),
            }
        )


def _headers_from_payload(payload: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(payload, list):
        return ()
    headers: list[tuple[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if name is None or value is None:
            continue
        headers.append((str(name), str(value)))
    return tuple(headers)


def _path_from_payload(value: object | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    if not isinstance(value, (str, bytes)):
        return None
    text = value.decode() if isinstance(value, bytes) else value
    text = text.strip()
    if not text:
        return None
    return Path(text)


def traffic_capture_id_for_path(source_path: Path) -> str:
    normalized = str(source_path.expanduser().resolve())
    digest = hashlib.sha1(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"capture-{digest}"
