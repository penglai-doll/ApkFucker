from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import json

from apk_hacker.application.services.custom_script_service import CustomScriptRecord, CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.services.hook_search import HookSearch
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def _empty_method_index() -> MethodIndex:
    return MethodIndex(classes=(), methods=())


def _empty_hook_plan() -> HookPlan:
    return HookPlan(items=())


@dataclass(frozen=True, slots=True)
class NavigationPage:
    title: str
    object_name: str


@dataclass(frozen=True, slots=True)
class WorkbenchState:
    sample_path: Path | None = None
    current_job: AnalysisJob | None = None
    static_inputs: StaticInputs | None = None
    method_index: MethodIndex = field(default_factory=_empty_method_index)
    visible_methods: tuple[MethodIndexEntry, ...] = ()
    selected_sources: tuple[HookPlanSource, ...] = ()
    hook_plan: HookPlan = field(default_factory=_empty_hook_plan)
    hook_events: tuple[HookEvent, ...] = ()
    custom_scripts: tuple[CustomScriptRecord, ...] = ()
    execution_mode: str = "fake_backend"
    selected_custom_script_path: Path | None = None
    custom_script_draft_name: str = ""
    custom_script_draft_content: str = ""
    search_query: str = ""
    run_count: int = 0
    summary_text: str = "No analysis run yet."


