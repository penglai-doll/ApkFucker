from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apk_hacker.domain.models.hook_event import HookEvent


class HookLogStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path.expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS hook_events (
                    timestamp TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    return_value TEXT,
                    stacktrace TEXT NOT NULL,
                    raw_payload TEXT NOT NULL
                )
                """
            )

    def insert(self, event: HookEvent) -> None:
        with sqlite3.connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO hook_events (
                    timestamp, job_id, event_type, source, class_name, method_name,
                    arguments, return_value, stacktrace, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp,
                    event.job_id,
                    event.event_type,
                    event.source,
                    event.class_name,
                    event.method_name,
                    json.dumps(list(event.arguments)),
                    event.return_value,
                    event.stacktrace,
                    json.dumps(event.raw_payload),
                ),
            )

    def list_for_job(self, job_id: str) -> list[HookEvent]:
        with sqlite3.connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT timestamp, job_id, event_type, source, class_name, method_name,
                       arguments, return_value, stacktrace, raw_payload
                FROM hook_events
                WHERE job_id = ?
                ORDER BY timestamp ASC
                """,
                (job_id,),
            ).fetchall()

        return [
            HookEvent(
                timestamp=row[0],
                job_id=row[1],
                event_type=row[2],
                source=row[3],
                class_name=row[4],
                method_name=row[5],
                arguments=json.loads(row[6]),
                return_value=row[7],
                stacktrace=row[8],
                raw_payload=json.loads(row[9]),
            )
            for row in rows
        ]
