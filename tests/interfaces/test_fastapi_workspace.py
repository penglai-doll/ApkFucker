from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.workspace_controller import WorkspaceController
from apk_hacker.application.services.workspace_registry_service import default_workspace_registry_path
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.hook_plan import HookPlanItem
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.hook_plan import MethodHookTarget
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.static_engine.analyzer import StaticArtifacts
from apk_hacker.interfaces.api_fastapi.app import build_app
from apk_hacker.interfaces.api_fastapi.routes_workspace import build_workspace_router


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


def _wait_for_execution_completion(state_path: Path) -> dict[str, object]:
    for _ in range(100):
        if state_path.exists():
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            if payload.get("last_execution_status") == "completed":
                return payload
        time.sleep(0.1)
    raise AssertionError("Execution did not complete within the expected time window.")


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


def _write_live_capture_runner(tmp_path: Path, fixture_har: Path) -> Path:
    script_path = tmp_path / "live_capture_runner.py"
    script_path.write_text(
        f"""
import shutil
import signal
import sys
import time
from pathlib import Path

source = Path({str(fixture_har)!r})
output = Path(sys.argv[1])
output.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(source, output)

running = True

def _stop(*_args):
    global running
    running = False

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

while running:
    time.sleep(0.05)
""".strip(),
        encoding="utf-8",
    )
    return script_path


def _write_related_candidate_sources(tmp_path: Path) -> Path:
    sources_root = tmp_path / "related_sources"
    (sources_root / "com" / "demo" / "shell").mkdir(parents=True, exist_ok=True)
    (sources_root / "okhttp3").mkdir(parents=True, exist_ok=True)
    (sources_root / "com" / "thirdparty" / "crypto").mkdir(parents=True, exist_ok=True)
    (sources_root / "org" / "other").mkdir(parents=True, exist_ok=True)

    (sources_root / "com" / "demo" / "shell" / "UploadManager.java").write_text(
        """
package com.demo.shell;

public class UploadManager {
    public String buildUploadUrl(String host) {
        return "https://demo-c2.example/api/upload";
    }
}
""".strip(),
        encoding="utf-8",
    )
    (sources_root / "com" / "demo" / "shell" / "HomeActivity.java").write_text(
        """
package com.demo.shell;

public class HomeActivity {
    protected void onCreate(android.os.Bundle savedInstanceState) {
        String note = "home screen entry";
    }
}
""".strip(),
        encoding="utf-8",
    )
    (sources_root / "okhttp3" / "OkHttpClient.java").write_text(
        """
package okhttp3;

public class OkHttpClient {
    public Call newCall(Request request) {
        String note = "network callback request url";
        return null;
    }
}
""".strip(),
        encoding="utf-8",
    )
    (sources_root / "com" / "thirdparty" / "crypto" / "CipherHelper.java").write_text(
        """
package com.thirdparty.crypto;

public class CipherHelper {
    public byte[] encryptPayload(byte[] data) {
        String note = "cipher AES/CBC/PKCS5Padding";
        return data;
    }
}
""".strip(),
        encoding="utf-8",
    )
    (sources_root / "org" / "other" / "DebugHelper.java").write_text(
        """
package org.other;

public class DebugHelper {
    public void dump(String value) {
        String note = "debug output";
    }
}
""".strip(),
        encoding="utf-8",
    )
    return sources_root


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


def test_import_case_runs_static_analysis_and_builds_method_index(tmp_path: Path) -> None:
    sample = tmp_path / "indexed.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    jadx_sources_dir = Path("tests/fixtures/jadx_sources").resolve()
    static_analyzer = _make_static_analyzer(tmp_path=tmp_path, jadx_sources_dir=jadx_sources_dir)
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
        )
    )

    response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "自动建索引",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert static_analyzer.calls == [
        (
            Path(payload["sample_path"]),
            Path(payload["workspace_root"]) / "static",
            "auto",
        )
    ]

    detail_response = client.get(f"/api/cases/{payload['case_id']}/workspace/detail")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["has_method_index"] is True
    assert detail_payload["method_count"] > 0


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


