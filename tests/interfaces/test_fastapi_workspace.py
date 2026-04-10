from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_import_case_creates_workspace(tmp_path: Path) -> None:
    sample = tmp_path / "demo.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    client = TestClient(build_app(default_workspace_root=workspace_root))

    response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "队列测试",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "队列测试"
    assert payload["case_id"].startswith("case-")
    assert Path(payload["workspace_root"]).is_dir()
    assert Path(payload["sample_path"]).is_file()


def test_get_workspace_returns_minimal_workspace_view(tmp_path: Path) -> None:
    sample = tmp_path / "workspace-demo.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    client = TestClient(build_app(default_workspace_root=workspace_root))

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "工作台测试",
        },
    )
    case_id = create_response.json()["case_id"]

    response = client.get(f"/api/cases/{case_id}/workspace")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": case_id,
        "title": "工作台测试",
        "view": "workspace",
    }
