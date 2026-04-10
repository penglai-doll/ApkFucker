from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_list_cases_returns_empty_items_when_workspace_root_missing(tmp_path: Path) -> None:
    client = TestClient(
        build_app(
            default_workspace_root=tmp_path / "missing-workspaces",
            registry_path=tmp_path / "api-registry.json",
        )
    )

    response = client.get("/api/cases")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_cases_returns_workspace_items_from_case_queue_service(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-001"
    case_root.mkdir(parents=True)
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "case_id": "case-001",
                "title": "Alpha",
                "workspace_version": 1,
                "created_at": "2026-04-10T00:00:00Z",
                "updated_at": "2026-04-10T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            registry_path=tmp_path / "api-registry.json",
        )
    )

    response = client.get("/api/cases")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "case_id": "case-001",
                "title": "Alpha",
                "workspace_root": str(case_root),
            }
        ]
    }


def test_list_cases_merges_default_and_registered_workspace_roots(tmp_path: Path) -> None:
    default_root = tmp_path / "default-workspaces"
    default_case_root = default_root / "case-default"
    default_case_root.mkdir(parents=True)
    (default_case_root / "workspace.json").write_text(
        json.dumps(
            {
                "case_id": "case-default",
                "title": "Default Case",
                "workspace_version": 1,
                "created_at": "2026-04-10T00:00:00Z",
                "updated_at": "2026-04-10T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    override_root = tmp_path / "override-workspaces"
    sample = tmp_path / "override.apk"
    sample.write_bytes(b"apk")
    registry_path = tmp_path / "api-registry.json"

    import_client = TestClient(
        build_app(default_workspace_root=default_root, registry_path=registry_path)
    )
    import_response = import_client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(override_root),
            "title": "Override Case",
        },
    )

    reopened_client = TestClient(
        build_app(default_workspace_root=default_root, registry_path=registry_path)
    )
    response = reopened_client.get("/api/cases")

    assert import_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "case_id": "case-default",
            "title": "Default Case",
            "workspace_root": str(default_case_root),
        },
        {
            "case_id": import_response.json()["case_id"],
            "title": "Override Case",
            "workspace_root": str(override_root / import_response.json()["case_id"]),
        },
    ]


def test_app_exposes_minimal_api_surface() -> None:
    client = TestClient(build_app())

    routes = {route.path for route in client.app.routes}

    assert "/api/cases" in routes
    assert "/api/cases/import" in routes
    assert "/api/cases/{case_id}/workspace" in routes
    assert "/ws" in routes

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
