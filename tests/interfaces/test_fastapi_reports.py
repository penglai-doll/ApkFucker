from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_export_report_returns_stable_case_scoped_path(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-report"
    case_root.mkdir(parents=True)
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-report",
                "title": "报告案件",
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

    response = client.post("/api/cases/case-report/reports/export")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "case-report",
        "report_path": str(case_root / "reports" / "case-report-report.md"),
    }