def test_live_traffic_capture_returns_unavailable_when_command_not_configured(tmp_path: Path) -> None:
    sample = tmp_path / "live-unavailable.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            environment_service=EnvironmentService(resolver=lambda _name: None),
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "抓包未配置",
        },
    )
    case_id = create_response.json()["case_id"]

    response = client.get(f"/api/cases/{case_id}/traffic/live")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": case_id,
        "status": "unavailable",
        "artifact_path": None,
        "message": "未配置实时抓包命令，请设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND。",
    }


def test_live_traffic_capture_start_and_stop_imports_har_artifact(tmp_path: Path) -> None:
    sample = tmp_path / "live-capture.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    fixture_har = Path("tests/fixtures/traffic/sample.har").resolve()
    runner = _write_live_capture_runner(tmp_path, fixture_har)
    static_analyzer = _make_static_analyzer(tmp_path=tmp_path, jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve())
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
            traffic_capture_command=f"{sys.executable} {runner} {{output_path}}",
        )
    )

    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(workspace_root),
            "title": "实时抓包导入",
        },
    )
    case_id = create_response.json()["case_id"]

    start_response = client.post(f"/api/cases/{case_id}/traffic/live/start")
    assert start_response.status_code == 200
    assert start_response.json()["case_id"] == case_id
    assert start_response.json()["status"] == "running"
    time.sleep(0.1)

    stop_response = client.post(f"/api/cases/{case_id}/traffic/live/stop")
    assert stop_response.status_code == 200
    stop_payload = stop_response.json()
    assert stop_payload["case_id"] == case_id
    assert stop_payload["status"] == "stopped"
    assert stop_payload["artifact_path"] is not None
    assert stop_payload["message"] == "已停止实时抓包，产物已保存。"

    traffic_response = client.get(f"/api/cases/{case_id}/traffic")
    assert traffic_response.status_code == 200
    capture_payload = traffic_response.json()["capture"]
    assert capture_payload["source_path"] == stop_payload["artifact_path"]
    assert capture_payload["flow_count"] == 2
    assert capture_payload["suspicious_count"] == 1


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


def test_workspace_detail_marks_that_case_as_last_opened_for_startup_restore(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    sample_one = tmp_path / "one.apk"
    sample_two = tmp_path / "two.apk"
    sample_one.write_bytes(b"apk-one")
    sample_two.write_bytes(b"apk-two")
    fixture_jadx = Path("tests/fixtures/jadx_sources").resolve()
    static_analyzer = _make_static_analyzer(tmp_path=tmp_path, jadx_sources_dir=fixture_jadx)
    registry_path = tmp_path / "registry.json"
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            registry_path=registry_path,
            static_analyzer=static_analyzer,
        )
    )

    first = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample_one),
            "workspace_root": str(workspace_root),
            "title": "案件一",
        },
    )
    second = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample_two),
            "workspace_root": str(workspace_root),
            "title": "案件二",
        },
    )
    first_case_id = first.json()["case_id"]

    detail_response = client.get(f"/api/cases/{first_case_id}/workspace/detail")
    startup_response = client.get("/api/settings/startup")

    assert detail_response.status_code == 200
    assert startup_response.status_code == 200
    assert second.status_code == 201
    assert startup_response.json()["case_id"] == first_case_id
    assert startup_response.json()["title"] == "案件一"
    assert startup_response.json()["launch_view"] == "workspace"


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


