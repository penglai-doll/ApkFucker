from pathlib import Path

from apk_hacker.domain.models.traffic import TrafficCapture
from apk_hacker.domain.models.traffic import TrafficCaptureProvenance
from apk_hacker.domain.models.traffic import TrafficCaptureSummary
from apk_hacker.domain.models.traffic import TrafficFlow
from apk_hacker.domain.models.traffic import TrafficHostSummary


def _flow() -> TrafficFlow:
    return TrafficFlow(
        capture_id="capture-1",
        flow_id="flow-1",
        timestamp="2026-04-26T00:00:00Z",
        method="post",
        url="https://demo-c2.example/api/upload",
        status_code=202,
        mime_type="application/json",
        request_headers=(("content-type", "application/json"),),
        response_headers=(("x-request-id", "abc"),),
        request_preview='{"device_id":"demo"}',
        response_preview='{"ok":true}',
        request_body_size=20,
        response_body_size=11,
        matched_indicators=("demo-c2.example",),
        suspicious=True,
        raw_payload={"source": "har"},
    )


def test_traffic_capture_payload_round_trips_canonical_shape() -> None:
    source_path = Path("D:/captures/sample.har")
    capture = TrafficCapture(
        source_path=source_path,
        provenance=TrafficCaptureProvenance(kind="manual_har", label="Manual HAR"),
        flow_count=1,
        suspicious_count=1,
        summary=TrafficCaptureSummary(
            https_flow_count=1,
            matched_indicator_count=1,
            top_hosts=(TrafficHostSummary("demo-c2.example", 1, 1, 1),),
            suspicious_hosts=(TrafficHostSummary("demo-c2.example", 1, 1, 1),),
        ),
        flows=(_flow(),),
    )

    payload = capture.to_payload()
    reloaded = TrafficCapture.from_payload(payload)

    assert payload["flow_schema"] == "traffic-flow.v1"
    assert payload["source_path"] == str(source_path)
    assert payload["provenance"] == {"kind": "manual_har", "label": "Manual HAR"}
    assert payload["summary"] == {
        "https_flow_count": 1,
        "matched_indicator_count": 1,
        "top_hosts": [
            {
                "host": "demo-c2.example",
                "flow_count": 1,
                "suspicious_count": 1,
                "https_flow_count": 1,
            }
        ],
        "suspicious_hosts": [
            {
                "host": "demo-c2.example",
                "flow_count": 1,
                "suspicious_count": 1,
                "https_flow_count": 1,
            }
        ],
    }
    assert payload["flows"][0]["method"] == "POST"
    assert payload["flows"][0]["request_headers"] == [
        {"name": "content-type", "value": "application/json"}
    ]
    assert reloaded == capture


def test_traffic_capture_from_payload_accepts_legacy_top_level_summary_shape() -> None:
    payload = {
        "source_path": "D:/captures/legacy.har",
        "flow_count": 1,
        "suspicious_count": 0,
        "https_flow_count": 1,
        "matched_indicator_count": 0,
        "top_hosts": [
            {
                "host": "cdn.example.org",
                "flow_count": 1,
                "suspicious_count": 0,
                "https_flow_count": 1,
            }
        ],
        "suspicious_hosts": [],
        "flows": [],
    }

    capture = TrafficCapture.from_payload(
        payload,
        provenance_factory=lambda _source_path: TrafficCaptureProvenance(
            kind="manual_har",
            label="Manual HAR",
        ),
    )

    assert capture is not None
    assert capture.provenance.kind == "manual_har"
    assert capture.https_flow_count == 1
    assert capture.matched_indicator_count == 0
    assert capture.top_hosts[0].host == "cdn.example.org"
