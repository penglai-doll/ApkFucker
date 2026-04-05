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
    assert capture.flows[0].url == "https://demo-c2.example/api/upload"
    assert capture.flows[0].suspicious is True
    assert "demo-c2.example" in capture.flows[0].matched_indicators
    assert capture.flows[1].suspicious is False
