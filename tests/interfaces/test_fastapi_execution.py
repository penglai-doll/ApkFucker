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