def test_api_sees_controller_initialized_workspace_via_legacy_registry_path(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    workspace_root = tmp_path / "override-workspaces"
    expected_registry_path = tmp_path / "cache" / "gui" / "workspace-registry.json"

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
    case_root = Path(create_response.json()["workspace_root"])
    case_scripts_root = scripts_root / case_root.name
    case_scripts_root.mkdir(parents=True, exist_ok=True)
    (case_scripts_root / "ssl-okhttp.js").write_text("// ssl", encoding="utf-8")
    (case_scripts_root / "cipher-monitor.js").write_text("// crypto", encoding="utf-8")

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
    assert payload["runtime"] == {
        "execution_count": 0,
        "last_execution_run_id": None,
        "last_execution_mode": None,
        "last_executed_backend_key": None,
        "last_execution_status": None,
        "last_execution_stage": None,
        "last_execution_error_code": None,
        "last_execution_error_message": None,
        "last_execution_event_count": None,
        "last_execution_result_path": None,
        "last_execution_db_path": None,
        "last_execution_bundle_path": None,
        "last_report_path": None,
        "traffic_capture_source_path": None,
        "traffic_capture_summary_path": None,
        "traffic_capture_flow_count": None,
        "traffic_capture_suspicious_count": None,
        "live_traffic_status": "idle",
        "live_traffic_artifact_path": None,
        "live_traffic_message": None,
    }
    assert len(static_analyzer.calls) == 1


def test_workspace_detail_includes_runtime_summary_after_execution_and_traffic_import(tmp_path: Path) -> None:
    sample = tmp_path / "detail-runtime.apk"
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
            "title": "运行态摘要案件",
        },
    )
    case_id = create_response.json()["case_id"]

    method_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post(f"/api/cases/{case_id}/hook-plan/methods", json=method).status_code == 200
    execution_response = client.post(
        f"/api/cases/{case_id}/executions",
        json={"execution_mode": "fake_backend"},
    )
    assert execution_response.status_code == 202
    runtime_state = _wait_for_execution_completion(workspace_root / case_id / "workspace-runtime.json")
    report_response = client.post(f"/api/cases/{case_id}/reports/export")
    assert report_response.status_code == 200
    import_response = client.post(
        f"/api/cases/{case_id}/traffic/import",
        json={"har_path": str(Path("tests/fixtures/traffic/sample.har").resolve())},
    )
    assert import_response.status_code == 200

    detail_response = client.get(f"/api/cases/{case_id}/workspace/detail")

    assert detail_response.status_code == 200
    payload = detail_response.json()
    runtime = payload["runtime"]
    assert runtime["execution_count"] == 1
    assert runtime["last_execution_mode"] == "fake_backend"
    assert runtime["last_executed_backend_key"] == runtime_state["last_executed_backend_key"]
    assert runtime["last_execution_status"] == "completed"
    assert runtime["last_execution_error_code"] is None
    assert runtime["last_execution_error_message"] is None
    assert runtime["last_execution_event_count"] == runtime_state["last_execution_event_count"]
    assert runtime["last_execution_db_path"] == runtime_state["last_execution_db_path"]
    assert runtime["last_execution_bundle_path"] == runtime_state["last_execution_bundle_path"]
    assert runtime["last_report_path"] == report_response.json()["report_path"]
    assert runtime["traffic_capture_source_path"].endswith(str(Path("tests/fixtures/traffic/sample.har")))
    assert runtime["traffic_capture_summary_path"]
    assert runtime["traffic_capture_flow_count"] == 2
    assert runtime["traffic_capture_suspicious_count"] == 1


def test_workspace_events_replay_recent_execution_history(tmp_path: Path) -> None:
    sample = tmp_path / "events-demo.apk"
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
            "title": "事件回放案件",
        },
    )
    case_id = create_response.json()["case_id"]

    method_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post(f"/api/cases/{case_id}/hook-plan/methods", json=method).status_code == 200
    assert client.post(
        f"/api/cases/{case_id}/executions",
        json={"execution_mode": "fake_backend"},
    ).status_code == 202
    _wait_for_execution_completion(workspace_root / case_id / "workspace-runtime.json")

    events_response = client.get(f"/api/cases/{case_id}/workspace/events", params={"limit": 5})

    assert events_response.status_code == 200
    payload = events_response.json()
    assert payload["case_id"] == case_id
    assert payload["items"]
    assert len(payload["items"]) <= 5
    assert all(item["type"] == "execution.event" for item in payload["items"])
    assert all("payload" in item for item in payload["items"])


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
    assert methods_response.json() == {
        "items": [],
        "total": 0,
        "scope": "first_party",
        "available_scopes": ["first_party", "related_candidates", "all"],
    }


def test_workspace_methods_supports_switching_to_all_scope(tmp_path: Path) -> None:
    sample = tmp_path / "methods-all-scope.apk"
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
            "title": "全部方法范围案件",
        },
    )
    case_id = create_response.json()["case_id"]

    first_party_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "", "limit": 500, "scope": "first_party"},
    )
    all_scope_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "", "limit": 500, "scope": "all"},
    )

    assert first_party_response.status_code == 200
    assert all_scope_response.status_code == 200
    first_party_payload = first_party_response.json()
    all_scope_payload = all_scope_response.json()
    assert first_party_payload["scope"] == "first_party"
    assert all_scope_payload["scope"] == "all"
    assert first_party_payload["available_scopes"] == ["first_party", "related_candidates", "all"]
    assert all_scope_payload["available_scopes"] == ["first_party", "related_candidates", "all"]
    assert all_scope_payload["total"] >= first_party_payload["total"]


