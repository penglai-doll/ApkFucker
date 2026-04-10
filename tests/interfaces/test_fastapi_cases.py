from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_list_cases_returns_empty_items(tmp_path: Path) -> None:
    client = TestClient(
        build_app(
            db_root=tmp_path / "cache",
            scripts_root=tmp_path / "scripts",
            workspace_root=tmp_path / "workspaces",
        )
    )

    response = client.get("/api/cases")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_import_case_creates_workspace(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk-bytes")
    client = TestClient(
        build_app(
            db_root=tmp_path / "cache",
            scripts_root=tmp_path / "scripts",
            workspace_root=tmp_path / "workspaces",
        )
    )

    response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample_path),
            "workspace_root": str(tmp_path / "workspaces"),
            "title": "队列测试",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "队列测试"
    assert payload["workspace_root"].startswith(str(tmp_path / "workspaces"))
    assert Path(payload["sample_path"]).read_bytes() == b"apk-bytes"
