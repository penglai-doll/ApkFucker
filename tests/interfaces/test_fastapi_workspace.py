from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.workspace_controller import WorkspaceController
from apk_hacker.application.services.workspace_registry_service import default_workspace_registry_path
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.static_engine.analyzer import StaticArtifacts
from apk_hacker.interfaces.api_fastapi.app import build_app


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts
        self.calls: list[tuple[Path, Path | None, str]] = []

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        self.calls.append((target_path, output_dir, mode))
        return self.artifacts


class _FakeJadxLauncher:
    def __init__(self, resolved_path: str | None = "/usr/local/bin/jadx-gui") -> None:
        self.resolved_path = resolved_path
        self.open_calls: list[tuple[str, Path]] = []

    def resolve(self, explicit_path: str | None) -> str | None:
        return self.resolved_path

    def open(self, jadx_gui_path: str, target_path: Path) -> None:
        self.open_calls.append((jadx_gui_path, target_path))


def _make_static_analyzer(
    *,
    tmp_path: Path,
    jadx_sources_dir: Path | None = None,
) -> _FakeStaticAnalyzer:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    return _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=tmp_path / "cache",
            report_dir=tmp_path / "cache" / "报告" / "sample",
            cache_dir=tmp_path / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=tmp_path / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources_dir,
            jadx_project_dir=None,
        )
    )


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


def test_import_case_returns_404_for_missing_sample(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    client = TestClient(build_app(default_workspace_root=workspace_root))

    response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(tmp_path / "missing.apk"),
            "workspace_root": str(workspace_root),
            "title": "缺失样本",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Sample file not found"


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


def test_workspace_lookup_survives_app_restart_for_override_root(tmp_path: Path) -> None:
    default_root = tmp_path / "default-workspaces"
    override_root = tmp_path / "override-workspaces"
    sample = tmp_path / "override-demo.apk"
    sample.write_bytes(b"apk")
    registry_path = tmp_path / "api-registry.json"
    client = TestClient(build_app(default_workspace_root=default_root, registry_path=registry_path))

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(override_root),
            "title": "切换根目录",
        },
    )
    case_id = create_response.json()["case_id"]

    reopened_client = TestClient(
        build_app(default_workspace_root=default_root, registry_path=registry_path)
    )
    workspace_response = reopened_client.get(f"/api/cases/{case_id}/workspace")

    assert workspace_response.status_code == 200
    assert workspace_response.json()["title"] == "切换根目录"


def test_workspace_lookup_uses_workspace_metadata_case_id(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    mismatched_case_root = workspace_root / "folder-name"
    mismatched_case_root.mkdir(parents=True)
    (mismatched_case_root / "workspace.json").write_text(
        """
        {
          "case_id": "case-real",
          "title": "真实案件",
          "workspace_version": 1,
          "created_at": "2026-04-10T00:00:00Z",
          "updated_at": "2026-04-10T00:00:00Z",
          "sample_filename": "original.apk"
        }
        """.strip(),
        encoding="utf-8",
    )
    client = TestClient(build_app(default_workspace_root=workspace_root))

    response = client.get("/api/cases/case-real/workspace")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "case-real",
        "title": "真实案件",
        "view": "workspace",
    }