def test_workspace_methods_exposes_related_candidates_scope(tmp_path: Path) -> None:
    sample = tmp_path / "methods-related.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    sources_root = _write_related_candidate_sources(tmp_path)
    static_analyzer = _make_static_analyzer(tmp_path=tmp_path, jadx_sources_dir=sources_root)
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
            "title": "相关候选案件",
        },
    )
    case_id = create_response.json()["case_id"]

    first_party_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "", "limit": 20, "scope": "first_party"},
    )
    related_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "", "limit": 20, "scope": "related_candidates"},
    )
    all_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "", "limit": 20, "scope": "all"},
    )

    assert first_party_response.status_code == 200
    assert related_response.status_code == 200
    assert all_response.status_code == 200
    first_party_payload = first_party_response.json()
    related_payload = related_response.json()
    all_payload = all_response.json()

    assert related_payload["scope"] == "related_candidates"
    assert related_payload["available_scopes"] == ["first_party", "related_candidates", "all"]
    assert first_party_payload["total"] == 2
    assert related_payload["total"] == 4
    assert all_payload["total"] == 5
    related_class_names = [item["class_name"] for item in related_payload["items"]]
    assert related_class_names[:2] == ["com.demo.shell.UploadManager", "com.demo.shell.HomeActivity"]
    assert "okhttp3.OkHttpClient" in related_class_names
    assert "com.thirdparty.crypto.CipherHelper" in related_class_names
    assert "org.other.DebugHelper" not in related_class_names


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


def test_workspace_recommendations_supports_keyword_filter(tmp_path: Path) -> None:
    sample = tmp_path / "recommend-filter-demo.apk"
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
            "title": "推荐筛选案件",
        },
    )
    case_id = create_response.json()["case_id"]

    ssl_response = client.get(
        f"/api/cases/{case_id}/workspace/recommendations",
        params={"limit": 5, "query": "ssl"},
    )
    assert ssl_response.status_code == 200
    ssl_items = ssl_response.json()["items"]
    assert len(ssl_items) == 1
    assert ssl_items[0]["title"] == "OkHttp3 SSL Unpinning"
    assert "ssl" in [term.lower() for term in ssl_items[0]["matched_terms"]]

    empty_response = client.get(
        f"/api/cases/{case_id}/workspace/recommendations",
        params={"limit": 5, "query": "camera"},
    )
    assert empty_response.status_code == 200
    assert empty_response.json()["items"] == []


def test_workspace_traffic_import_persists_case_scoped_capture(tmp_path: Path) -> None:
    sample = tmp_path / "traffic-demo.apk"
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
            "title": "流量案件",
        },
    )
    case_id = create_response.json()["case_id"]
    case_root = Path(create_response.json()["workspace_root"])

    import_response = client.post(
        f"/api/cases/{case_id}/traffic/import",
        json={"har_path": str(Path("tests/fixtures/traffic/sample.har").resolve())},
    )

    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["case_id"] == case_id
    assert payload["flow_count"] == 2
    assert payload["suspicious_count"] == 1
    assert payload["source_path"].endswith(str(Path("tests/fixtures/traffic/sample.har")))
    assert payload["provenance"] == {
        "kind": "manual_har",
        "label": "手工 HAR 导入",
    }
    assert payload["summary"] == {
        "https_flow_count": 2,
        "matched_indicator_count": 2,
        "top_hosts": [
            {
                "host": "demo-c2.example",
                "flow_count": 1,
                "suspicious_count": 1,
                "https_flow_count": 1,
            },
            {
                "host": "cdn.example.org",
                "flow_count": 1,
                "suspicious_count": 0,
                "https_flow_count": 1,
            },
        ],
        "suspicious_hosts": [
            {
                "host": "demo-c2.example",
                "flow_count": 1,
                "suspicious_count": 1,
                "https_flow_count": 1,
            }
        ],
    }
    assert payload["flows"][0]["suspicious"] is True
    assert payload["flows"][0]["url"] == "https://demo-c2.example/api/upload"

    detail_response = client.get(f"/api/cases/{case_id}/traffic")
    assert detail_response.status_code == 200
    assert detail_response.json() == {"case_id": case_id, "capture": payload}

    runtime_payload = json.loads((case_root / "workspace-runtime.json").read_text(encoding="utf-8"))
    assert runtime_payload["traffic_capture_source_path"].endswith(str(Path("tests/fixtures/traffic/sample.har")))
    assert runtime_payload["traffic_capture_flow_count"] == 2
    assert runtime_payload["traffic_capture_suspicious_count"] == 1
    assert Path(runtime_payload["traffic_capture_summary_path"]).is_file()


