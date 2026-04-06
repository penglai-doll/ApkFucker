from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.indexes import MethodIndex
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore
from apk_hacker.static_engine.analyzer import StaticAnalyzer, StaticArtifacts


def _empty_method_index() -> MethodIndex:
    return MethodIndex(classes=(), methods=())


def _load_json_artifact(path: Path, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label} artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class SupportsStaticAnalyze(Protocol):
    def analyze(
        self,
        target_path: Path,
        output_dir: Path | None = None,
        mode: str = "auto",
    ) -> StaticArtifacts: ...


class JobService:
    def __init__(
        self,
        static_analyzer: SupportsStaticAnalyze | None = None,
        static_adapter: StaticAdapter | None = None,
        method_indexer: JavaMethodIndexer | None = None,
        hook_plan_service: HookPlanService | None = None,
        fake_backend: FakeExecutionBackend | None = None,
    ) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._static_analyzer = static_analyzer or StaticAnalyzer()
        self._static_adapter = static_adapter or StaticAdapter()
        self._method_indexer = method_indexer or JavaMethodIndexer()
        self._hook_plan_service = hook_plan_service or HookPlanService()
        self._fake_backend = fake_backend or FakeExecutionBackend()

    def create_job(self, input_target: Path) -> AnalysisJob:
        job = AnalysisJob.queued(str(input_target))
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> AnalysisJob:
        return self._jobs[job_id]

    def load_static_workspace(
        self,
        sample_path: Path,
        output_dir: Path | None = None,
        mode: str = "auto",
    ) -> tuple[AnalysisJob, StaticInputs, MethodIndex]:
        job = self.create_job(sample_path)
        artifacts = self._static_analyzer.analyze(sample_path, output_dir=output_dir, mode=mode)

        analysis_report = _load_json_artifact(artifacts.analysis_json, "analysis")
        callback_config = _load_json_artifact(artifacts.callback_config_json, "callback config")
        static_inputs = self._static_adapter.adapt(
            sample_path=sample_path,
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={
                "analysis_report": artifacts.analysis_json,
                "callback_config": artifacts.callback_config_json,
                "noise_log": artifacts.noise_log_json,
                "jadx_sources": artifacts.jadx_sources_dir,
                "jadx_project": artifacts.jadx_project_dir,
                "static_markdown_report": artifacts.report_dir / "report.md",
                "static_docx_report": artifacts.report_dir / "report.docx",
            },
        )
        method_index = (
            self._method_indexer.build(artifacts.jadx_sources_dir)
            if artifacts.jadx_sources_dir is not None
            else _empty_method_index()
        )
        return job, static_inputs, method_index

    def run_fake_flow(
        self,
        analysis_report: dict,
        callback_config: dict,
        jadx_sources_dir: Path,
        db_path: Path,
    ) -> tuple:
        static_inputs = self._static_adapter.adapt(
            sample_path=Path("/samples/demo.apk"),
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={"analysis_report": "cache/demo/analysis.json"},
        )
        index = self._method_indexer.build(jadx_sources_dir)
        selected = tuple(method for method in index.methods if method.method_name == "buildUploadUrl")
        plan = self._hook_plan_service.plan_for_methods(list(selected))
        events = self._fake_backend.execute(
            ExecutionRequest(
                job_id="job-1",
                plan=plan,
                package_name=static_inputs.package_name,
                sample_path=Path("/samples/demo.apk"),
            )
        )
        store = HookLogStore(db_path)
        for event in events:
            store.insert(event)
        return static_inputs, plan, store.list_for_job("job-1")
