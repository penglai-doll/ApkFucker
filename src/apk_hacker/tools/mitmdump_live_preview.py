from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock

from mitmproxy import http

from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_PREVIEW_PATH_ENV


_preview_path_raw = os.getenv(TRAFFIC_CAPTURE_PREVIEW_PATH_ENV, "").strip()
_preview_path = Path(_preview_path_raw).expanduser() if _preview_path_raw else None
_write_lock = Lock()
_sequence = 0


def _write_preview_entry(payload: dict[str, object]) -> None:
    if _preview_path is None:
        return
    _preview_path.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with _preview_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def response(flow: http.HTTPFlow) -> None:
    global _sequence
    if _preview_path is None:
        return

    _sequence += 1
    _write_preview_entry(
        {
            "flow_id": f"preview-{_sequence}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": flow.request.method.upper(),
            "url": flow.request.pretty_url,
            "status_code": flow.response.status_code if flow.response is not None else None,
            "matched_indicators": [],
            "suspicious": False,
        }
    )
