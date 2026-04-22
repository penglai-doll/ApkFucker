from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Sequence

from apk_hacker.domain.models.traffic import TrafficFlowSummary


class TrafficFlowStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path.expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def replace_capture(self, capture_id: str, flows: Sequence[TrafficFlowSummary]) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM traffic_flows WHERE capture_id = ?", (capture_id,))
            conn.executemany(
                """
                INSERT INTO traffic_flows (
                    capture_id,
                    flow_id,
                    method,
                    url,
                    status_code,
                    mime_type,
                    request_preview,
                    response_preview,
                    matched_indicators_json,
                    suspicious
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        capture_id,
                        flow.flow_id,
                        flow.method,
                        flow.url,
                        flow.status_code,
                        flow.mime_type,
                        flow.request_preview,
                        flow.response_preview,
                        json.dumps(list(flow.matched_indicators), ensure_ascii=False),
                        int(flow.suspicious),
                    )
                    for flow in flows
                ],
            )
            conn.commit()

    def list_for_capture(self, capture_id: str) -> list[TrafficFlowSummary]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT flow_id, method, url, status_code, mime_type,
                       request_preview, response_preview, matched_indicators_json, suspicious
                FROM traffic_flows
                WHERE capture_id = ?
                ORDER BY rowid ASC
                """,
                (capture_id,),
            ).fetchall()
        return [
            TrafficFlowSummary(
                flow_id=str(flow_id),
                method=str(method),
                url=str(url),
                status_code=status_code if isinstance(status_code, int) else None,
                mime_type=str(mime_type) if mime_type is not None else None,
                request_preview=str(request_preview),
                response_preview=str(response_preview),
                matched_indicators=tuple(
                    str(value)
                    for value in json.loads(matched_indicators_json or "[]")
                    if isinstance(value, str)
                ),
                suspicious=bool(suspicious),
            )
            for flow_id, method, url, status_code, mime_type, request_preview, response_preview, matched_indicators_json, suspicious in rows
        ]

    def _initialize(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traffic_flows (
                    capture_id TEXT NOT NULL,
                    flow_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status_code INTEGER,
                    mime_type TEXT,
                    request_preview TEXT NOT NULL,
                    response_preview TEXT NOT NULL,
                    matched_indicators_json TEXT NOT NULL,
                    suspicious INTEGER NOT NULL,
                    PRIMARY KEY (capture_id, flow_id)
                )
                """
            )
            conn.commit()
