from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import json

from apk_hacker.application.services.custom_script_service import CustomScriptRecord, CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
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
    selected_methods: tuple[MethodIndexEntry, ...] = ()
    hook_plan: HookPlan = field(default_factory=_empty_hook_plan)
    hook_events: tuple[HookEvent, ...] = ()
    custom_scripts: tuple[CustomScriptRecord, ...] = ()
    search_query: str = ""
    run_count: int = 0
    summary_text: str = "No analysis run yet."


class WorkbenchController:
    def __init__(
        self,
        fixture_root: Path,
        jadx_sources_root: Path,
        scripts_root: Path,
        db_root: Path,
    ) -> None:
        self._fixture_root = fixture_root
        self._jadx_sources_root = jadx_sources_root
        self._scripts_root = scripts_root
        self._db_root = db_root
        self._job_service = JobService()
        self._adapter = StaticAdapter()
        self._indexer = JavaMethodIndexer()
        self._search = HookSearch()
        self._hook_plan_service = HookPlanService()
        self._fake_backend = FakeExecutionBackend()
        self._custom_scripts = CustomScriptService(scripts_root)

    def load_demo_workspace(self, sample_path: Path) -> WorkbenchState:
        analysis_report = json.loads(
            (self._fixture_root / "sample_analysis.json").read_text(encoding="utf-8")
        )
        callback_config = json.loads(
            (self._fixture_root / "sample_callback-config.json").read_text(encoding="utf-8")
        )
        job = self._job_service.create_job(sample_path)
        static_inputs = self._adapter.adapt(
            sample_path=sample_path,
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={
                "analysis_report": self._fixture_root / "sample_analysis.json",
                "callback_config": self._fixture_root / "sample_callback-config.json",
                "jadx_sources": self._jadx_sources_root,
            },
        )
        method_index = self._indexer.build(self._jadx_sources_root)
        custom_scripts = tuple(self._custom_scripts.discover())
        visible_methods = method_index.methods

        return WorkbenchState(
            sample_path=sample_path,
            current_job=job,
            static_inputs=static_inputs,
            method_index=method_index,
            visible_methods=visible_methods,
            custom_scripts=custom_scripts,
            summary_text=f"Loaded demo workspace for {sample_path.name}.",
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
        if any(self._same_method(existing, method) for existing in state.selected_methods):
            return state

        selected_methods = (*state.selected_methods, method)
        hook_plan = self._hook_plan_service.plan_for_methods(list(selected_methods))
        return replace(
            state,
            selected_methods=selected_methods,
            hook_plan=hook_plan,
            summary_text=f"Prepared {len(hook_plan.items)} planned hook item(s).",
        )

    def run_fake_analysis(self, state: WorkbenchState) -> WorkbenchState:
        if state.current_job is None:
            return replace(state, summary_text="Load a workspace before running fake analysis.")
        if not state.hook_plan.items:
            return replace(state, summary_text="Add at least one method to the hook plan first.")

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

    @staticmethod
    def _same_method(left: MethodIndexEntry, right: MethodIndexEntry) -> bool:
        return (
            left.class_name == right.class_name
            and left.method_name == right.method_name
            and left.parameter_types == right.parameter_types
            and left.source_path == right.source_path
        )