def test_custom_script_detail_update_and_delete_apis_round_trip_and_sync_hook_plan(tmp_path: Path) -> None:
    sample = tmp_path / "custom-script-crud.apk"
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
            "title": "脚本 CRUD 案件",
        },
    )
    case_id = create_response.json()["case_id"]

    save_response = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "trace_login", "content": "send('v1');\n"},
    )
    assert save_response.status_code == 200
    script_id = save_response.json()["script_id"]

    detail_response = client.get(f"/api/cases/{case_id}/custom-scripts/{script_id}")
    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "script_id": script_id,
        "name": "trace_login",
        "script_path": save_response.json()["script_path"],
        "content": "send('v1');\n",
    }

    add_script_response = client.post(
        f"/api/cases/{case_id}/hook-plan/custom-scripts",
        json={"script_id": script_id},
    )
    assert add_script_response.status_code == 200
    assert add_script_response.json()["items"][0]["render_context"]["rendered_script"] == "send('v1');\n"

    update_response = client.put(
        f"/api/cases/{case_id}/custom-scripts/{script_id}",
        json={"name": "trace_login_v2", "content": "send('v2');\n"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "trace_login_v2"
    assert update_response.json()["script_path"].endswith("trace_login_v2.js")
    updated_script_id = update_response.json()["script_id"]

    updated_detail_response = client.get(f"/api/cases/{case_id}/custom-scripts/{updated_script_id}")
    assert updated_detail_response.status_code == 200
    assert updated_detail_response.json()["content"] == "send('v2');\n"

    list_response = client.get(f"/api/cases/{case_id}/custom-scripts")
    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()["items"]] == ["trace_login_v2"]

    refreshed_plan = client.get(f"/api/cases/{case_id}/hook-plan")
    assert refreshed_plan.status_code == 200
    assert refreshed_plan.json()["items"][0]["source"]["script_name"] == "trace_login_v2"
    assert refreshed_plan.json()["items"][0]["source"]["script_path"].endswith("trace_login_v2.js")
    assert refreshed_plan.json()["items"][0]["render_context"]["rendered_script"] == "send('v2');\n"

    delete_response = client.delete(f"/api/cases/{case_id}/custom-scripts/{updated_script_id}")
    assert delete_response.status_code == 204

    missing_after_delete = client.get(f"/api/cases/{case_id}/custom-scripts/{updated_script_id}")
    assert missing_after_delete.status_code == 404
    assert missing_after_delete.json()["detail"] == "Custom script not found"

    empty_list_response = client.get(f"/api/cases/{case_id}/custom-scripts")
    assert empty_list_response.status_code == 200
    assert empty_list_response.json()["items"] == []

    cleared_plan = client.get(f"/api/cases/{case_id}/hook-plan")
    assert cleared_plan.status_code == 200
    assert cleared_plan.json()["items"] == []


def test_workspace_route_uses_runtime_public_api_for_hook_plan(tmp_path: Path) -> None:
    registry_service = WorkspaceRegistryService(tmp_path / "registry.json")
    source = HookPlanSource.from_method(
        MethodIndexEntry(
            class_name="com.demo.net.Config",
            method_name="buildUploadUrl",
            parameter_types=("String",),
            return_type="String",
            is_constructor=False,
            overload_count=1,
            source_path="tests/fixtures/jadx_sources/com/demo/net/Config.java",
            line_hint=4,
        )
    )
    item = HookPlanItem(
        item_id="item-1",
        kind="method_hook",
        source_kind=source.source_kind or "selected_method",
        enabled=True,
        inject_order=1,
        target=MethodHookTarget(
            target_id="target-1",
            class_name="com.demo.net.Config",
            method_name="buildUploadUrl",
            parameter_types=("String",),
            return_type="String",
            source_origin=source.source_id,
        ),
        render_context={},
    )
    state = WorkspaceRuntimeState(
        case_id="case-001",
        workspace_root=tmp_path / "case-001",
        updated_at="2026-04-22T00:00:00+00:00",
        selected_hook_sources=(source,),
        rendered_hook_plan=HookPlan(items=(item,)),
    )

    class _RuntimeFacadeOnly:
        def get_hook_plan_view(self, case_id: str):
            assert case_id == "case-001"
            return SimpleNamespace(
                state=state,
                source_by_item_id={"item-1": source},
            )

        def get_state(self, case_id: str):  # pragma: no cover - should never be called
            raise AssertionError(f"route should use public hook-plan view API, not get_state({case_id!r})")

    app = FastAPI()
    app.include_router(
        build_workspace_router(
            registry_service=registry_service,
            default_workspace_root=tmp_path / "workspaces",
            workspace_runtime_service=_RuntimeFacadeOnly(),
        )
    )
    client = TestClient(app)

    response = client.get("/api/cases/case-001/hook-plan")

    assert response.status_code == 200
    assert response.json()["items"][0]["source"]["method"]["method_name"] == "buildUploadUrl"


def test_hook_plan_items_include_source_summary_without_positional_reconstruction(tmp_path: Path) -> None:
    sample = tmp_path / "hook-plan-source.apk"
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
            "title": "Hook 来源案件",
        },
    )
    case_id = create_response.json()["case_id"]

    method_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post(f"/api/cases/{case_id}/hook-plan/methods", json=method).status_code == 200
    save_script_response = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "trace-login", "content": "send('custom');"},
    )
    assert save_script_response.status_code == 200
    script_payload = save_script_response.json()
    assert (
        client.post(
            f"/api/cases/{case_id}/hook-plan/custom-scripts",
            json={"script_id": script_payload["script_id"]},
        ).status_code
        == 200
    )

    hook_plan_response = client.get(f"/api/cases/{case_id}/hook-plan")

    assert hook_plan_response.status_code == 200
    payload = hook_plan_response.json()
    assert len(payload["selected_hook_sources"]) == len(payload["items"])
    assert payload["items"][0]["source"]["kind"] == "method_hook"
    assert payload["items"][0]["source"]["method"]["method_name"] == "buildUploadUrl"
    assert payload["items"][1]["source"]["kind"] == "custom_script"
    assert payload["items"][1]["source"]["script_name"] == "trace-login"
    assert payload["items"][1]["source"]["script_path"].endswith("trace-login.js")


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
    static_analyzer = _make_static_analyzer(
        tmp_path=tmp_path,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
            environment_service=EnvironmentService(
                resolver=lambda name: f"/usr/bin/{name}" if name in {"adb", "frida", "mitmdump"} else None,
                module_resolver=lambda name: object() if name == "frida" else None,
            ),
            traffic_capture_command="mitmdump -w {output_path}",
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

    environment_response = client.get("/api/settings/environment")
    assert environment_response.status_code == 200
    ssl_template = environment_response.json()["live_capture"]["ssl_hook_guidance"]["suggested_template_entries"][0]

    add_template_response = client.post(f"/api/cases/{case_id}/hook-plan/templates", json=ssl_template)
    assert add_template_response.status_code == 200

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
    assert len(payload["items"]) == 4
    assert all("rendered_script" in item["render_context"] for item in payload["items"])
    runtime_state_path = case_root / "workspace-runtime.json"
    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    assert runtime_state["case_id"] == case_id
    assert len(runtime_state["selected_hook_sources"]) == 4
    assert len(runtime_state["rendered_hook_plan"]["items"]) == 4

    first_item_id = payload["items"][0]["item_id"]
    remove_response = client.delete(f"/api/cases/{case_id}/hook-plan/items/{first_item_id}")
    assert remove_response.status_code == 200
    assert len(remove_response.json()["items"]) == 3

    clear_response = client.delete(f"/api/cases/{case_id}/hook-plan")
    assert clear_response.status_code == 200
    assert clear_response.json()["items"] == []


def test_hook_plan_item_patch_toggles_enabled_and_reorders_items(tmp_path: Path) -> None:
    sample = tmp_path / "hook-plan-patch.apk"
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
            "title": "Hook Plan Patch 案件",
        },
    )
    case_id = create_response.json()["case_id"]

    methods_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "", "limit": 2},
    )
    first_method, second_method = methods_response.json()["items"][:2]
    assert client.post(f"/api/cases/{case_id}/hook-plan/methods", json=first_method).status_code == 200
    assert client.post(f"/api/cases/{case_id}/hook-plan/methods", json=second_method).status_code == 200

    initial_plan = client.get(f"/api/cases/{case_id}/hook-plan").json()
    first_item_id = initial_plan["items"][0]["item_id"]
    second_item_id = initial_plan["items"][1]["item_id"]

    disable_response = client.patch(
        f"/api/cases/{case_id}/hook-plan/items/{first_item_id}",
        json={"enabled": False},
    )
    assert disable_response.status_code == 200
    disabled_payload = disable_response.json()
    assert disabled_payload["items"][0]["enabled"] is False

    reorder_response = client.patch(
        f"/api/cases/{case_id}/hook-plan/items/{second_item_id}",
        json={"inject_order": 1},
    )
    assert reorder_response.status_code == 200
    reordered_payload = reorder_response.json()
    assert [item["item_id"] for item in reordered_payload["items"]] == [second_item_id, first_item_id]
    assert [item["inject_order"] for item in reordered_payload["items"]] == [1, 2]
    assert reordered_payload["items"][1]["enabled"] is False

    invalid_response = client.patch(
        f"/api/cases/{case_id}/hook-plan/items/{second_item_id}",
        json={"inject_order": 99},
    )
    assert invalid_response.status_code == 400
    assert invalid_response.json()["detail"] == "Hook plan order is out of range."


