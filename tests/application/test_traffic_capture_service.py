from pathlib import Path

from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.static_inputs import StaticInputs


def _static_inputs() -> StaticInputs:
    return StaticInputs(
        sample_path=Path("/samples/demo.apk"),
        package_name="com.demo.shell",
        technical_tags=("network-callback",),
        dangerous_permissions=("android.permission.READ_SMS",),
        callback_endpoints=("https://demo-c2.example/api/upload", "demo-c2.example", "1.2.3.4"),
        callback_clues=("request body includes device_id and sms_body",),
        crypto_signals=(),
        packer_hints=(),
        limitations=(),
        artifact_paths=ArtifactPaths(),
    )


def test_traffic_capture_service_flags_callback_related_flows() -> None:
    capture = TrafficCaptureService().load_har(
        Path("tests/fixtures/traffic/sample.har"),
        _static_inputs(),
    )

    assert capture.flow_count == 2
    assert capture.suspicious_count == 1
    assert capture.https_flow_count == 2
    assert capture.matched_indicator_count == 2
    assert capture.flows[0].url == "https://demo-c2.example/api/upload"
    assert capture.flows[0].suspicious is True
    assert "demo-c2.example" in capture.flows[0].matched_indicators
    assert capture.flows[1].suspicious is False
    assert [host.host for host in capture.top_hosts] == ["demo-c2.example", "cdn.example.org"]
    assert capture.top_hosts[0].flow_count == 1
    assert capture.top_hosts[0].suspicious_count == 1
    assert capture.top_hosts[0].https_flow_count == 1
    assert [host.host for host in capture.suspicious_hosts] == ["demo-c2.example"]


def test_traffic_capture_service_loads_recent_live_preview_entries(tmp_path: Path) -> None:
    preview_path = tmp_path / "live-preview.ndjson"
    preview_path.write_text(
        "\n".join(
            [
                '{"flow_id":"preview-1","timestamp":"2026-04-19T10:00:00Z","method":"GET","url":"https://cdn.example.org/a.js","status_code":200,"matched_indicators":[],"suspicious":false}',
                '{"flow_id":"preview-2","timestamp":"2026-04-19T10:00:02Z","method":"POST","url":"https://demo-c2.example/api/upload","status_code":202,"matched_indicators":["demo-c2.example"],"suspicious":true}',
                '{"flow_id":"preview-3","timestamp":"2026-04-19T10:00:04Z","method":"POST","url":"https://demo-c2.example/api/ping","status_code":200,"matched_indicators":["demo-c2.example"],"suspicious":true}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    items, truncated = TrafficCaptureService().load_live_preview(preview_path, limit=2)

    assert truncated is True
    assert [item["flow_id"] for item in items] == ["preview-2", "preview-3"]
    assert items[-1]["url"] == "https://demo-c2.example/api/ping"
    assert items[-1]["suspicious"] is True
