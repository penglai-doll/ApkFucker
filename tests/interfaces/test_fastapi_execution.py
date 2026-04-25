from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

from fastapi.testclient import TestClient

from apk_hacker.static_engine.analyzer import StaticArtifacts
from apk_hacker.application.services.device_inventory_service import DeviceInventoryService
from apk_hacker.application.services.execution_presets import ExecutionPresetStatus
from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.domain.models.environment import ConnectedDevice
from apk_hacker.domain.models.environment import DeviceInventorySnapshot
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistry
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.app import build_app
from apk_hacker.infrastructure.execution.backend import ExecutionBackend
from apk_hacker.infrastructure.execution.backend import ExecutionCancelled
from apk_hacker.domain.models.hook_event import HookEvent


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        del target_path, output_dir, mode
        return self.artifacts


class _StaticDeviceInventoryService:
    def inspect(self, package_name: str | None = None) -> DeviceInventorySnapshot:
        del package_name
        return DeviceInventorySnapshot(
            devices=(
                ConnectedDevice(
                    serial="emulator-5554",
                    state="device",
                    model="Pixel",
                    rooted=True,
                    frida_visible=True,
                    package_installed=True,
                    is_emulator=True,
                ),
            )
        )


def _build_app(tmp_path: Path, *, device_inventory_service: DeviceInventoryService | None = None) -> TestClient:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=tmp_path / "artifacts",
            report_dir=tmp_path / "artifacts" / "报告" / "sample",
            cache_dir=tmp_path / "artifacts" / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=tmp_path / "artifacts" / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    return TestClient(
        build_app(
            default_workspace_root=tmp_path / "workspaces",
            static_analyzer=fake_analyzer,
            device_inventory_service=device_inventory_service or _StaticDeviceInventoryService(),
        )
    )


def test_websocket_pings_pong() -> None:
    client = TestClient(build_app())

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "ping"})
        payload = websocket.receive_json()

    assert payload["type"] == "pong"


def test_websocket_ignores_non_object_messages() -> None:
    client = TestClient(build_app())

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json(["ping"])
        websocket.send_json({"type": "ping"})
        payload = websocket.receive_json()

    assert payload["type"] == "pong"


def test_websocket_ignores_non_json_text_messages() -> None:
    client = TestClient(build_app())

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("ping")
        websocket.send_json({"type": "ping"})
        payload = websocket.receive_json()

    assert payload["type"] == "pong"