def test_hook_plan_refreshes_saved_custom_script_content(tmp_path: Path) -> None:
    sample = tmp_path / "refresh-script.apk"
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
            "title": "脚本刷新案件",
        },
    )
    case_id = create_response.json()["case_id"]

    save_response = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "trace_login", "content": "send('v1');\n"},
    )
    script_id = save_response.json()["script_id"]
    assert client.post(
        f"/api/cases/{case_id}/hook-plan/custom-scripts",
        json={"script_id": script_id},
    ).status_code == 200

    initial_plan = client.get(f"/api/cases/{case_id}/hook-plan")
    assert initial_plan.status_code == 200
    assert initial_plan.json()["items"][0]["render_context"]["rendered_script"] == "send('v1');\n"

    updated_save = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "trace_login", "content": "send('v2');\n"},
    )
    assert updated_save.status_code == 200

    refreshed_plan = client.get(f"/api/cases/{case_id}/hook-plan")
    assert refreshed_plan.status_code == 200
    assert refreshed_plan.json()["items"][0]["render_context"]["rendered_script"] == "send('v2');\n"

    reopened_client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=static_analyzer,
        )
    )
    reopened_plan = reopened_client.get(f"/api/cases/{case_id}/hook-plan")
    assert reopened_plan.status_code == 200
    assert reopened_plan.json()["items"][0]["render_context"]["rendered_script"] == "send('v2');\n"


