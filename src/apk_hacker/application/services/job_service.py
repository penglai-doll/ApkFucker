from __future__ import annotations

from pathlib import Path

from apk_hacker.domain.models.job import AnalysisJob


class JobService:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}

    def create_job(self, input_target: Path) -> AnalysisJob:
        job = AnalysisJob.queued(str(input_target))
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> AnalysisJob:
        return self._jobs[job_id]
