from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_list_cases_returns_empty_items(tmp_path: Path) -> None:
    client = TestClient(build_app(workspace_root=tmp_path / "workspaces"))

    response = client.get("/api/cases")

    assert response.status_code == 200
    assert response.json() == {"items": []}
