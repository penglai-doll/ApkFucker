from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

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
