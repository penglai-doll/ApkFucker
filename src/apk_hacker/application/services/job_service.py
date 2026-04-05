from __future__ import annotations

from pathlib import Path

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


class JobService:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}

    def create_job(self, input_target: Path) -> AnalysisJob:
        job = AnalysisJob.queued(str(input_target))
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> AnalysisJob:
        return self._jobs[job_id]

    def run_fake_flow(
        self,
        analysis_report: dict,
        callback_config: dict,
        jadx_sources_dir: Path,
        db_path: Path,
    ) -> tuple:
        static_inputs = StaticAdapter().adapt(
            sample_path=Path("/samples/demo.apk"),
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={"analysis_report": "cache/demo/analysis.json"},
        )
        index = JavaMethodIndexer().build(jadx_sources_dir)
        selected = tuple(method for method in index.methods if method.method_name == "buildUploadUrl")
        plan = HookPlanService().plan_for_methods(list(selected))
        events = FakeExecutionBackend().execute("job-1", plan)
        store = HookLogStore(db_path)
        for event in events:
            store.insert(event)
        return static_inputs, plan, store.list_for_job("job-1")
