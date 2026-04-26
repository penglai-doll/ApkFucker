from __future__ import annotations

from collections import deque
from collections import defaultdict
import json
from pathlib import Path
from urllib.parse import urlparse

from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.domain.models.traffic import TrafficCaptureSummary
from apk_hacker.domain.models.traffic import TrafficCaptureProvenance
from apk_hacker.domain.models.traffic import TrafficFlow
from apk_hacker.domain.models.traffic import TrafficHostSummary
from apk_hacker.domain.models.traffic import traffic_capture_id_for_path

MANUAL_HAR_PROVENANCE_KIND = "manual_har"
LIVE_CAPTURE_PROVENANCE_KIND = "live_capture"

_TRAFFIC_CAPTURE_PROVENANCE_LABELS = {
    MANUAL_HAR_PROVENANCE_KIND: "手工 HAR 导入",
    LIVE_CAPTURE_PROVENANCE_KIND: "实时抓包自动导入",
}


def _preview(text: object | None, limit: int = 120) -> str:
    if text is None:
        return ""
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _content_text(section: object) -> str:
    if not isinstance(section, dict):
        return ""
    text = section.get("text")
    return str(text) if text is not None else ""


def _headers(section: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(section, list):
        return ()
    headers: list[tuple[str, str]] = []
    for item in section:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if name is None or value is None:
            continue
        headers.append((str(name), str(value)))
    return tuple(headers)


def _body_size(section: object) -> int | None:
    if not isinstance(section, dict):
        return None
    value = section.get("bodySize")
    if isinstance(value, int) and value >= 0:
        return value
    content = section.get("content")
    if isinstance(content, dict):
        size = content.get("size")
        if isinstance(size, int) and size >= 0:
            return size
    return None


def _indicators(static_inputs: StaticInputs) -> tuple[str, ...]:
    values: list[str] = []
    for endpoint in static_inputs.callback_endpoints:
        stripped = endpoint.strip()
        if not stripped:
            continue
        values.append(stripped)
        parsed = urlparse(stripped)
        if parsed.netloc:
            values.append(parsed.netloc)
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def infer_traffic_capture_provenance_kind(source_path: Path) -> str:
    normalized = source_path.expanduser().resolve().as_posix()
    if "/evidence/traffic/live/" in normalized:
        return LIVE_CAPTURE_PROVENANCE_KIND
    return MANUAL_HAR_PROVENANCE_KIND


def build_traffic_capture_provenance(kind: str | None, source_path: Path) -> TrafficCaptureProvenance:
    normalized_kind = kind or infer_traffic_capture_provenance_kind(source_path)
    label = _TRAFFIC_CAPTURE_PROVENANCE_LABELS.get(normalized_kind)
    if label is None:
        raise ValueError(f"Unsupported traffic capture provenance kind: {normalized_kind}")
    return TrafficCaptureProvenance(kind=normalized_kind, label=label)


class TrafficCaptureService:
    def load_har(
        self,
        har_path: Path,
        static_inputs: StaticInputs,
        *,
        provenance_kind: str | None = None,
    ) -> TrafficCapture:
        path = har_path.expanduser().resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("log", {}).get("entries", [])
        if not isinstance(entries, list):
            raise ValueError(f"HAR file is missing log.entries: {path}")

        indicators = _indicators(static_inputs)
        capture_id = traffic_capture_id_for_path(path)
        flows: list[TrafficFlow] = []
        host_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "flow_count": 0,
                "suspicious_count": 0,
                "https_flow_count": 0,
            }
        )
        https_flow_count = 0
        matched_indicator_count = 0
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            request = entry.get("request", {})
            response = entry.get("response", {})
            if not isinstance(request, dict) or not isinstance(response, dict):
                continue
            url = str(request.get("url", "")).strip()
            method = str(request.get("method", "GET")).upper()
            status_code = response.get("status")
            if not isinstance(status_code, int):
                status_code = None
            request_text = _content_text(request.get("postData"))
            response_content = response.get("content", {})
            response_text = _content_text(response_content)
            mime_type = None
            if isinstance(response_content, dict):
                raw_mime = response_content.get("mimeType")
                mime_type = str(raw_mime) if raw_mime else None

            matched = tuple(indicator for indicator in indicators if indicator in url)
            parsed = urlparse(url)
            host = (parsed.hostname or parsed.netloc or "").strip() or "(unknown)"
            scheme = parsed.scheme.lower()
            is_https = scheme == "https"
            if is_https:
                https_flow_count += 1
            matched_indicator_count += len(matched)
            host_stats[host]["flow_count"] += 1
            if is_https:
                host_stats[host]["https_flow_count"] += 1
            if matched:
                host_stats[host]["suspicious_count"] += 1
            flows.append(
                TrafficFlow(
                    capture_id=capture_id,
                    flow_id=f"flow-{index}",
                    timestamp=str(entry["startedDateTime"]) if isinstance(entry.get("startedDateTime"), str) else None,
                    method=method,
                    url=url,
                    scheme=scheme,
                    host=host,
                    path=parsed.path or "/",
                    status_code=status_code,
                    mime_type=mime_type,
                    request_headers=_headers(request.get("headers")),
                    response_headers=_headers(response.get("headers")),
                    request_preview=_preview(request_text),
                    response_preview=_preview(response_text),
                    request_body_size=_body_size(request),
                    response_body_size=_body_size(response),
                    matched_indicators=matched,
                    suspicious=bool(matched),
                    raw_payload={
                        "startedDateTime": entry.get("startedDateTime"),
                        "time": entry.get("time"),
                    },
                )
            )

        flows.sort(key=lambda item: (not item.suspicious, item.url))
        suspicious_count = sum(1 for flow in flows if flow.suspicious)
        host_summaries = tuple(
            TrafficHostSummary(
                host=host,
                flow_count=stats["flow_count"],
                suspicious_count=stats["suspicious_count"],
                https_flow_count=stats["https_flow_count"],
            )
            for host, stats in sorted(
                host_stats.items(),
                key=lambda item: (
                    -item[1]["flow_count"],
                    -item[1]["suspicious_count"],
                    -item[1]["https_flow_count"],
                    item[0],
                ),
            )
        )
        top_hosts = host_summaries[:5]
        suspicious_hosts = tuple(summary for summary in host_summaries if summary.suspicious_count > 0)[:5]
        return TrafficCapture(
            source_path=path,
            provenance=build_traffic_capture_provenance(provenance_kind, path),
            flow_count=len(flows),
            suspicious_count=suspicious_count,
            summary=TrafficCaptureSummary(
                https_flow_count=https_flow_count,
                matched_indicator_count=matched_indicator_count,
                top_hosts=top_hosts,
                suspicious_hosts=suspicious_hosts,
            ),
            flows=tuple(flows),
        )

    def load_live_preview(self, preview_path: Path, *, limit: int = 8) -> tuple[tuple[TrafficFlow, ...], bool]:
        path = preview_path.expanduser().resolve()
        if not path.exists():
            return (), False

        bounded_limit = max(1, min(limit, 20))
        capture_id = traffic_capture_id_for_path(path)
        recent_items: deque[TrafficFlow] = deque(maxlen=bounded_limit)
        total_valid = 0

        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                normalized = line.strip()
                if not normalized:
                    continue
                try:
                    payload = json.loads(normalized)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                url = str(payload.get("url", "")).strip()
                method = str(payload.get("method", "GET")).upper()
                if not url:
                    continue
                matched_indicators = payload.get("matched_indicators", [])
                if not isinstance(matched_indicators, list):
                    matched_indicators = []
                status_code = payload.get("status_code")
                preview_item = TrafficFlow(
                    capture_id=capture_id,
                    flow_id=str(payload.get("flow_id") or f"preview-{index}"),
                    timestamp=str(payload["timestamp"]) if isinstance(payload.get("timestamp"), str) else None,
                    method=method,
                    url=url,
                    status_code=status_code if isinstance(status_code, int) else None,
                    mime_type=str(payload["mime_type"]) if isinstance(payload.get("mime_type"), str) else None,
                    request_preview=str(payload.get("request_preview", "")),
                    response_preview=str(payload.get("response_preview", "")),
                    request_body_size=(
                        payload.get("request_body_size") if isinstance(payload.get("request_body_size"), int) else None
                    ),
                    response_body_size=(
                        payload.get("response_body_size") if isinstance(payload.get("response_body_size"), int) else None
                    ),
                    matched_indicators=tuple(str(value) for value in matched_indicators),
                    suspicious=bool(payload.get("suspicious", False)),
                    raw_payload={
                        "preview_path": str(path),
                    },
                )
                total_valid += 1
                recent_items.append(preview_item)

        return tuple(recent_items), total_valid > len(recent_items)
