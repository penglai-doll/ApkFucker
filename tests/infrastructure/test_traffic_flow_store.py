from pathlib import Path
import sqlite3

from apk_hacker.domain.models.traffic import TrafficFlowSummary
from apk_hacker.infrastructure.persistence.traffic_flow_store import TrafficFlowStore


def _flows() -> tuple[TrafficFlowSummary, ...]:
    return (
        TrafficFlowSummary(
            flow_id="flow-1",
            method="POST",
            url="https://demo-c2.example/api/upload",
            status_code=202,
            mime_type="application/json",
            request_preview='{"device_id":"demo"}',
            response_preview='{"ok":true}',
            matched_indicators=("demo-c2.example",),
            suspicious=True,
        ),
        TrafficFlowSummary(
            flow_id="flow-2",
            method="GET",
            url="https://cdn.example.org/app.js",
            status_code=200,
            mime_type="application/javascript",
            request_preview="",
            response_preview="console.log('demo')",
            matched_indicators=(),
            suspicious=False,
        ),
    )


def test_traffic_flow_store_persists_imported_har_flows(tmp_path: Path) -> None:
    store = TrafficFlowStore(tmp_path / "flows.sqlite3")

    store.replace_capture("capture-001", _flows())

    loaded = store.list_for_capture("capture-001")
    assert len(loaded) == 2
    assert loaded[0].summary == _flows()[0]
    assert loaded[0].schema_version == "traffic-flow.v1"
    assert loaded[0].capture_id == "capture-001"
    assert loaded[0].scheme == "https"
    assert loaded[0].host == "demo-c2.example"
    assert loaded[0].path == "/api/upload"
    assert loaded[1].matched_indicators == ()


def test_traffic_flow_store_replace_capture_overwrites_previous_rows(tmp_path: Path) -> None:
    store = TrafficFlowStore(tmp_path / "flows.sqlite3")
    store.replace_capture("capture-001", _flows())

    replacement = (
        TrafficFlowSummary(
            flow_id="flow-9",
            method="DELETE",
            url="https://demo-c2.example/api/device/1",
            status_code=204,
            mime_type=None,
            request_preview="",
            response_preview="",
            matched_indicators=("demo-c2.example",),
            suspicious=True,
        ),
    )
    store.replace_capture("capture-001", replacement)

    loaded = store.list_for_capture("capture-001")
    assert [flow.summary for flow in loaded] == list(replacement)
    assert store.list_for_capture("capture-missing") == []


def test_traffic_flow_store_migrates_legacy_tables_without_indicator_column(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-flows.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE traffic_flows (
                capture_id TEXT NOT NULL,
                flow_id TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                mime_type TEXT,
                request_preview TEXT NOT NULL,
                response_preview TEXT NOT NULL,
                suspicious INTEGER NOT NULL,
                PRIMARY KEY (capture_id, flow_id)
            )
            """
        )
        conn.commit()

    store = TrafficFlowStore(db_path)
    store.replace_capture("capture-legacy", _flows())

    loaded = store.list_for_capture("capture-legacy")
    assert [flow.summary for flow in loaded] == list(_flows())
