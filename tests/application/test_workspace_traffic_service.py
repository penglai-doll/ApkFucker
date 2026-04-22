from pathlib import Path

from apk_hacker.application.services.traffic_capture_service import TrafficCaptureService
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
from apk_hacker.application.services.workspace_traffic_service import WorkspaceTrafficService
from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState
from apk_hacker.infrastructure.persistence.traffic_flow_store import TrafficFlowStore


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


def test_workspace_traffic_service_import_har_updates_runtime_state_and_persists_flows(tmp_path: Path) -> None:
    workspace_root = tmp_path / "case-001"
    state = build_default_runtime_state("case-001", workspace_root)
    service = WorkspaceTrafficService(
        traffic_capture_service=TrafficCaptureService(),
        traffic_flow_store_factory=TrafficFlowStore,
    )

    updated, capture = service.import_har(
        state,
        Path("tests/fixtures/traffic/sample.har"),
        _static_inputs(),
    )

    assert updated.traffic_capture_summary_path == workspace_root / "evidence" / "traffic" / "traffic-capture.json"
    assert updated.traffic_capture_flow_count == 2
    assert updated.traffic_capture_suspicious_count == 1
    assert capture.flow_count == 2
    assert service.traffic_flow_store_path(workspace_root).is_file()

    reloaded = service.get_capture(updated)
    assert reloaded is not None
    assert len(reloaded.flows) == 2
    assert reloaded.flows[0].url == "https://demo-c2.example/api/upload"
    store = TrafficFlowStore(service.traffic_flow_store_path(workspace_root))
    assert len(store.list_for_capture(service.capture_id_for_path(capture.source_path))) == 2


def test_workspace_traffic_service_updates_live_capture_state_without_touching_capture_summary(tmp_path: Path) -> None:
    service = WorkspaceTrafficService()
    state = build_default_runtime_state("case-live", tmp_path / "case-live")

    updated = service.save_live_capture_state(
        state,
        TrafficLiveCaptureState(
            status="running",
            session_id="live-001",
            output_path=tmp_path / "case-live" / "evidence" / "traffic" / "live" / "live-001.har",
            message="已开始实时抓包。",
        ),
    )

    assert updated.live_traffic_capture.status == "running"
    assert updated.traffic_capture_summary_path is None
    assert service.build_live_capture_output_path(updated.workspace_root, "live-002") == (
        tmp_path / "case-live" / "evidence" / "traffic" / "live" / "live-002.har"
    )


def test_workspace_traffic_service_capture_ids_do_not_collide_for_same_stem_paths(tmp_path: Path) -> None:
    service = WorkspaceTrafficService()
    first = tmp_path / "a" / "sample.har"
    second = tmp_path / "b" / "sample.har"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")

    first_id = service.capture_id_for_path(first)
    second_id = service.capture_id_for_path(second)

    assert first_id != second_id
