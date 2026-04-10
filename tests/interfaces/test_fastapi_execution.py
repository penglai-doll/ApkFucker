from __future__ import annotations

from fastapi.testclient import TestClient

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
