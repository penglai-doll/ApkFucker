from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.traffic import TrafficCapture, TrafficFlowSummary


def _preview(text: object | None, limit: int = 120) -> str:
    if text is None:
        return ""
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _content_text(section: object) -> str:
    if not isinstance(section, dict):
        return ""
    text = section.get("text")
    return str(text) if text is not None else ""


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


class TrafficCaptureService:
    def load_har(self, har_path: Path, static_inputs: StaticInputs) -> TrafficCapture:
        path = har_path.expanduser().resolve()
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("log", {}).get("entries", [])
        if not isinstance(entries, list):
            raise ValueError(f"HAR file is missing log.entries: {path}")

        indicators = _indicators(static_inputs)
        flows: list[TrafficFlowSummary] = []
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
            flows.append(
                TrafficFlowSummary(
                    flow_id=f"flow-{index}",
                    method=method,
                    url=url,
                    status_code=status_code,
                    mime_type=mime_type,
                    request_preview=_preview(request_text),
                    response_preview=_preview(response_text),
                    matched_indicators=matched,
                    suspicious=bool(matched),
                )
            )

        flows.sort(key=lambda item: (not item.suspicious, item.url))
        suspicious_count = sum(1 for flow in flows if flow.suspicious)
        return TrafficCapture(
            source_path=path,
            flow_count=len(flows),
            suspicious_count=suspicious_count,
            flows=tuple(flows),
        )
