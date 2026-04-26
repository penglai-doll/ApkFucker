from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import textwrap
import time

from fastapi.testclient import TestClient
import pytest

from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.interfaces.api_fastapi.app import build_app
from apk_hacker.interfaces.api_fastapi.traffic_capture_dispatcher import _split_command_template
from apk_hacker.static_engine.analyzer import StaticArtifacts


@pytest.mark.skipif(os.name != "nt", reason="Windows command splitting regression")
def test_live_capture_command_split_preserves_windows_paths() -> None:
    parts = _split_command_template(
        r'"C:\Users\zhong\Python311\python.exe" "C:\tmp\capture helper.py" {output_path}'
    )

    assert parts == [
        r"C:\Users\zhong\Python311\python.exe",
        r"C:\tmp\capture helper.py",
        "{output_path}",
    ]


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        return self.artifacts


def _make_static_analyzer(*, tmp_path: Path) -> _FakeStaticAnalyzer:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    return _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=tmp_path / "cache",
            report_dir=tmp_path / "cache" / "报告" / "sample",
            cache_dir=tmp_path / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=tmp_path / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=Path("tests/fixtures/jadx_sources").resolve(),
            jadx_project_dir=None,
        )
    )


def _create_case(*, client: TestClient, sample_path: Path, workspace_root: Path, title: str) -> tuple[str, Path]:
    create_response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample_path),
            "workspace_root": str(workspace_root),
            "title": title,
        },
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    return payload["case_id"], Path(payload["workspace_root"])


def _runtime_payload(case_root: Path) -> dict[str, object]:
    return json.loads((case_root / "workspace-runtime.json").read_text(encoding="utf-8"))


def _write_live_capture_script(tmp_path: Path, *, fixture_path: Path | None) -> Path:
    script_path = tmp_path / "fake_live_capture.py"
    fixture_literal = repr(str(fixture_path)) if fixture_path is not None else "None"
    script_path.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import shutil
            import signal
            import sys
            import time

            output_path = pathlib.Path(sys.argv[1])
            fixture_path = {fixture_literal}

            def _flush_and_exit(*_args):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if fixture_path is not None:
                    shutil.copyfile(pathlib.Path(fixture_path), output_path)
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, _flush_and_exit)
            if hasattr(signal, "SIGBREAK"):
                signal.signal(signal.SIGBREAK, _flush_and_exit)

            while True:
                time.sleep(0.1)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return script_path


