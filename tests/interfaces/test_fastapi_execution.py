from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_websocket_pings_pong(tmp_path: Path) -> None:
    client = TestClient(
        build_app(
            db_root=tmp_path / "cache",
            scripts_root=tmp_path / "scripts",
            workspace_root=tmp_path / "workspaces",
        )
    )

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "ping"})
        payload = websocket.receive_json()

    assert payload["type"] == "pong"


def test_startup_settings_include_last_workspace(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk-bytes")
    client = TestClient(
        build_app(
            db_root=tmp_path / "cache",
            scripts_root=tmp_path / "scripts",
            workspace_root=tmp_path / "workspaces",
        )
    )
    import_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample_path),
            "workspace_root": str(tmp_path / "workspaces"),
            "title": "启动设置",
        },
    )
    case_id = import_response.json()["case_id"]
    workspace_root = import_response.json()["workspace_root"]

    response = client.get("/api/settings/startup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["launch_view"] == "workspace"
    assert payload["last_workspace_root"] == workspace_root
    assert payload["last_case_id"] == case_id
