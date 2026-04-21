from __future__ import annotations

import json
from pathlib import Path
import time

from fastapi.testclient import TestClient

from apk_hacker.static_engine.analyzer import StaticArtifacts
from apk_hacker.interfaces.api_fastapi.app import build_app


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        del target_path, output_dir, mode
        return self.artifacts


def _build_app(tmp_path: Path) -> TestClient:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=tmp_path / "artifacts",
            report_dir=tmp_path / "artifacts" / "报告" / "sample",
            cache_dir=tmp_path / "artifacts" / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=tmp_path / "artifacts" / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    return TestClient(build_app(default_workspace_root=tmp_path / "workspaces", static_analyzer=fake_analyzer))


def _wait_for_execution_completion(state_path: Path) -> dict[str, object]:
    for _ in range(20):
        if state_path.exists():
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            if payload.get("last_execution_status") == "completed":
                return payload
        time.sleep(0.1)
    raise AssertionError("Execution did not complete within the expected time window.")


def test_export_report_returns_stable_case_scoped_path(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-report"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
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
    client = _build_app(tmp_path)

    method_response = client.get(
        "/api/cases/case-report/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post("/api/cases/case-report/hook-plan/methods", json=method).status_code == 200
    assert client.post("/api/cases/case-report/executions", json={"execution_mode": "fake_backend"}).status_code == 202
    _wait_for_execution_completion(case_root / "workspace-runtime.json")

    response = client.post("/api/cases/case-report/reports/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "case-report"
    assert payload["report_path"] == str(case_root / "reports" / "case-report-report.md")
    assert payload["static_report_path"].endswith("report.md")
    report_content = Path(payload["report_path"]).read_text(encoding="utf-8")
    assert "- Last Status: completed" in report_content
    assert "- Requested Mode: fake_backend" in report_content
    assert "- Executed Backend: fake_backend" in report_content
    assert "- Failure Code: -" in report_content
    assert "- Failure Message: -" in report_content
    runtime_state = json.loads((case_root / "workspace-runtime.json").read_text(encoding="utf-8"))
    assert runtime_state["last_report_path"] == payload["report_path"]


def test_export_report_includes_imported_traffic_capture(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    case_root = workspace_root / "case-traffic-report"
    case_root.mkdir(parents=True)
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True)
    (sample_root / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "case_id": "case-traffic-report",
                "title": "流量报告案件",
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client = _build_app(tmp_path)

    import_response = client.post(
        "/api/cases/case-traffic-report/traffic/import",
        json={"har_path": str(Path("tests/fixtures/traffic/sample.har").resolve())},
    )
    assert import_response.status_code == 200

    response = client.post("/api/cases/case-traffic-report/reports/export")

    assert response.status_code == 200
    payload = response.json()
    report_content = Path(payload["report_path"]).read_text(encoding="utf-8")
    assert "## Traffic Capture" in report_content
    assert "sample.har" in report_content
    assert "- Flow Count: 2" in report_content
    assert "- Suspicious Count: 1" in report_content
    assert "- HTTPS Flow Count: 2" in report_content
    assert "- Matched Indicator Count: 2" in report_content
    assert "### Top Hosts" in report_content
    assert "- demo-c2.example: 1 flows, 1 suspicious, 1 HTTPS" in report_content
    assert "### Suspicious Hosts" in report_content