def test_custom_script_detail_update_and_delete_routes(tmp_path: Path) -> None:
    sample = tmp_path / "custom-script-crud.apk"
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
            "title": "脚本 CRUD 案件",
        },
    )
    case_id = create_response.json()["case_id"]

    save_response = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "trace_login", "content": "send('v1');\n"},
    )
    script_id = save_response.json()["script_id"]
    assert client.post(
        f"/api/cases/{case_id}/hook-plan/custom-scripts",
        json={"script_id": script_id},
    ).status_code == 200

    detail_response = client.get(f"/api/cases/{case_id}/custom-scripts/{script_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["content"] == "send('v1');\n"

    update_response = client.put(
        f"/api/cases/{case_id}/custom-scripts/{script_id}",
        json={"name": "trace_login", "content": "send('v2');\n"},
    )
    assert update_response.status_code == 200
    updated_detail = client.get(f"/api/cases/{case_id}/custom-scripts/{script_id}")
    assert updated_detail.status_code == 200
    assert updated_detail.json()["content"] == "send('v2');\n"
    plan_response = client.get(f"/api/cases/{case_id}/hook-plan")
    assert plan_response.status_code == 200
    assert plan_response.json()["items"][0]["render_context"]["rendered_script"] == "send('v2');\n"

    delete_response = client.delete(f"/api/cases/{case_id}/custom-scripts/{script_id}")
    assert delete_response.status_code == 204
    scripts_response = client.get(f"/api/cases/{case_id}/custom-scripts")
    assert scripts_response.status_code == 200
    assert scripts_response.json()["items"] == []
    plan_after_delete = client.get(f"/api/cases/{case_id}/hook-plan")
    assert plan_after_delete.status_code == 200
    assert plan_after_delete.json()["items"] == []


def test_save_custom_script_returns_400_for_invalid_user_input(tmp_path: Path) -> None:
    sample = tmp_path / "invalid-script-name.apk"
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
            "title": "非法脚本名案件",
        },
    )
    case_id = create_response.json()["case_id"]

    save_response = client.post(
        f"/api/cases/{case_id}/custom-scripts",
        json={"name": "bad script name", "content": "send('oops');\n"},
    )

    assert save_response.status_code == 400
    assert save_response.json() == {
        "detail": "Script name can only contain letters, numbers, dot, dash, and underscore.",
    }