def test_api_sees_controller_initialized_workspace_via_default_registry_path(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    workspace_root = tmp_path / "override-workspaces"
    expected_registry_path = default_workspace_registry_path(workspace_root.parent)

    controller = WorkspaceController(
        db_root=tmp_path / "cache" / "gui",
        scripts_root=scripts_root,
        job_service=JobService(
            static_analyzer=_FakeStaticAnalyzer(
                StaticArtifacts(
                    output_root=tmp_path / "cache",
                    report_dir=tmp_path / "cache" / "报告" / "sample",
                    cache_dir=tmp_path / "cache" / "sample",
                    analysis_json=fixture_root / "sample_analysis.json",
                    callback_config_json=fixture_root / "sample_callback-config.json",
                    noise_log_json=tmp_path / "cache" / "sample" / "noise-log.json",
                    jadx_sources_dir=jadx_sources,
                    jadx_project_dir=None,
                )
            )
        ),
        workspace_service=WorkspaceService(),
        case_queue_service=CaseQueueService(),
        custom_script_service=CustomScriptService(scripts_root),
        report_export_service=ReportExportService(),
    )

    state = controller.initialize_workspace(
        sample_path=sample_path,
        workspace_root=workspace_root,
        title="控制器案件",
    )
    client = TestClient(build_app(default_workspace_root=tmp_path / "workspaces"))

    cases_response = client.get("/api/cases")
    workspace_response = client.get(f"/api/cases/{state.workspace.case_id}/workspace")

    assert expected_registry_path == controller.db_root / "workspace-registry.json"
    assert cases_response.status_code == 200
    assert cases_response.json()["items"] == [
        {
            "case_id": state.workspace.case_id,
            "title": "控制器案件",
            "workspace_root": str(state.workspace.workspace_root),
        }
    ]
    assert workspace_response.status_code == 200
    assert workspace_response.json()["title"] == "控制器案件"


def test_workspace_detail_returns_static_brief_and_custom_scripts(tmp_path: Path) -> None:
    sample = tmp_path / "detail-demo.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    (scripts_root / "ssl-okhttp.js").write_text("// ssl", encoding="utf-8")
    (scripts_root / "cipher-monitor.js").write_text("// crypto", encoding="utf-8")
    static_analyzer = _make_static_analyzer(
        tmp_path=tmp_path,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
            custom_scripts_root=scripts_root,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "静态简报案件",
        },
    )
    case_id = create_response.json()["case_id"]

    detail_response = client.get(f"/api/cases/{case_id}/workspace/detail")

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["case_id"] == case_id
    assert payload["title"] == "静态简报案件"
    assert payload["package_name"] == "com.demo.shell"
    assert payload["technical_tags"] == ["webview-hybrid", "network-callback"]
    assert payload["dangerous_permissions"] == ["android.permission.READ_SMS", "android.permission.RECORD_AUDIO"]
    assert payload["callback_endpoints"] == ["https://demo-c2.example/api/upload", "demo-c2.example", "1.2.3.4"]
    assert payload["callback_clues"]
    assert payload["crypto_signals"] == ["AES/CBC/PKCS5Padding", "HMAC-SHA256"]
    assert payload["packer_hints"] == ["com.tencent.legu"]
    assert payload["limitations"]
    assert [item["name"] for item in payload["custom_scripts"]] == ["cipher-monitor", "ssl-okhttp"]
    assert payload["can_open_in_jadx"] is True
    assert payload["has_method_index"] is True
    assert payload["method_count"] > 0
    assert len(static_analyzer.calls) == 1


def test_workspace_methods_filters_results_and_uses_loaded_bundle(tmp_path: Path) -> None:
    sample = tmp_path / "methods-demo.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    static_analyzer = _make_static_analyzer(
        tmp_path=tmp_path,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "方法检索案件",
        },
    )
    case_id = create_response.json()["case_id"]

    detail_response = client.get(f"/api/cases/{case_id}/workspace/detail")
    assert detail_response.status_code == 200

    methods_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "upload", "limit": 2},
    )

    assert methods_response.status_code == 200
    payload = methods_response.json()
    assert payload["items"]
    assert len(payload["items"]) <= 2
    assert {item["method_name"] for item in payload["items"]} == {"buildUploadUrl"}
    assert len(static_analyzer.calls) == 1


def test_workspace_methods_returns_empty_list_without_jadx_sources(tmp_path: Path) -> None:
    sample = tmp_path / "methods-empty.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    static_analyzer = _make_static_analyzer(tmp_path=tmp_path, jadx_sources_dir=None)
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "无索引案件",
        },
    )
    case_id = create_response.json()["case_id"]

    methods_response = client.get(f"/api/cases/{case_id}/workspace/methods", params={"query": "upload"})

    assert methods_response.status_code == 200
    assert methods_response.json() == {"items": [], "total": 0}


def test_workspace_recommendations_include_template_fallback_without_method_index(tmp_path: Path) -> None:
    sample = tmp_path / "recommend-demo.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    static_analyzer = _make_static_analyzer(tmp_path=tmp_path, jadx_sources_dir=None)
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "推荐案件",
        },
    )
    case_id = create_response.json()["case_id"]

    recommendations_response = client.get(
        f"/api/cases/{case_id}/workspace/recommendations",
        params={"limit": 5},
    )

    assert recommendations_response.status_code == 200
    payload = recommendations_response.json()
    assert payload["items"]
    assert payload["items"][0]["kind"] == "template_hook"
    assert "SSL" in payload["items"][0]["title"]


