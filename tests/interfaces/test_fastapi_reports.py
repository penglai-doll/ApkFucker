from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_export_report_returns_report_path(tmp_path: Path) -> None:
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
            "title": "报告测试",
        },
    )
    case_id = import_response.json()["case_id"]

    response = client.post(f"/api/cases/{case_id}/reports/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == case_id
    assert payload["report_path"].endswith("merged-report.md")