def _write_live_capture_preview_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "fake_live_capture_preview.py"
    script_path.write_text(
        textwrap.dedent(
            """
            import json
            import os
            import pathlib
            import signal
            import sys
            import time

            output_path = pathlib.Path(sys.argv[1])
            preview_path = pathlib.Path(sys.argv[2])

            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview_path.write_text(
                json.dumps(
                    {
                        "flow_id": "preview-1",
                        "timestamp": "2026-04-19T10:00:00Z",
                        "method": "GET",
                        "url": "https://cdn.example.org/app.js",
                        "status_code": 200,
                        "matched_indicators": [],
                        "suspicious": False,
                    }
                )
                + "\\n"
                + json.dumps(
                    {
                        "flow_id": "preview-2",
                        "timestamp": "2026-04-19T10:00:02Z",
                        "method": "POST",
                        "url": "https://demo-c2.example/api/upload",
                        "status_code": 202,
                        "matched_indicators": ["demo-c2.example"],
                        "suspicious": True,
                    }
                )
                + "\\n",
                encoding="utf-8",
            )

            def _flush_and_exit(*_args):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    "{\\"log\\": {\\"version\\": \\"1.2\\", \\"creator\\": {\\"name\\": \\"test\\", \\"version\\": \\"1.0\\"}, \\"entries\\": []}}",
                    encoding="utf-8",
                )
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, _flush_and_exit)
            if hasattr(signal, "SIGBREAK"):
                signal.signal(signal.SIGBREAK, _flush_and_exit)

            while True:
                time.sleep(0.1)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return script_path


def test_live_traffic_status_reports_unavailable_when_command_is_not_configured(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("APKHACKER_TRAFFIC_CAPTURE_COMMAND", raising=False)
    sample = tmp_path / "traffic-live-missing-command.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=_make_static_analyzer(tmp_path=tmp_path),
            environment_service=EnvironmentService(resolver=lambda _name: None),
        )
    )
    case_id, _case_root = _create_case(
        client=client,
        sample_path=sample,
        workspace_root=workspace_root,
        title="未配置抓包命令",
    )

    response = client.get(f"/api/cases/{case_id}/traffic/live")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": case_id,
        "status": "unavailable",
        "session_id": None,
        "artifact_path": None,
        "output_path": None,
        "preview_path": None,
        "message": "未配置实时抓包命令，请设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND。",
    }


def test_live_traffic_start_and_stop_imports_capture_and_persists_runtime(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sample = tmp_path / "traffic-live-success.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    fixture_path = Path("tests/fixtures/traffic/sample.har").resolve()
    live_script = _write_live_capture_script(tmp_path, fixture_path=fixture_path)
    monkeypatch.setenv(
        "APKHACKER_TRAFFIC_CAPTURE_COMMAND",
        f'"{sys.executable}" "{live_script}" {{output_path}}',
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=_make_static_analyzer(tmp_path=tmp_path),
            environment_service=EnvironmentService(resolver=lambda _name: None),
        )
    )
    case_id, case_root = _create_case(
        client=client,
        sample_path=sample,
        workspace_root=workspace_root,
        title="实时抓包导入",
    )

    start_response = client.post(f"/api/cases/{case_id}/traffic/live/start")

    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["case_id"] == case_id
    assert start_payload["status"] == "running"
    assert start_payload["artifact_path"].endswith(".har")
    assert start_payload["message"] == "已开始实时抓包。"

    running_runtime = _runtime_payload(case_root)
    assert running_runtime["live_traffic_capture_status"] == "running"
    assert running_runtime["live_traffic_capture_output_path"] == start_payload["artifact_path"]
    assert running_runtime["live_traffic_capture_message"] == "已开始实时抓包。"

    status_response = client.get(f"/api/cases/{case_id}/traffic/live")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "running"
    time.sleep(0.2)

    stop_response = client.post(f"/api/cases/{case_id}/traffic/live/stop")

    assert stop_response.status_code == 200
    stop_payload = stop_response.json()
    assert stop_payload["case_id"] == case_id
    assert stop_payload["status"] == "stopped"
    assert stop_payload["artifact_path"] == start_payload["artifact_path"]
    assert stop_payload["message"] == "已停止实时抓包，产物已保存。"

    stopped_runtime = _runtime_payload(case_root)
    assert stopped_runtime["live_traffic_capture_status"] == "stopped"
    assert stopped_runtime["live_traffic_capture_output_path"] == start_payload["artifact_path"]
    assert stopped_runtime["live_traffic_capture_message"] == "已停止实时抓包，产物已保存。"
    assert stopped_runtime["traffic_capture_source_path"] == start_payload["artifact_path"]
    assert stopped_runtime["traffic_capture_flow_count"] == 2
    assert stopped_runtime["traffic_capture_suspicious_count"] == 1
    assert Path(stopped_runtime["traffic_capture_summary_path"]).is_file()
    assert (case_root / "evidence" / "traffic" / "traffic-flows.sqlite3").is_file()

    traffic_response = client.get(f"/api/cases/{case_id}/traffic")
    assert traffic_response.status_code == 200
    capture_payload = traffic_response.json()["capture"]
    assert capture_payload["source_path"] == start_payload["artifact_path"]
    assert capture_payload["provenance"] == {
        "kind": "live_capture",
        "label": "实时抓包自动导入",
    }
    assert capture_payload["flow_schema"] == "traffic-flow.v1"
    assert capture_payload["flows"][0]["schema_version"] == "traffic-flow.v1"
    assert capture_payload["flows"][0]["capture_id"].startswith("capture-")
    assert capture_payload["flows"][0]["host"] == "demo-c2.example"
    assert capture_payload["flows"][0]["path"] == "/api/upload"


def test_live_traffic_stop_returns_clear_message_when_output_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sample = tmp_path / "traffic-live-missing-output.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    live_script = _write_live_capture_script(tmp_path, fixture_path=None)
    monkeypatch.setenv(
        "APKHACKER_TRAFFIC_CAPTURE_COMMAND",
        f'"{sys.executable}" "{live_script}" {{output_path}}',
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=_make_static_analyzer(tmp_path=tmp_path),
            environment_service=EnvironmentService(resolver=lambda _name: None),
        )
    )
    case_id, case_root = _create_case(
        client=client,
        sample_path=sample,
        workspace_root=workspace_root,
        title="实时抓包缺失产物",
    )

    start_response = client.post(f"/api/cases/{case_id}/traffic/live/start")
    assert start_response.status_code == 200
    time.sleep(0.2)

    stop_response = client.post(f"/api/cases/{case_id}/traffic/live/stop")

    assert stop_response.status_code == 200
    payload = stop_response.json()
    assert payload["case_id"] == case_id
    assert payload["status"] == "stopped"
    assert payload["artifact_path"] is not None
    assert payload["message"] == "已停止实时抓包，但未找到预期产物文件。"

    runtime_payload = _runtime_payload(case_root)
    assert runtime_payload["live_traffic_capture_status"] == "stopped"
    assert runtime_payload["live_traffic_capture_message"] == "已停止实时抓包，但未找到预期产物文件。"
    assert runtime_payload["traffic_capture_source_path"] is None
    assert runtime_payload["traffic_capture_summary_path"] is None
    assert runtime_payload["traffic_capture_flow_count"] is None
    assert runtime_payload["traffic_capture_suspicious_count"] is None


def test_live_traffic_preview_returns_recent_requests_while_running(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sample = tmp_path / "traffic-live-preview.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    live_script = _write_live_capture_preview_script(tmp_path)
    monkeypatch.setenv(
        "APKHACKER_TRAFFIC_CAPTURE_COMMAND",
        f'"{sys.executable}" "{live_script}" {{output_path}} {{preview_path}}',
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=_make_static_analyzer(tmp_path=tmp_path),
            environment_service=EnvironmentService(resolver=lambda _name: None),
        )
    )
    case_id, _case_root = _create_case(
        client=client,
        sample_path=sample,
        workspace_root=workspace_root,
        title="实时抓包预览",
    )

    start_response = client.post(f"/api/cases/{case_id}/traffic/live/start")
    assert start_response.status_code == 200
    time.sleep(0.2)

    preview_response = client.get(f"/api/cases/{case_id}/traffic/live/preview")

    assert preview_response.status_code == 200
    payload = preview_response.json()
    assert payload["case_id"] == case_id
    assert payload["status"] == "running"
    assert payload["preview_path"].endswith(".ndjson")
    assert payload["truncated"] is False
    assert [item["flow_id"] for item in payload["items"]] == ["preview-1", "preview-2"]
    assert payload["items"][1]["url"] == "https://demo-c2.example/api/upload"
    assert payload["items"][1]["suspicious"] is True
    assert payload["items"][1]["matched_indicators"] == ["demo-c2.example"]

    stop_response = client.post(f"/api/cases/{case_id}/traffic/live/stop")
    assert stop_response.status_code == 200


def test_live_traffic_environment_and_command_placeholders_follow_saved_runtime_settings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    sample = tmp_path / "traffic-live-custom-port.apk"
    sample.write_bytes(b"apk")
    workspace_root = tmp_path / "workspaces"
    recorded_args_path = tmp_path / "capture-args.json"
    live_script = tmp_path / "capture_args.py"
    live_script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import signal
            import sys
            import time

            output_path = pathlib.Path(sys.argv[1])
            recorded_args_path = pathlib.Path({str(recorded_args_path)!r})
            payload = {{
                "listen_host": sys.argv[2],
                "listen_port": sys.argv[3],
            }}
            recorded_args_path.write_text(json.dumps(payload), encoding="utf-8")

            def _flush_and_exit(*_args):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    "{{\\"log\\": {{\\"version\\": \\"1.2\\", \\"creator\\": {{\\"name\\": \\"test\\", \\"version\\": \\"1.0\\"}}, \\"entries\\": []}}}}",
                    encoding="utf-8",
                )
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, _flush_and_exit)
            if hasattr(signal, "SIGBREAK"):
                signal.signal(signal.SIGBREAK, _flush_and_exit)

            while True:
                time.sleep(0.1)
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "APKHACKER_TRAFFIC_CAPTURE_COMMAND",
        f'"{sys.executable}" "{live_script}" {{output_path}} {{listen_host}} {{listen_port}}',
    )
    client = TestClient(
        build_app(
            default_workspace_root=workspace_root,
            static_analyzer=_make_static_analyzer(tmp_path=tmp_path),
            environment_service=EnvironmentService(resolver=lambda _name: None),
        )
    )
    case_id, _case_root = _create_case(
        client=client,
        sample_path=sample,
        workspace_root=workspace_root,
        title="自定义抓包监听地址",
    )

    update_response = client.put(
        "/api/settings/runtime",
        json={
            "live_capture_listen_host": "127.0.0.1",
            "live_capture_listen_port": "9091",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["live_capture_listen_host"] == "127.0.0.1"
    assert update_response.json()["live_capture_listen_port"] == "9091"

    environment_response = client.get("/api/settings/environment")

    assert environment_response.status_code == 200
    assert environment_response.json()["live_capture"]["listen_host"] == "127.0.0.1"
    assert environment_response.json()["live_capture"]["listen_port"] == 9091

    start_response = client.post(f"/api/cases/{case_id}/traffic/live/start")

    assert start_response.status_code == 200
    time.sleep(0.2)
    recorded_payload = json.loads(recorded_args_path.read_text(encoding="utf-8"))
    assert recorded_payload == {
        "listen_host": "127.0.0.1",
        "listen_port": "9091",
    }

    stop_response = client.post(f"/api/cases/{case_id}/traffic/live/stop")
    assert stop_response.status_code == 200