def test_open_jadx_returns_success_when_launcher_is_available(tmp_path: Path) -> None:
    sample = tmp_path / "jadx-open.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    static_analyzer = _make_static_analyzer(
        tmp_path=tmp_path,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
    )
    launcher = _FakeJadxLauncher()
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
            jadx_gui_resolver=launcher.resolve,
            jadx_opener=launcher.open,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "JADX 打开案件",
        },
    )
    case_id = create_response.json()["case_id"]

    response = client.post(f"/api/cases/{case_id}/actions/open-jadx")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": case_id,
        "status": "opened",
    }
    assert launcher.open_calls == [
        (
            "/usr/local/bin/jadx-gui",
            Path("tests/fixtures/jadx_sources").resolve(),
        )
    ]


def test_open_jadx_returns_409_when_launcher_is_unavailable(tmp_path: Path) -> None:
    sample = tmp_path / "jadx-missing.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    static_analyzer = _make_static_analyzer(
        tmp_path=tmp_path,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
    )
    launcher = _FakeJadxLauncher(resolved_path=None)
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
            jadx_gui_resolver=launcher.resolve,
            jadx_opener=launcher.open,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "JADX 缺失案件",
        },
    )
    case_id = create_response.json()["case_id"]

    response = client.post(f"/api/cases/{case_id}/actions/open-jadx")

    assert response.status_code == 409
    assert response.json()["detail"] == "jadx-gui is not configured or not available"
    assert launcher.open_calls == []


def test_hook_plan_api_persists_sources_and_renders_plan_preview(tmp_path: Path) -> None:
    sample = tmp_path / "hook-plan-demo.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    static_analyzer = _make_static_analyzer(
        tmp_path=tmp_path,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
            custom_scripts_root=scripts_root,
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "Hook Plan 案件",
        },
    )
    case_id = create_response.json()["case_id"]
    case_root = Path(create_response.json()["workspace_root"])
    sample_root = case_root / "sample"
    sample_root.mkdir(parents=True, exist_ok=True)
    (sample_root / "original.apk").write_bytes(b"apk")

    method_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    add_method_response = client.post(
        f"/api/cases/{case_id}/hook-plan/methods",
        json=method,
    )
    assert add_method_response.status_code == 200

    recommendation_response = client.get(
        f"/api/cases/{case_id}/workspace/recommendations",
        params={"limit": 8},
    )
    recommendation_items = recommendation_response.json()["items"]
    recommendation_id = next(
        (
            item["recommendation_id"]
            for item in recommendation_items
            if item["kind"] != "method_hook"
            or item.get("method", {}).get("method_name") != method["method_name"]
        ),
        recommendation_items[0]["recommendation_id"],
    )
    add_recommendation_response = client.post(
        f"/api/cases/{case_id}/hook-plan/recommendations",
        json={"recommendation_id": recommendation_id},
    )
    assert add_recommendation_response.status_code == 200

    script_save_response = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "trace_login", "content": "send('trace');\n"},
    )
    assert script_save_response.status_code == 200
    scripts_response = client.get(f"/api/cases/{case_id}/custom-scripts")
    script_id = scripts_response.json()["items"][0]["script_id"]
    add_script_response = client.post(
        f"/api/cases/{case_id}/hook-plan/custom-scripts",
        json={"script_id": script_id},
    )
    assert add_script_response.status_code == 200

    hook_plan_response = client.get(f"/api/cases/{case_id}/hook-plan")
    assert hook_plan_response.status_code == 200
    payload = hook_plan_response.json()
    assert payload["case_id"] == case_id
    assert payload["updated_at"]
    assert len(payload["items"]) == 3
    assert all("rendered_script" in item["render_context"] for item in payload["items"])
    runtime_state_path = case_root / "workspace-runtime.json"
    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    assert runtime_state["case_id"] == case_id
    assert len(runtime_state["selected_hook_sources"]) == 3
    assert len(runtime_state["rendered_hook_plan"]["items"]) == 3

    first_item_id = payload["items"][0]["item_id"]
    remove_response = client.delete(f"/api/cases/{case_id}/hook-plan/items/{first_item_id}")
    assert remove_response.status_code == 200
    assert len(remove_response.json()["items"]) == 2

    clear_response = client.delete(f"/api/cases/{case_id}/hook-plan")
    assert clear_response.status_code == 200
    assert clear_response.json()["items"] == []
