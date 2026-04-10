from __future__ import annotations

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_list_cases_returns_empty_items() -> None:
    client = TestClient(build_app())

    response = client.get("/api/cases")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_app_exposes_minimal_api_surface() -> None:
    client = TestClient(build_app())

    routes = {route.path for route in client.app.routes}

    assert "/api/cases" in routes
    assert "/ws" in routes

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
