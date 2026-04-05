from pathlib import Path
import json

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
