from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistry
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.app import build_app


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


def test_start_execution_returns_started_and_broadcasts_websocket_event(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-123"
    case_root.mkdir(parents=True)
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
    client = TestClient(build_app(default_workspace_root=workspace_root))

    with client.websocket_connect("/ws") as websocket:
        response = client.post("/api/cases/case-123/executions")
        assert response.status_code == 202
        assert response.json() == {
            "case_id": "case-123",
            "status": "started",
        }
        event = websocket.receive_json()

    assert event == {
        "type": "execution.started",
        "case_id": "case-123",
        "status": "started",
    }


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


def test_get_environment_reports_tools_and_execution_presets(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    environment_service = EnvironmentService(
        resolver=lambda name: {
            "adb": "/usr/bin/adb",
            "jadx": "/usr/bin/jadx",
            "jadx-gui": "/usr/bin/jadx-gui",
        }.get(name),
        module_resolver=lambda name: object() if name == "frida" else None,
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            environment_service=environment_service,
        )
    )

    response = client.get("/api/settings/environment")

    assert response.status_code == 200
    assert response.json() == {
        "summary": "4 available, 2 missing",
        "recommended_execution_mode": "real_frida_session",
        "tools": [
            {"name": "jadx", "label": "jadx", "available": True, "path": "/usr/bin/jadx"},
            {"name": "jadx-gui", "label": "jadx-gui", "available": True, "path": "/usr/bin/jadx-gui"},
            {"name": "apktool", "label": "apktool", "available": False, "path": None},
            {"name": "adb", "label": "adb", "available": True, "path": "/usr/bin/adb"},
            {"name": "frida", "label": "frida", "available": False, "path": None},
            {"name": "python-frida", "label": "python-frida", "available": True, "path": "module:frida"},
        ],
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
    }