class WorkbenchController:
    def __init__(
        self,
        scripts_root: Path,
        db_root: Path,
        job_service: JobService | None = None,
        fixture_root: Path | None = None,
        jadx_sources_root: Path | None = None,
    ) -> None:
        self._fixture_root = fixture_root
        self._jadx_sources_root = jadx_sources_root
        self._scripts_root = scripts_root
        self._db_root = db_root
        self._analysis_output_root = db_root / "static-analysis"
        self._job_service = job_service or JobService()
        self._adapter = StaticAdapter()
        self._indexer = JavaMethodIndexer()
        self._search = HookSearch()
        self._hook_plan_service = HookPlanService()
        self._fake_backend = FakeExecutionBackend()
        self._custom_scripts = CustomScriptService(scripts_root)

    @property
    def demo_available(self) -> bool:
        return self._fixture_root is not None and self._jadx_sources_root is not None

    def load_demo_workspace(self, sample_path: Path) -> WorkbenchState:
        if not self.demo_available:
            raise RuntimeError("Demo workspace is not configured.")
        analysis_report = json.loads(
            (self._fixture_root / "sample_analysis.json").read_text(encoding="utf-8")  # type: ignore[operator]
        )
        callback_config = json.loads(
            (self._fixture_root / "sample_callback-config.json").read_text(encoding="utf-8")  # type: ignore[operator]
        )
        job = self._job_service.create_job(sample_path)
        static_inputs = self._adapter.adapt(
            sample_path=sample_path,
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={
                "analysis_report": self._fixture_root / "sample_analysis.json",  # type: ignore[operator]
                "callback_config": self._fixture_root / "sample_callback-config.json",  # type: ignore[operator]
                "jadx_sources": self._jadx_sources_root,
            },
        )
        method_index = self._indexer.build(self._jadx_sources_root)  # type: ignore[arg-type]
        custom_scripts = tuple(self._custom_scripts.discover())
        visible_methods = method_index.methods

        return WorkbenchState(
            sample_path=sample_path,
            current_job=job,
            static_inputs=static_inputs,
            method_index=method_index,
            visible_methods=visible_methods,
            custom_scripts=custom_scripts,
            custom_script_draft_name=custom_scripts[0].name if custom_scripts else "",
            custom_script_draft_content=self._custom_scripts.read_script(custom_scripts[0]) if custom_scripts else "",
            selected_custom_script_path=custom_scripts[0].script_path if custom_scripts else None,
            summary_text=f"Loaded demo workspace for {sample_path.name}.",
        )

    def load_sample_workspace(self, sample_path: Path) -> WorkbenchState:
        job, static_inputs, method_index = self._job_service.load_static_workspace(
            sample_path,
            output_dir=self._analysis_output_root,
        )
        custom_scripts = tuple(self._custom_scripts.discover())
        return WorkbenchState(
            sample_path=sample_path,
            current_job=job,
            static_inputs=static_inputs,
            method_index=method_index,
            visible_methods=method_index.methods,
            custom_scripts=custom_scripts,
            custom_script_draft_name=custom_scripts[0].name if custom_scripts else "",
            custom_script_draft_content=self._custom_scripts.read_script(custom_scripts[0]) if custom_scripts else "",
            selected_custom_script_path=custom_scripts[0].script_path if custom_scripts else None,
            summary_text=f"Static analysis finished for {sample_path.name}.",
        )

    def search_methods(self, state: WorkbenchState, query: str) -> WorkbenchState:
        normalized_query = query.strip()
        visible_methods = self._search.search(state.method_index, normalized_query)
        return replace(
            state,
            search_query=normalized_query,
            visible_methods=visible_methods,
        )

    def add_method_to_plan(self, state: WorkbenchState, method: MethodIndexEntry) -> WorkbenchState:
        source = HookPlanSource.from_method(method)
        if any(existing.source_id == source.source_id for existing in state.selected_sources):
            return state

        selected_sources = (*state.selected_sources, source)
        hook_plan = self._hook_plan_service.plan_for_sources(list(selected_sources))
        return replace(
            state,
            selected_sources=selected_sources,
            hook_plan=hook_plan,
            summary_text=f"Prepared {len(hook_plan.items)} planned hook item(s).",
        )

    def add_custom_script_to_plan(self, state: WorkbenchState, script: CustomScriptRecord) -> WorkbenchState:
        source = HookPlanSource.from_custom_script(script.name, str(script.script_path))
        if any(existing.source_id == source.source_id for existing in state.selected_sources):
            return replace(
                state,
                summary_text=f"Custom script {script.name} is already in the hook plan.",
            )

        selected_sources = (*state.selected_sources, source)
        hook_plan = self._hook_plan_service.plan_for_sources(list(selected_sources))
        return replace(
            state,
            selected_sources=selected_sources,
            hook_plan=hook_plan,
            summary_text=f"Prepared {len(hook_plan.items)} planned hook item(s).",
        )

    def select_custom_script(self, state: WorkbenchState, script: CustomScriptRecord | None) -> WorkbenchState:
        if script is None:
            return replace(
                state,
                selected_custom_script_path=None,
                custom_script_draft_name="",
                custom_script_draft_content="",
            )

        return replace(
            state,
            selected_custom_script_path=script.script_path,
            custom_script_draft_name=script.name,
            custom_script_draft_content=self._custom_scripts.read_script(script),
        )

    def save_custom_script(self, state: WorkbenchState, name: str, content: str) -> WorkbenchState:
        try:
            record = self._custom_scripts.save_script(name, content)
        except (OSError, ValueError) as exc:
            return replace(state, summary_text=f"Failed to save custom script: {exc}")

        custom_scripts = tuple(self._custom_scripts.discover())
        return replace(
            state,
            custom_scripts=custom_scripts,
            selected_custom_script_path=record.script_path,
            custom_script_draft_name=record.name,
            custom_script_draft_content=content,
            summary_text=f"Saved custom script {record.name}.",
        )

    def set_execution_mode(self, state: WorkbenchState, mode: str) -> WorkbenchState:
        return replace(state, execution_mode=mode)

    def run_analysis(self, state: WorkbenchState) -> WorkbenchState:
        if state.current_job is None:
            return replace(state, summary_text="Load a workspace before running analysis.")
        if not state.hook_plan.items:
            return replace(state, summary_text="Add at least one hook plan item first.")
        if state.execution_mode == "real_device":
            return replace(
                state,
                hook_events=(),
                summary_text="Real device execution is not available in this build yet.",
            )
        return self.run_fake_analysis(state)

    def run_fake_analysis(self, state: WorkbenchState) -> WorkbenchState:
        if state.current_job is None:
            return replace(state, summary_text="Load a workspace before running fake analysis.")
        if not state.hook_plan.items:
            return replace(state, summary_text="Add at least one hook plan item first.")

        events = self._fake_backend.execute(state.current_job.job_id, state.hook_plan)
        run_count = state.run_count + 1
        db_path = self._db_root / f"{state.current_job.job_id}-run-{run_count}.sqlite3"
        store = HookLogStore(db_path)
        for event in events:
            store.insert(event)
        rows = tuple(store.list_for_job(state.current_job.job_id))
        return replace(
            state,
            hook_events=rows,
            run_count=run_count,
            summary_text=f"Captured {len(rows)} event(s) from {len(state.hook_plan.items)} planned hook(s).",
        )
