from pathlib import Path
import json

import apk_hacker.interfaces.cli.main as cli_main
from apk_hacker.application.services.job_service import JobService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.infrastructure.execution.backend import ExecutionBackend
from apk_hacker.interfaces.cli.main import execute_cli, parse_args
from apk_hacker.application.services.workbench_controller import WorkbenchController
from apk_hacker.static_engine.analyzer import StaticArtifacts
from pytest import raises


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        del target_path, output_dir, mode
        return self.artifacts


class _FakeRealBackend(ExecutionBackend):
    def __init__(self, events: tuple[HookEvent, ...]) -> None:
        self.events = events
        self.calls: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        self.calls.append(request)
        return self.events


class _FailingReportExportService:
    def export_markdown(self, report, output_path: Path) -> Path:
        del report, output_path
        raise OSError("disk full")


def _build_controller(tmp_path: Path, real_backend: ExecutionBackend | None = None) -> WorkbenchController:
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
    execution_backends = {"real_device": real_backend} if real_backend is not None else None
    return WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        execution_backends=execution_backends,
    )


def test_cli_parse_args_supports_run_options() -> None:
    args = parse_args(
        [
            "--sample",
            "/samples/demo.apk",
            "--method-query",
            "buildUploadUrl",
            "--method-query",
            "submitTelemetry",
            "--add-top-recommendations",
            "2",
            "--execution-mode",
            "fake_backend",
            "--run",
        ]
    )

    assert args.sample == Path("/samples/demo.apk")
    assert args.method_query == ["buildUploadUrl", "submitTelemetry"]
    assert args.add_top_recommendations == 2
    assert args.execution_mode == "fake_backend"
    assert args.run is True


def test_execute_cli_returns_static_summary_without_run(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")

    result = execute_cli(
        parse_args(
            [
                "--sample",
                str(sample_path),
                "--method-query",
                "buildUploadUrl",
            ]
        ),
        controller=controller,
    )

    assert result["package_name"] == "com.demo.shell"
    assert result["selected_plan_count"] == 1
    assert result["event_count"] == 0
    assert result["selected_targets"][0]["method_name"] == "buildUploadUrl"


def test_execute_cli_runs_fake_backend_and_returns_execution_artifacts(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")

    result = execute_cli(
        parse_args(
            [
                "--sample",
                str(sample_path),
                "--method-query",
                "buildUploadUrl",
                "--execution-mode",
                "fake_backend",
                "--run",
            ]
        ),
        controller=controller,
    )

    assert result["event_count"] == 1
    assert result["execution_mode"] == "fake_backend"
    assert result["last_execution_db_path"].endswith(".sqlite3")
    assert result["events"][0]["method_name"] == "buildUploadUrl"


def test_execute_cli_runs_real_backend_and_returns_bundle_path(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    real_backend = _FakeRealBackend(
        (
            HookEvent(
                timestamp="2026-04-06T00:00:00Z",
                job_id="job-1",
                event_type="execution_bundle",
                source="real",
                class_name="backend",
                method_name="artifacts",
                arguments=(
                    str(tmp_path / "execution-runs" / "job-1"),
                    str(tmp_path / "execution-runs" / "job-1" / "plan.json"),
                    str(tmp_path / "execution-runs" / "job-1" / "stdout.log"),
                    str(tmp_path / "execution-runs" / "job-1" / "stderr.log"),
                ),
                return_value="python helper.py",
                stacktrace="",
                raw_payload={},
            ),
            HookEvent(
                timestamp="2026-04-06T00:00:01Z",
                job_id="job-1",
                event_type="runtime_env",
                source="real",
                class_name="cli.real",
                method_name="configured",
                arguments=("serial-123",),
                return_value="ok",
                stacktrace="",
                raw_payload={},
            ),
        )
    )
    controller = _build_controller(tmp_path, real_backend=real_backend)

    result = execute_cli(
        parse_args(
            [
                "--sample",
                str(sample_path),
                "--method-query",
                "buildUploadUrl",
                "--execution-mode",
                "real_device",
                "--run",
            ]
        ),
        controller=controller,
    )

    assert result["execution_mode"] == "real_device"
    assert result["event_count"] == 1
    assert result["last_execution_bundle_path"].endswith("job-1")
    assert result["events"][0]["event_type"] == "runtime_env"


def test_execute_cli_can_export_markdown_report(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")

    result = execute_cli(
        parse_args(
            [
                "--sample",
                str(sample_path),
                "--method-query",
                "buildUploadUrl",
                "--export-report",
            ]
        ),
        controller=controller,
    )

    report_path = Path(result["exported_report_path"])
    content = report_path.read_text(encoding="utf-8")

    assert report_path.exists()
    assert report_path.name.endswith("-report.md")
    assert "com.demo.shell" in content
    assert "buildUploadUrl" in content


def test_execute_cli_raises_when_report_export_fails(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)
    controller._report_export = _FailingReportExportService()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")

    with raises(RuntimeError, match="disk full"):
        execute_cli(
            parse_args(
                [
                    "--sample",
                    str(sample_path),
                    "--method-query",
                    "buildUploadUrl",
                    "--export-report",
                ]
            ),
            controller=controller,
        )


def test_execute_cli_main_emits_json_summary(tmp_path: Path, capsys) -> None:
    controller = _build_controller(tmp_path)
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")

    execute_cli(
        parse_args(
            [
                "--sample",
                str(sample_path),
                "--method-query",
                "buildUploadUrl",
            ]
        ),
        controller=controller,
    )
    payload = capsys.readouterr()
    assert payload.out == ""
    assert payload.err == ""


def test_cli_main_prints_json_payload_and_returns_zero(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli_main,
        "execute_cli",
        lambda args: {
            "job_id": "job-1",
            "sample_path": str(args.sample),
            "summary": "ok",
        },
    )

    exit_code = cli_main.main(["--sample", "/tmp/demo.apk"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "job_id": "job-1",
        "sample_path": "/tmp/demo.apk",
        "summary": "ok",
    }


def test_cli_main_prints_json_error_and_returns_nonzero(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli_main, "execute_cli", lambda args: (_ for _ in ()).throw(RuntimeError("boom")))

    exit_code = cli_main.main(["--sample", "/tmp/demo.apk"])
    payload = capsys.readouterr()

    assert exit_code == 1
    assert payload.out == ""
    assert json.loads(payload.err) == {"error": "boom"}
