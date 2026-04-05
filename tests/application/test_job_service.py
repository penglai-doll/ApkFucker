from pathlib import Path

from apk_hacker.application.services.job_service import JobService


def test_job_service_creates_job_record() -> None:
    service = JobService()

    job = service.create_job(Path("/samples/demo.apk"))

    assert job.status == "queued"
    assert job.input_target == "/samples/demo.apk"
    assert service.get_job(job.job_id) == job
