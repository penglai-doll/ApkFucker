from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Sequence

from apk_hacker.domain.models.traffic import TrafficFlow
from apk_hacker.domain.models.traffic import TrafficFlowSummary


class TrafficFlowStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path.expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def replace_capture(self, capture_id: str, flows: Sequence[TrafficFlow | TrafficFlowSummary]) -> None:
        normalized_flows = [
            flow if isinstance(flow, TrafficFlow) else TrafficFlow.from_summary(capture_id, flow)
            for flow in flows
        ]
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM traffic_flows WHERE capture_id = ?", (capture_id,))
            conn.executemany(
                """
                INSERT INTO traffic_flows (
                    schema_version,
                    capture_id,
                    flow_id,
                    timestamp,
                    method,
                    url,
                    scheme,
                    host,
                    path,
                    status_code,
                    mime_type,
                    request_headers_json,
                    response_headers_json,
                    request_preview,
                    response_preview,
                    request_body_size,
                    response_body_size,
                    matched_indicators_json,
                    suspicious,
                    raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        flow.schema_version,
                        capture_id,
                        flow.flow_id,
                        flow.timestamp,
                        flow.method,
                        flow.url,
                        flow.scheme,
                        flow.host,
                        flow.path,
                        flow.status_code,
                        flow.mime_type,
                        json.dumps(
                            [{"name": name, "value": value} for name, value in flow.request_headers],
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            [{"name": name, "value": value} for name, value in flow.response_headers],
                            ensure_ascii=False,
                        ),
                        flow.request_preview,
                        flow.response_preview,
                        flow.request_body_size,
                        flow.response_body_size,
                        json.dumps(list(flow.matched_indicators), ensure_ascii=False),
                        int(flow.suspicious),
                        json.dumps(flow.raw_payload or {}, ensure_ascii=False),
                    )
                    for flow in normalized_flows
                ],
            )
            conn.commit()

    def list_for_capture(self, capture_id: str) -> list[TrafficFlow]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT schema_version, capture_id, flow_id, timestamp, method, url,
                       scheme, host, path, status_code, mime_type,
                       request_headers_json, response_headers_json,
                       request_preview, response_preview, request_body_size, response_body_size,
                       matched_indicators_json, suspicious, raw_payload_json
                FROM traffic_flows
                WHERE capture_id = ?
                ORDER BY rowid ASC
                """,
                (capture_id,),
            ).fetchall()
        return [
            TrafficFlow(
                schema_version=str(schema_version or "traffic-flow.v1"),
                capture_id=str(row_capture_id),
                flow_id=str(flow_id),
                timestamp=str(timestamp) if timestamp is not None else None,
                method=str(method),
                url=str(url),
                scheme=str(scheme or ""),
                host=str(host or ""),
                path=str(path or ""),
                status_code=status_code if isinstance(status_code, int) else None,
                mime_type=str(mime_type) if mime_type is not None else None,
                request_headers=_load_headers(request_headers_json),
                response_headers=_load_headers(response_headers_json),
                request_preview=str(request_preview),
                response_preview=str(response_preview),
                request_body_size=request_body_size if isinstance(request_body_size, int) else None,
                response_body_size=response_body_size if isinstance(response_body_size, int) else None,
                matched_indicators=tuple(
                    str(value)
                    for value in json.loads(matched_indicators_json or "[]")
                    if isinstance(value, str)
                ),
                suspicious=bool(suspicious),
                raw_payload=_load_raw_payload(raw_payload_json),
            )
            for (
                schema_version,
                row_capture_id,
                flow_id,
                timestamp,
                method,
                url,
                scheme,
                host,
                path,
                status_code,
                mime_type,
                request_headers_json,
                response_headers_json,
                request_preview,
                response_preview,
                request_body_size,
                response_body_size,
                matched_indicators_json,
                suspicious,
                raw_payload_json,
            ) in rows
        ]

    def _initialize(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traffic_flows (
                    schema_version TEXT NOT NULL DEFAULT 'traffic-flow.v1',
                    capture_id TEXT NOT NULL,
                    flow_id TEXT NOT NULL,
                    timestamp TEXT,
                    method TEXT NOT NULL,
                    url TEXT NOT NULL,
                    scheme TEXT NOT NULL DEFAULT '',
                    host TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL DEFAULT '',
                    status_code INTEGER,
                    mime_type TEXT,
                    request_headers_json TEXT NOT NULL DEFAULT '[]',
                    response_headers_json TEXT NOT NULL DEFAULT '[]',
                    request_preview TEXT NOT NULL,
                    response_preview TEXT NOT NULL,
                    request_body_size INTEGER,
                    response_body_size INTEGER,
                    matched_indicators_json TEXT NOT NULL,
                    suspicious INTEGER NOT NULL,
                    raw_payload_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (capture_id, flow_id)
                )
                """
            )
            self._ensure_columns(conn)
            conn.commit()

    @staticmethod
    def _ensure_columns(conn: sqlite3.Connection) -> None:
        existing = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(traffic_flows)").fetchall()
        }
        columns: dict[str, str] = {
            "schema_version": "TEXT NOT NULL DEFAULT 'traffic-flow.v1'",
            "timestamp": "TEXT",
            "scheme": "TEXT NOT NULL DEFAULT ''",
            "host": "TEXT NOT NULL DEFAULT ''",
            "path": "TEXT NOT NULL DEFAULT ''",
            "request_headers_json": "TEXT NOT NULL DEFAULT '[]'",
            "response_headers_json": "TEXT NOT NULL DEFAULT '[]'",
            "request_preview": "TEXT NOT NULL DEFAULT ''",
            "response_preview": "TEXT NOT NULL DEFAULT ''",
            "request_body_size": "INTEGER",
            "response_body_size": "INTEGER",
            "matched_indicators_json": "TEXT NOT NULL DEFAULT '[]'",
            "suspicious": "INTEGER NOT NULL DEFAULT 0",
            "raw_payload_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, definition in columns.items():
            if name in existing:
                continue
            conn.execute(f"ALTER TABLE traffic_flows ADD COLUMN {name} {definition}")


def _load_headers(payload: object) -> tuple[tuple[str, str], ...]:
    try:
        rows = json.loads(str(payload or "[]"))
    except json.JSONDecodeError:
        return ()
    if not isinstance(rows, list):
        return ()
    headers: list[tuple[str, str]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if name is None or value is None:
            continue
        headers.append((str(name), str(value)))
    return tuple(headers)


def _load_raw_payload(payload: object) -> dict[str, object]:
    try:
        row = json.loads(str(payload or "{}"))
    except json.JSONDecodeError:
        return {}
    return row if isinstance(row, dict) else {}