def test_custom_scripts_are_isolated_per_case(tmp_path: Path) -> None:
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

    first_sample = tmp_path / "first.apk"
    second_sample = tmp_path / "second.apk"
    first_sample.write_bytes(b"apk")
    second_sample.write_bytes(b"apk")
    first_case = client.post(
        "/api/cases/import",
        json={"sample_path": str(first_sample), "workspace_root": str(workspace_root), "title": "第一案件"},
    ).json()["case_id"]
    second_case = client.post(
        "/api/cases/import",
        json={"sample_path": str(second_sample), "workspace_root": str(workspace_root), "title": "第二案件"},
    ).json()["case_id"]

    assert client.post(
        f"/api/cases/{first_case}/custom-scripts",
        json={"name": "only-first", "content": "send('first');\n"},
    ).status_code == 200

    first_scripts = client.get(f"/api/cases/{first_case}/custom-scripts")
    second_scripts = client.get(f"/api/cases/{second_case}/custom-scripts")
    assert [item["name"] for item in first_scripts.json()["items"]] == ["only-first"]
    assert second_scripts.json()["items"] == []


def test_remove_hook_plan_item_preserves_unrenderable_selected_sources(tmp_path: Path) -> None:
    sample = tmp_path / "remove-hidden-source.apk"
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
            "title": "删除隐藏来源案件",
        },
    )
    case_id = create_response.json()["case_id"]
    case_root = Path(create_response.json()["workspace_root"])

    method_response = client.get(
        f"/api/cases/{case_id}/workspace/methods",
        params={"query": "upload", "limit": 1},
    )
    method = method_response.json()["items"][0]
    assert client.post(f"/api/cases/{case_id}/hook-plan/methods", json=method).status_code == 200

    runtime_state_path = case_root / "workspace-runtime.json"
    runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    runtime_state["selected_hook_sources"].append(
        {
            "source_id": "custom_script:/tmp/missing.js",
            "kind": "custom_script",
            "script_name": "broken-script",
        }
    )
    runtime_state_path.write_text(json.dumps(runtime_state, ensure_ascii=False, indent=2), encoding="utf-8")

    hook_plan_response = client.get(f"/api/cases/{case_id}/hook-plan")
    assert hook_plan_response.status_code == 200
    payload = hook_plan_response.json()
    assert len(payload["items"]) == 1

    remove_response = client.delete(f"/api/cases/{case_id}/hook-plan/items/{payload['items'][0]['item_id']}")

    assert remove_response.status_code == 200
    assert remove_response.json()["items"] == []
    reloaded_runtime_state = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    assert len(reloaded_runtime_state["selected_hook_sources"]) == 1
    assert reloaded_runtime_state["selected_hook_sources"][0]["source_id"] == "custom_script:/tmp/missing.js"
