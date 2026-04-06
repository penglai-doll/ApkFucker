from pathlib import Path
import json

from apk_hacker.static_engine.analyzer import StaticArtifacts
from apk_hacker.application.services.job_service import JobService


def test_job_service_creates_job_record() -> None:
    service = JobService()

    job = service.create_job(Path("/samples/demo.apk"))

    assert job.status == "queued"
    assert job.input_target == "/samples/demo.apk"
    assert service.get_job(job.job_id) == job


def test_job_service_runs_fake_flow(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs")
    analysis = json.loads((fixture_root / "sample_analysis.json").read_text(encoding="utf-8"))
    callback = json.loads((fixture_root / "sample_callback-config.json").read_text(encoding="utf-8"))

    service = JobService()

    static_inputs, plan, rows = service.run_fake_flow(
        analysis_report=analysis,
        callback_config=callback,
        jadx_sources_dir=Path("tests/fixtures/jadx_sources"),
        db_path=tmp_path / "hooks.sqlite3",
    )

    assert static_inputs.package_name == "com.demo.shell"
    assert len(plan.items) == 2
    assert len(rows) == 2


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts
        self.calls: list[tuple[Path, Path | None, str]] = []

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        self.calls.append((target_path, output_dir, mode))
        return self.artifacts


def test_job_service_loads_static_workspace_from_real_artifacts(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"

    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    service = JobService(static_analyzer=fake_analyzer)

    job, static_inputs, method_index = service.load_static_workspace(
        sample_path,
        output_dir=output_root,
    )

    assert job.input_target == str(sample_path)
    assert static_inputs.package_name == "com.demo.shell"
    assert static_inputs.artifact_paths.analysis_report == (fixture_root / "sample_analysis.json")
    assert static_inputs.artifact_paths.static_markdown_report == (output_root / "报告" / "sample" / "report.md")
    assert static_inputs.artifact_paths.static_docx_report == (output_root / "报告" / "sample" / "report.docx")
    assert len(method_index.methods) == 5
    assert fake_analyzer.calls == [(sample_path, output_root, "auto")]


def test_job_service_returns_empty_index_when_jadx_sources_are_missing(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"

    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=None,
            jadx_project_dir=None,
        )
    )
    service = JobService(static_analyzer=fake_analyzer)

    _, _, method_index = service.load_static_workspace(sample_path, output_dir=output_root)

    assert method_index.methods == ()


def test_job_service_raises_clear_error_for_missing_artifacts(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"

    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=tmp_path / "missing-analysis.json",
            callback_config_json=tmp_path / "missing-callback.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=None,
            jadx_project_dir=None,
        )
    )
    service = JobService(static_analyzer=fake_analyzer)

    try:
        service.load_static_workspace(sample_path, output_dir=output_root)
    except FileNotFoundError as exc:
        assert "analysis artifact" in str(exc).lower()
    else:
        raise AssertionError("Expected FileNotFoundError for missing static artifacts")