def test_start_execution_returns_accepted_and_broadcasts_started_then_completed_events(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-123"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-123",
                "title": "广播测试",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-123/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-123/hook-plan/methods", json=method).status_code == 200
    runtime_state_path = case_root / "workspace-runtime.json"
    seeded_runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    seeded_runtime_state["last_execution_error_code"] = "stale.execution_error"
    seeded_runtime_state["last_execution_error_message"] = "should be cleared"
    runtime_state_path.write_text(json.dumps(seeded_runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-123/executions",
            json={"execution_mode": "fake_backend"},
        )
        payload = response.json()
        started_event = websocket.receive_json()
        executing_event = websocket.receive_json()
        persisting_event = websocket.receive_json()
        completed_event = websocket.receive_json()

    assert response.status_code == 202
    assert payload["case_id"] == "case-123"
    assert payload["status"] == "started"
    assert payload["stage"] == "queued"
    assert payload["execution_mode"] == "fake_backend"
    assert payload["executed_backend_key"] == "fake_backend"
    assert payload["event_count"] is None
    assert payload["db_path"] is None
    assert payload["bundle_path"] is None
    assert payload["executed_backend_label"] == "Fake Backend"
    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    assert runtime_state["last_execution_run_id"] == completed_event["run_id"]
    assert runtime_state["last_execution_result_path"] == completed_event["bundle_path"]
    assert runtime_state["last_execution_db_path"] == completed_event["db_path"]
    assert runtime_state["last_execution_error_code"] is None
    assert runtime_state["last_execution_error_message"] is None
    assert started_event == {
        "type": "execution.started",
        "case_id": "case-123",
        "status": "started",
        "stage": "queued",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
    }
    assert executing_event == {
        "type": "execution.progress",
        "case_id": "case-123",
        "status": "started",
        "stage": "executing",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
    }
    assert persisting_event == {
        "type": "execution.progress",
        "case_id": "case-123",
        "status": "started",
        "stage": "persisting",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
    }
    assert completed_event["type"] == "execution.completed"
    assert completed_event["case_id"] == "case-123"
    assert completed_event["status"] == "completed"
    assert completed_event["stage"] == "completed"
    assert completed_event["executed_backend_key"] == "fake_backend"
    assert completed_event["event_count"] > 0
    assert completed_event["db_path"].endswith(".sqlite3")
    assert Path(completed_event["db_path"]).exists()
    assert completed_event["bundle_path"]
    assert Path(completed_event["bundle_path"]).exists()
    assert completed_event["executed_backend_label"] == "Fake Backend"


def test_start_execution_does_not_broadcast_started_when_plan_is_missing(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-empty"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-empty",
                "title": "空计划案件",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-empty/executions",
            json={"execution_mode": "fake_backend"},
        )
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()

    assert response.status_code == 400
    assert response.json()["detail"] == "Add at least one hook plan item first."
    assert pong == {"type": "pong"}


def test_start_execution_broadcasts_failed_event_for_backend_errors(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-real"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-real",
                "title": "真实后端失败",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("APKHACKER_REAL_BACKEND_COMMAND", raising=False)
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability=None: (
            ExecutionPresetStatus(
                key="fake_backend",
                label="Fake Backend",
                available=True,
                detail="ready",
            ),
            ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=True,
                detail="ready (custom)",
            ),
            ExecutionPresetStatus(
                key="real_adb_probe",
                label="ADB Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_bootstrap",
                label="Frida Bootstrap",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_probe",
                label="Frida Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_inject",
                label="Frida Inject",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_session",
                label="Frida Session",
                available=False,
                detail="unavailable",
            ),
        ),
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-real/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-real/hook-plan/methods", json=method).status_code == 200
    runtime_state_path = case_root / "workspace-runtime.json"
    seeded_runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    seeded_runtime_state["last_execution_error_code"] = "stale.execution_error"
    seeded_runtime_state["last_execution_error_message"] = "stale failure"
    runtime_state_path.write_text(json.dumps(seeded_runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-real/executions",
            json={"execution_mode": "real_device"},
        )
        started_event = websocket.receive_json()
        progress_event = websocket.receive_json()
        failed_event = websocket.receive_json()

    assert response.status_code == 202
    assert response.json() == {
        "case_id": "case-real",
        "status": "started",
        "execution_mode": "real_device",
        "executed_backend_key": "real_device",
        "stage": "queued",
        "run_id": None,
        "event_count": None,
        "db_path": None,
        "bundle_path": None,
        "executed_backend_label": "Real Device",
    }
    assert started_event == {
        "type": "execution.started",
        "case_id": "case-real",
        "status": "started",
        "stage": "queued",
        "execution_mode": "real_device",
        "executed_backend_key": "real_device",
        "executed_backend_label": "Real Device",
    }
    assert progress_event == {
        "type": "execution.progress",
        "case_id": "case-real",
        "status": "started",
        "stage": "executing",
        "execution_mode": "real_device",
        "executed_backend_key": "real_device",
        "executed_backend_label": "Real Device",
    }
    assert failed_event["type"] == "execution.failed"
    assert failed_event["case_id"] == "case-real"
    assert failed_event["status"] == "error"
    assert failed_event["stage"] == "failed"
    assert failed_event["execution_mode"] == "real_device"
    assert failed_event["executed_backend_key"] == "real_device"
    assert failed_event["error_code"] == "backend_not_configured"
    assert "APKHACKER_REAL_BACKEND_COMMAND" in failed_event["message"]
    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    assert runtime_state["last_execution_mode"] == "real_device"
    assert runtime_state["last_executed_backend_key"] == "real_device"
    assert runtime_state["last_execution_status"] == "error"
    assert runtime_state["last_execution_stage"] == "failed"
    assert runtime_state["last_execution_error_code"] == "backend_not_configured"
    assert runtime_state["last_execution_error_message"] == failed_event["message"]
    runtime_state = json.loads((case_root / "workspace-runtime.json").read_text(encoding="utf-8"))
    assert runtime_state["last_execution_mode"] == "real_device"
    assert runtime_state["last_executed_backend_key"] == "real_device"
    assert runtime_state["last_execution_status"] == "error"
    assert runtime_state["last_execution_stage"] == "failed"
    assert runtime_state["last_execution_error_code"] == "backend_not_configured"
    assert "APKHACKER_REAL_BACKEND_COMMAND" in runtime_state["last_execution_error_message"]


def test_start_execution_marks_structured_real_backend_fatal_events_as_failed(
    tmp_path: Path, monkeypatch
) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-structured-real"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-structured-real",
                "title": "结构化真实后端失败",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    helper = tmp_path / "structured_real_backend.py"
    helper.write_text(
        """
import json

print(json.dumps({
    "event_type": "frida_session_error",
    "class_name": "frida.session",
    "method_name": "attach",
    "arguments": [],
    "return_value": "attach failed",
    "stacktrace": "",
}))
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APKHACKER_REAL_BACKEND_COMMAND", f"{sys.executable} {helper}")
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability=None: (
            ExecutionPresetStatus(
                key="fake_backend",
                label="Fake Backend",
                available=True,
                detail="ready",
            ),
            ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=True,
                detail="ready (custom)",
            ),
            ExecutionPresetStatus(
                key="real_adb_probe",
                label="ADB Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_bootstrap",
                label="Frida Bootstrap",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_probe",
                label="Frida Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_inject",
                label="Frida Inject",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_session",
                label="Frida Session",
                available=False,
                detail="unavailable",
            ),
        ),
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-structured-real/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post(
        "/api/cases/case-structured-real/hook-plan/methods", json=method
    ).status_code == 200

    runtime_state_path = case_root / "workspace-runtime.json"

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-structured-real/executions",
            json={"execution_mode": "real_device"},
        )
        started_event = websocket.receive_json()
        progress_event = websocket.receive_json()
        failed_event = websocket.receive_json()

    assert response.status_code == 202
    assert response.json()["status"] == "started"
    assert started_event == {
        "type": "execution.started",
        "case_id": "case-structured-real",
        "status": "started",
        "stage": "queued",
        "execution_mode": "real_device",
        "executed_backend_key": "real_device",
        "executed_backend_label": "Real Device",
    }
    assert progress_event == {
        "type": "execution.progress",
        "case_id": "case-structured-real",
        "status": "started",
        "stage": "executing",
        "execution_mode": "real_device",
        "executed_backend_key": "real_device",
        "executed_backend_label": "Real Device",
    }
    assert failed_event["type"] == "execution.failed"
    assert failed_event["case_id"] == "case-structured-real"
    assert failed_event["status"] == "error"
    assert failed_event["stage"] == "failed"
    assert failed_event["execution_mode"] == "real_device"
    assert failed_event["executed_backend_key"] == "real_device"
    assert failed_event["error_code"] == "frida_session_error"
    assert "attach failed" in failed_event["message"]
    assert "Artifacts saved to" in failed_event["message"]

    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    assert runtime_state["last_execution_status"] == "error"
    assert runtime_state["last_execution_stage"] == "failed"
    assert runtime_state["last_execution_error_code"] == "frida_session_error"
    assert runtime_state["last_execution_error_message"] == failed_event["message"]


def test_start_execution_returns_conflict_when_case_is_already_running(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-running"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-running",
                "title": "并发执行案件",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-running/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-running/hook-plan/methods", json=method).status_code == 200

    from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend

    original_execute = FakeExecutionBackend.execute

    def slow_execute(self, request):  # type: ignore[no-untyped-def]
        time.sleep(0.2)
        return original_execute(self, request)

    monkeypatch.setattr(FakeExecutionBackend, "execute", slow_execute)

    first_response = client.post(
        "/api/cases/case-running/executions",
        json={"execution_mode": "fake_backend"},
    )
    second_response = client.post(
        "/api/cases/case-running/executions",
        json={"execution_mode": "fake_backend"},
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Execution is already running for this case."


def test_cancel_execution_marks_case_as_cancelling_then_cancelled(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-cancel"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-cancel",
                "title": "取消执行案件",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-cancel/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-cancel/hook-plan/methods", json=method).status_code == 200

    from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend

    def cancellable_execute(self, request):  # type: ignore[no-untyped-def]
        deadline = time.time() + 1
        while time.time() < deadline:
            if request.cancellation_event is not None and request.cancellation_event.is_set():
                raise ExecutionCancelled("Execution was cancelled by the user.")
            time.sleep(0.01)
        return ()

    monkeypatch.setattr(FakeExecutionBackend, "execute", cancellable_execute)

    with client.websocket_connect("/ws") as websocket:
        start_response = client.post(
            "/api/cases/case-cancel/executions",
            json={"execution_mode": "fake_backend"},
        )
        started_event = websocket.receive_json()
        progress_event = websocket.receive_json()
        cancel_response = client.post("/api/cases/case-cancel/executions/cancel")
        cancelling_event = websocket.receive_json()
        cancelled_event = websocket.receive_json()

    assert start_response.status_code == 202
    assert start_response.json()["stage"] == "queued"
    assert started_event["type"] == "execution.started"
    assert progress_event == {
        "type": "execution.progress",
        "case_id": "case-cancel",
        "status": "started",
        "stage": "executing",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
    }
    assert cancel_response.status_code == 202
    assert cancel_response.json() == {
        "case_id": "case-cancel",
        "status": "cancelling",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "stage": "cancelling",
    }
    assert cancelling_event == {
        "type": "execution.cancelling",
        "case_id": "case-cancel",
        "status": "cancelling",
        "stage": "cancelling",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
    }
    assert cancelled_event == {
        "type": "execution.cancelled",
        "case_id": "case-cancel",
        "status": "cancelled",
        "stage": "cancelled",
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
        "message": "Execution was cancelled by the user.",
    }
    runtime_state = json.loads((case_root / "workspace-runtime.json").read_text(encoding="utf-8"))
    assert runtime_state["last_execution_status"] == "cancelled"
    assert runtime_state["last_execution_stage"] == "cancelled"
    assert runtime_state["last_executed_backend_key"] == "fake_backend"
    assert runtime_state["last_execution_error_code"] is None
    assert runtime_state["last_execution_error_message"] is None


def test_start_execution_routes_named_real_preset_via_shared_backend_builder(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-preset"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-preset",
                "title": "命名预设案件",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-preset/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-preset/hook-plan/methods", json=method).status_code == 200

    seen_modes: list[str] = []
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability=None: (
            ExecutionPresetStatus(
                key="fake_backend",
                label="Fake Backend",
                available=True,
                detail="ready",
            ),
            ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=True,
                detail="ready (ADB Probe)",
            ),
            ExecutionPresetStatus(
                key="real_adb_probe",
                label="ADB Probe",
                available=True,
                detail="ready",
            ),
            ExecutionPresetStatus(
                key="real_frida_bootstrap",
                label="Frida Bootstrap",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_probe",
                label="Frida Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_inject",
                label="Frida Inject",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_session",
                label="Frida Session",
                available=False,
                detail="unavailable",
            ),
        ),
    )

    class _PresetBackend(ExecutionBackend):
        def execute(self, request):  # type: ignore[no-untyped-def]
            seen_modes.append("called")
            return (
                HookEvent(
                    timestamp="2026-04-17T00:00:00Z",
                    job_id=request.job_id,
                    event_type="probe",
                    source="real",
                    class_name="preset.backend",
                    method_name="run",
                    arguments=("ok",),
                    return_value="done",
                    stacktrace="",
                    raw_payload={},
                ),
            )

    def build_backend(execution_mode: str, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        seen_modes.append(execution_mode)
        if execution_mode == "real_adb_probe":
            return _PresetBackend()
        raise AssertionError(f"Unexpected execution mode: {execution_mode}")

    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_backend",
        build_backend,
    )

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-preset/executions",
            json={"execution_mode": "real_adb_probe"},
        )
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        completed_event = websocket.receive_json()

    assert response.status_code == 202
    assert response.json()["execution_mode"] == "real_adb_probe"
    assert completed_event["type"] == "execution.completed"
    assert completed_event["execution_mode"] == "real_adb_probe"
    assert completed_event["executed_backend_key"] == "real_adb_probe"
    assert completed_event["executed_backend_label"] == "ADB Probe"
    assert seen_modes == ["real_adb_probe", "called"]


def test_get_startup_uses_registry_and_workspace_metadata(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-restore"
    case_root.mkdir(parents=True)
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-restore",
                "title": "恢复案件",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    registry_path = tmp_path / "workspace-registry.json"
    WorkspaceRegistryService(registry_path).save(
        WorkspaceRegistry(
            default_workspace_root=workspace_root,
            last_opened_workspace=case_root,
            known_workspace_roots=(workspace_root,),
        )
    )
    client = TestClient(
        build_app(default_workspace_root=workspace_root, registry_path=registry_path)
    )

    response = client.get("/api/settings/startup")

    assert response.status_code == 200
    assert response.json() == {
        "launch_view": "workspace",
        "last_workspace_root": str(case_root),
        "case_id": "case-restore",
        "title": "恢复案件",
    }


def test_get_startup_falls_back_to_queue_when_registry_has_no_last_workspace(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    registry_path = tmp_path / "workspace-registry.json"
    WorkspaceRegistryService(registry_path).save(
        WorkspaceRegistry(
            default_workspace_root=workspace_root,
            last_opened_workspace=None,
            known_workspace_roots=(workspace_root,),
        )
    )
    client = TestClient(
        build_app(default_workspace_root=workspace_root, registry_path=registry_path)
    )

    response = client.get("/api/settings/startup")

    assert response.status_code == 200
    assert response.json() == {
        "launch_view": "queue",
        "last_workspace_root": None,
        "case_id": None,
        "title": None,
    }


def test_open_path_uses_desktop_launcher_and_returns_opened_status(tmp_path: Path) -> None:
    opened_paths: list[Path] = []
    target_path = tmp_path / "evidence" / "run.sqlite3"
    target_path.parent.mkdir(parents=True)
    target_path.write_text("demo", encoding="utf-8")
    client = TestClient(
        build_app(
            default_workspace_root=tmp_path / "workspaces",
            path_opener=lambda path: opened_paths.append(path),
        )
    )

    response = client.post(
        "/api/settings/open-path",
        json={"path": str(target_path)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "path": str(target_path),
        "status": "opened",
    }
    assert opened_paths == [target_path]


def test_get_environment_reports_tools_and_execution_presets(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    environment_service = EnvironmentService(
        resolver=lambda name: {
            "adb": "/usr/bin/adb",
            "jadx": "/usr/bin/jadx",
            "jadx-gui": "/usr/bin/jadx-gui",
            "mitmdump": "/usr/bin/mitmdump",
        }.get(name),
        module_resolver=lambda name: object() if name == "frida" else None,
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            environment_service=environment_service,
            device_inventory_service=DeviceInventoryService(
                adb_runner=lambda *args: subprocess.CompletedProcess(
                    list(args),
                    0,
                    "List of devices attached\nR5CX1234ABC\tdevice product:r0q model:SM_S9180 device:r0q transport_id:3\n",
                    "",
                )
                if args == ("devices", "-l")
                else subprocess.CompletedProcess(list(args), 0, "arm64-v8a\n", ""),
                frida_device_provider=lambda: {"R5CX1234ABC"},
            ),
        )
    )

    response = client.get("/api/settings/environment")

    assert response.status_code == 200
    assert response.json() == {
        "summary": "5 available, 4 missing",
        "recommended_execution_mode": "real_frida_session",
        "tools": [
            {"name": "jadx", "label": "jadx", "available": True, "path": "/usr/bin/jadx"},
            {"name": "jadx-gui", "label": "jadx-gui", "available": True, "path": "/usr/bin/jadx-gui"},
            {"name": "apktool", "label": "apktool", "available": False, "path": None},
            {"name": "adb", "label": "adb", "available": True, "path": "/usr/bin/adb"},
            {"name": "frida", "label": "frida", "available": False, "path": None},
            {"name": "mitmdump", "label": "mitmdump", "available": True, "path": "/usr/bin/mitmdump"},
            {"name": "mitmproxy", "label": "mitmproxy", "available": False, "path": None},
            {"name": "tcpdump", "label": "tcpdump", "available": False, "path": None},
            {"name": "python-frida", "label": "python-frida", "available": True, "path": "module:frida"},
        ],
        "live_capture": {
            "available": True,
            "source": "builtin_mitmdump",
            "detail": "内置 Mitmdump 已就绪（监听 0.0.0.0:8080）",
            "listen_host": "0.0.0.0",
            "listen_port": 8080,
            "help_text": "请把设备 HTTP/HTTPS 代理指向分析机 IP 的 8080 端口，停止后会自动导入 HAR。",
            "proxy_address_hint": "分析机局域网 IP:8080",
            "install_url": "http://mitm.it",
            "certificate_path": str((tmp_path / "home" / ".mitmproxy" / "mitmproxy-ca-cert.cer").resolve()),
            "certificate_directory_path": str((tmp_path / "home" / ".mitmproxy").resolve()),
            "certificate_exists": False,
            "certificate_help_text": "首次启动内置 Mitmdump 后会在本机生成证书，也可以在设备浏览器访问 http://mitm.it 下载。",
            "proxy_ready": True,
            "certificate_ready": True,
            "https_capture_ready": True,
            "setup_steps": [
                "设置代理：先把测试设备 HTTP / HTTPS 代理指向分析机局域网 IP 的 8080 端口。",
                "安装抓包证书：在设备浏览器访问 http://mitm.it，或直接安装工作台给出的 mitm 证书。",
                "复现关键网络动作：开始抓包后优先复现登录、上报、证书校验或长连接建立等关键动作。",
            ],
            "proxy_steps": [
                "使用局域网 IP：代理主机建议使用分析机局域网 IP，端口固定为 8080。",
                "确认网络可达：如果设备和分析机不在同一网段，先确认路由或热点转发可达。",
            ],
            "certificate_steps": [
                "验证证书解密：安装 mitm 证书后，优先验证浏览器或 WebView 请求是否能正常解密。",
                "处理 HTTPS 拒绝：证书文件还未生成，先启动一次内置抓包或访问 http://mitm.it 再继续。",
            ],
            "recommended_actions": [
                "优先接受网络、HTTPS、SSL 相关 Hook 建议，再开始复现关键请求。",
                "抓到高优流量后，结合 Hook 工作台查看对应类和方法，补齐明文链路。",
            ],
            "setup_step_details": [
                {
                    "key": "builtin-proxy",
                    "title": "设置代理",
                    "detail": "先把测试设备 HTTP / HTTPS 代理指向分析机局域网 IP 的 8080 端口。",
                    "emphasis": "required",
                },
                {
                    "key": "builtin-cert",
                    "title": "安装抓包证书",
                    "detail": "在设备浏览器访问 http://mitm.it，或直接安装工作台给出的 mitm 证书。",
                    "emphasis": "required",
                },
                {
                    "key": "builtin-replay",
                    "title": "复现关键网络动作",
                    "detail": "开始抓包后优先复现登录、上报、证书校验或长连接建立等关键动作。",
                    "emphasis": "recommended",
                },
            ],
            "proxy_step_details": [
                {
                    "key": "proxy-host",
                    "title": "使用局域网 IP",
                    "detail": "代理主机建议使用分析机局域网 IP，端口固定为 8080。",
                    "emphasis": "required",
                },
                {
                    "key": "proxy-network",
                    "title": "确认网络可达",
                    "detail": "如果设备和分析机不在同一网段，先确认路由或热点转发可达。",
                    "emphasis": "recommended",
                },
            ],
            "certificate_step_details": [
                {
                    "key": "certificate-verify",
                    "title": "验证证书解密",
                    "detail": "安装 mitm 证书后，优先验证浏览器或 WebView 请求是否能正常解密。",
                    "emphasis": "recommended",
                },
                {
                    "key": "certificate-followup",
                    "title": "处理 HTTPS 拒绝",
                    "detail": "证书文件还未生成，先启动一次内置抓包或访问 http://mitm.it 再继续。",
                    "emphasis": "recommended",
                },
            ],
            "network_summary": {
                "supports_https_intercept": True,
                "supports_packet_capture": False,
                "supports_ssl_hooking": True,
                "proxy_ready": True,
                "certificate_ready": True,
                "https_capture_ready": True,
            },
            "ssl_hook_guidance": {
                "recommended": True,
                "summary": "建议优先启用 SSL / HTTPS 相关 Hook。",
                "reason": "当前已具备抓包与设备注入基础，优先启用 SSL Hook 更容易拿到 HTTPS 明文与协议细节。",
                "suggested_templates": [
                    "OkHttp3 SSL Unpinning",
                ],
                "suggested_template_entries": [
                    {
                        "template_id": "ssl.okhttp3_unpin",
                        "template_name": "OkHttp3 SSL Unpinning",
                        "plugin_id": "builtin.ssl-okhttp3-unpin",
                    }
                ],
                "suggested_terms": ["https", "ssl", "certificate", "network"],
            },
        },
        "execution_presets": [
            {"key": "fake_backend", "label": "Fake Backend", "available": True, "detail": "ready"},
            {
                "key": "real_device",
                "label": "Real Device",
                "available": True,
                "detail": "ready (Frida Session)",
            },
            {"key": "real_adb_probe", "label": "ADB Probe", "available": True, "detail": "ready"},
            {
                "key": "real_frida_bootstrap",
                "label": "Frida Bootstrap",
                "available": True,
                "detail": "ready",
            },
            {
                "key": "real_frida_probe",
                "label": "Frida Probe",
                "available": False,
                "detail": "unavailable (missing frida)",
            },
            {
                "key": "real_frida_inject",
                "label": "Frida Inject",
                "available": False,
                "detail": "unavailable (missing frida)",
            },
            {
                "key": "real_frida_session",
                "label": "Frida Session",
                "available": True,
                "detail": "ready",
            },
        ],
        "recommended_device_serial": "R5CX1234ABC",
        "connected_devices": [
            {
                "serial": "R5CX1234ABC",
                "state": "device",
                "model": "SM S9180",
                "product": "r0q",
                "device": "r0q",
                "transport_id": "3",
                "abi": "arm64-v8a",
                "rooted": False,
                "frida_visible": True,
                "package_installed": None,
                "is_emulator": False,
            }
        ],
    }


def test_runtime_settings_round_trip_via_settings_api(tmp_path: Path) -> None:
    client = _build_app(tmp_path)

    initial = client.get("/api/settings/runtime")

    assert initial.status_code == 200
    assert initial.json() == {
        "execution_mode": "fake_backend",
        "device_serial": "",
        "frida_server_binary_path": "",
        "frida_server_remote_path": "",
        "frida_session_seconds": "",
        "live_capture_listen_host": "0.0.0.0",
        "live_capture_listen_port": "8080",
    }

    updated = client.put(
        "/api/settings/runtime",
        json={
            "execution_mode": "real_frida_session",
            "device_serial": "emulator-5554",
            "frida_server_binary_path": "/tmp/frida-server",
            "frida_server_remote_path": "/data/local/tmp/frida-server",
            "frida_session_seconds": "4.5",
            "live_capture_listen_host": "127.0.0.1",
            "live_capture_listen_port": "9090",
        },
    )

    assert updated.status_code == 200
    assert updated.json() == {
        "execution_mode": "real_frida_session",
        "device_serial": "emulator-5554",
        "frida_server_binary_path": "/tmp/frida-server",
        "frida_server_remote_path": "/data/local/tmp/frida-server",
        "frida_session_seconds": "4.5",
        "live_capture_listen_host": "127.0.0.1",
        "live_capture_listen_port": "9090",
    }

    restored = client.get("/api/settings/runtime")

    assert restored.status_code == 200
    assert restored.json() == updated.json()


def test_start_execution_forwards_runtime_options_to_backend_and_request(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-runtime"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-runtime",
                "title": "运行参数透传",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-runtime/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-runtime/hook-plan/methods", json=method).status_code == 200
    frida_binary = tmp_path / "frida-server"
    frida_binary.write_text("binary", encoding="utf-8")

    seen: dict[str, object] = {}

    class _CapturingBackend(ExecutionBackend):
        configured = True

        def execute(self, request):  # type: ignore[override]
            seen["request_runtime_env"] = dict(request.runtime_env)
            return (
                HookEvent(
                    timestamp="2026-04-17T00:00:00Z",
                    job_id=request.job_id,
                    event_type="captured_runtime",
                    source="test-backend",
                    class_name="runtime",
                    method_name="execute",
                    arguments=(),
                    return_value=None,
                    stacktrace="",
                    raw_payload={},
                ),
            )

    def _fake_build_execution_backend(execution_mode, *, artifact_root=None, extra_env=None, real_device_command=None):
        seen["execution_mode"] = execution_mode
        seen["extra_env"] = dict(extra_env or {})
        seen["artifact_root"] = artifact_root
        seen["real_device_command"] = real_device_command
        return _CapturingBackend()

    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_backend",
        _fake_build_execution_backend,
    )
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability: (
            ExecutionPresetStatus(key="fake_backend", label="Fake Backend", available=True, detail="ready"),
            ExecutionPresetStatus(key="real_device", label="Real Device", available=True, detail="ready"),
            ExecutionPresetStatus(key="real_frida_session", label="Frida Session", available=True, detail="ready"),
        ),
    )

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-runtime/executions",
            json={
                "execution_mode": "real_frida_session",
                "device_serial": "emulator-5554",
                "frida_server_binary_path": str(frida_binary),
                "frida_server_remote_path": "/data/local/tmp/frida-server",
                "frida_session_seconds": "3.5",
            },
        )
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()

    assert response.status_code == 202
    assert seen["execution_mode"] == "real_frida_session"
    assert seen["extra_env"] == {
        "APKHACKER_DEVICE_SERIAL": "emulator-5554",
        "APKHACKER_FRIDA_SERVER_BINARY": str(frida_binary),
        "APKHACKER_FRIDA_SERVER_REMOTE_PATH": "/data/local/tmp/frida-server",
        "APKHACKER_FRIDA_SESSION_SECONDS": "3.5",
    }
    assert seen["request_runtime_env"] == {
        "APKHACKER_DEVICE_SERIAL": "emulator-5554",
        "APKHACKER_FRIDA_SERVER_BINARY": str(frida_binary),
        "APKHACKER_FRIDA_SERVER_REMOTE_PATH": "/data/local/tmp/frida-server",
        "APKHACKER_FRIDA_SESSION_SECONDS": "3.5",
    }


def test_start_execution_rejects_unavailable_execution_preset_synchronously(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-invalid-preset"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-invalid-preset",
                "title": "预设同步校验",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("APKHACKER_REAL_BACKEND_COMMAND", raising=False)
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability: (
            ExecutionPresetStatus(key="fake_backend", label="Fake Backend", available=True, detail="ready"),
            ExecutionPresetStatus(
                key="real_frida_session",
                label="Frida Session",
                available=False,
                detail="unavailable (not configured)",
            ),
            ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=False,
                detail="unavailable (no ready backend)",
            ),
        ),
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-invalid-preset/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-invalid-preset/hook-plan/methods", json=method).status_code == 200

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-invalid-preset/executions",
            json={"execution_mode": "real_frida_session"},
        )
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Execution preset unavailable: unavailable (not configured)",
    }
    assert pong == {"type": "pong"}


def test_start_execution_rejects_invalid_runtime_options_synchronously(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-invalid-runtime"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-invalid-runtime",
                "title": "运行参数同步校验",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability: (
            ExecutionPresetStatus(key="fake_backend", label="Fake Backend", available=True, detail="ready"),
            ExecutionPresetStatus(key="real_device", label="Real Device", available=True, detail="ready"),
        ),
    )
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-invalid-runtime/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-invalid-runtime/hook-plan/methods", json=method).status_code == 200
    frida_binary = tmp_path / "missing-frida-server"

    response = client.post(
        "/api/cases/case-invalid-runtime/executions",
        json={
            "execution_mode": "real_device",
            "frida_server_binary_path": str(frida_binary),
            "frida_session_seconds": "bad",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Frida server binary path does not exist.",
    }


def test_execution_preflight_reports_ready_and_validation_failures(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-preflight"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-preflight",
                "title": "执行前检查案件",
                "created_at": "2026-04-18T00:00:00Z",
                "updated_at": "2026-04-18T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    device_inventory_service = DeviceInventoryService(
        adb_runner=lambda *args: subprocess.CompletedProcess(list(args), 1, "", "unused"),
        frida_device_provider=lambda: (),
    )
    monkeypatch.setattr(
        device_inventory_service,
        "inspect",
        lambda package_name=None: DeviceInventorySnapshot(
            devices=(
                ConnectedDevice(
                    serial="R5CX1234ABC",
                    state="device",
                    model="Galaxy",
                    rooted=True,
                    frida_visible=False,
                    package_installed=False,
                ),
            )
        ),
    )
    client = _build_app(tmp_path, device_inventory_service=device_inventory_service)

    missing_plan = client.post(
        "/api/cases/case-preflight/executions/preflight",
        json={"execution_mode": "fake_backend"},
    )

    assert missing_plan.status_code == 200
    assert missing_plan.json() == {
        "case_id": "case-preflight",
        "ready": False,
        "execution_mode": "fake_backend",
        "executed_backend_key": "fake_backend",
        "executed_backend_label": "Fake Backend",
        "detail": "Add at least one hook plan item first.",
    }

    method = client.get(
        "/api/cases/case-preflight/workspace/methods",
        params={"query": "upload", "limit": 1},
    ).json()["items"][0]
    assert client.post("/api/cases/case-preflight/hook-plan/methods", json=method).status_code == 200

    frida_server_binary = tmp_path / "frida-server"
    frida_server_binary.write_text("demo", encoding="utf-8")
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability=None: (
            ExecutionPresetStatus(
                key="fake_backend",
                label="Fake Backend",
                available=True,
                detail="ready",
            ),
            ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=True,
                detail="ready (custom)",
            ),
            ExecutionPresetStatus(
                key="real_adb_probe",
                label="ADB Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_bootstrap",
                label="Frida Bootstrap",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_probe",
                label="Frida Probe",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_inject",
                label="Frida Inject",
                available=False,
                detail="unavailable",
            ),
            ExecutionPresetStatus(
                key="real_frida_session",
                label="Frida Session",
                available=False,
                detail="unavailable",
            ),
        ),
    )

    ready = client.post(
        "/api/cases/case-preflight/executions/preflight",
        json={
            "execution_mode": "real_device",
            "frida_server_binary_path": str(frida_server_binary),
            "frida_session_seconds": "3",
        },
    )

    assert ready.status_code == 200
    assert ready.json() == {
        "case_id": "case-preflight",
        "ready": True,
        "execution_mode": "real_device",
        "executed_backend_key": "real_device",
        "executed_backend_label": "Real Device",
        "detail": "ready",
    }


def test_execution_preflight_requires_device_selection_when_multiple_devices_are_connected(
    tmp_path: Path, monkeypatch
) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-device-preflight"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-device-preflight",
                "title": "设备选择案件",
                "created_at": "2026-04-19T00:00:00Z",
                "updated_at": "2026-04-19T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability=None: (
            ExecutionPresetStatus(key="fake_backend", label="Fake Backend", available=True, detail="ready"),
            ExecutionPresetStatus(key="real_device", label="Real Device", available=True, detail="ready (custom)"),
        ),
    )
    device_inventory_service = DeviceInventoryService(
        adb_runner=lambda *args: subprocess.CompletedProcess(list(args), 1, "", "unused"),
        frida_device_provider=lambda: (),
    )
    monkeypatch.setattr(
        device_inventory_service,
        "inspect",
        lambda package_name=None: DeviceInventorySnapshot(
            devices=(
                ConnectedDevice(serial="emulator-5554", state="device", model="Pixel", is_emulator=True),
                ConnectedDevice(serial="R5CX1234ABC", state="device", model="Galaxy"),
            )
        ),
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=_FakeStaticAnalyzer(
                StaticArtifacts(
                    output_root=tmp_path / "artifacts",
                    report_dir=tmp_path / "artifacts" / "报告" / "sample",
                    cache_dir=tmp_path / "artifacts" / "cache" / "sample",
                    analysis_json=Path("tests/fixtures/static_outputs/sample_analysis.json").resolve(),
                    callback_config_json=Path("tests/fixtures/static_outputs/sample_callback-config.json").resolve(),
                    noise_log_json=tmp_path / "artifacts" / "cache" / "sample" / "noise-log.json",
                    jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
                    jadx_project_dir=None,
                )
            ),
            device_inventory_service=device_inventory_service,
        )
    )

    method = client.get(
        "/api/cases/case-device-preflight/workspace/methods",
        params={"query": "upload", "limit": 1},
    ).json()["items"][0]
    assert client.post("/api/cases/case-device-preflight/hook-plan/methods", json=method).status_code == 200

    response = client.post(
        "/api/cases/case-device-preflight/executions/preflight",
        json={"execution_mode": "real_device"},
    )

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["detail"] == "检测到多个已连接设备，请先选择目标设备。"


def test_execution_preflight_requires_frida_visibility_for_frida_session(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-frida-preflight"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-frida-preflight",
                "title": "Frida 预检案件",
                "created_at": "2026-04-19T00:00:00Z",
                "updated_at": "2026-04-19T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "apk_hacker.application.services.workspace_runtime_service.build_execution_preset_statuses",
        lambda snapshot, runtime_availability=None: (
            ExecutionPresetStatus(key="fake_backend", label="Fake Backend", available=True, detail="ready"),
            ExecutionPresetStatus(key="real_device", label="Real Device", available=True, detail="ready (Frida Session)"),
            ExecutionPresetStatus(key="real_frida_session", label="Frida Session", available=True, detail="ready"),
        ),
    )
    device_inventory_service = DeviceInventoryService(
        adb_runner=lambda *args: subprocess.CompletedProcess(list(args), 1, "", "unused"),
        frida_device_provider=lambda: (),
    )
    monkeypatch.setattr(
        device_inventory_service,
        "inspect",
        lambda package_name=None: DeviceInventorySnapshot(
            devices=(
                ConnectedDevice(
                    serial="R5CX1234ABC",
                    state="device",
                    model="Galaxy",
                    rooted=True,
                    frida_visible=False,
                    package_installed=True,
                ),
            )
        ),
    )
    client = _build_app(tmp_path, device_inventory_service=device_inventory_service)

    method = client.get(
        "/api/cases/case-frida-preflight/workspace/methods",
        params={"query": "upload", "limit": 1},
    ).json()["items"][0]
    assert client.post("/api/cases/case-frida-preflight/hook-plan/methods", json=method).status_code == 200

    response = client.post(
        "/api/cases/case-frida-preflight/executions/preflight",
        json={
            "execution_mode": "real_frida_session",
            "device_serial": "R5CX1234ABC",
        },
    )

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["detail"] == "所选设备当前未被 Frida 识别，请提供 Frida Server 文件或先完成自举。"


def test_execution_history_routes_replay_completed_run_events(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-history"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-history",
                "title": "执行历史案件",
                "created_at": "2026-04-18T00:00:00Z",
                "updated_at": "2026-04-18T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    method = client.get(
        "/api/cases/case-history/workspace/methods",
        params={"query": "upload", "limit": 1},
    ).json()["items"][0]
    assert client.post("/api/cases/case-history/hook-plan/methods", json=method).status_code == 200

    with client.websocket_connect("/ws") as websocket:
        response = client.post(
            "/api/cases/case-history/executions",
            json={"execution_mode": "fake_backend"},
        )
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        completed_event = websocket.receive_json()

    assert response.status_code == 202

    history = client.get("/api/cases/case-history/executions/history")

    assert history.status_code == 200
    payload = history.json()
    assert payload["case_id"] == "case-history"
    assert len(payload["items"]) == 1
    entry = payload["items"][0]
    assert entry["run_id"] == completed_event["run_id"]
    assert entry["status"] == "completed"
    assert entry["execution_mode"] == "fake_backend"
    assert entry["executed_backend_key"] == "fake_backend"
    assert entry["event_count"] == completed_event["event_count"]
    assert entry["db_path"] == completed_event["db_path"]
    assert entry["bundle_path"] == completed_event["bundle_path"]

    events = client.get(
        f"/api/cases/case-history/executions/history/{entry['history_id']}/events",
        params={"limit": 5},
    )

    assert events.status_code == 200
    events_payload = events.json()
    assert events_payload["case_id"] == "case-history"
    assert len(events_payload["items"]) > 0
    assert all(item["type"] == "execution.event" for item in events_payload["items"])
