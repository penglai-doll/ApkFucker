# APKHacker Refactor Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge APKHacker around stable normalized artifacts and a decomposed runtime facade without breaking the existing workspace workflow.

**Architecture:** Keep the existing `domain/application/infrastructure/interfaces/static_engine` structure, preserve the current FastAPI + React/Tauri workspace loop, and refactor by extracting focused application services behind `workspace_runtime_service.py`. Use `StaticInputs` as the compatibility layer while formalizing normalized static artifacts as the stable schema foundation.

**Tech Stack:** Python 3.11, pytest, FastAPI, React/Tauri, SQLite, existing Frida/ADB execution backends, Jinja2 template rendering.

---

## File Structure

### Files to create
- `src/apk_hacker/application/services/workspace_hook_plan_service.py` — Hook source selection, plan item mutation, rerender orchestration
- `src/apk_hacker/application/services/workspace_execution_service.py` — execution routing, preflight, run history, result persistence orchestration
- `src/apk_hacker/application/services/workspace_traffic_service.py` — HAR import, traffic summary persistence, live-capture state updates, traffic store integration seam
- `src/apk_hacker/application/services/workspace_report_service.py` — report export coordination
- `src/apk_hacker/infrastructure/persistence/traffic_flow_store.py` — first SQLite persistence boundary for traffic flows
- `tests/application/test_workspace_hook_plan_service.py`
- `tests/application/test_workspace_execution_service.py`
- `tests/application/test_workspace_traffic_service.py`
- `tests/application/test_workspace_report_service.py`
- `tests/infrastructure/test_traffic_flow_store.py`

### Files to modify
- `README.md`
- `src/apk_hacker/application/services/job_service.py`
- `src/apk_hacker/application/services/static_adapter.py`
- `src/apk_hacker/application/services/static_result_normalizer.py`
- `src/apk_hacker/application/services/workspace_state_service.py`
- `src/apk_hacker/application/services/workspace_runtime_service.py`
- `src/apk_hacker/application/services/workspace_runtime_state.py`
- `src/apk_hacker/application/services/hook_plan_service.py`
- `src/apk_hacker/application/services/traffic_capture_service.py`
- `src/apk_hacker/domain/models/hook_plan.py`
- `src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- `src/apk_hacker/interfaces/api_fastapi/routes_traffic.py`
- `src/apk_hacker/infrastructure/templates/script_renderer.py`
- `tests/application/test_static_adapter.py`
- `tests/application/test_hook_plan_service.py`
- `tests/application/test_workspace_runtime_state.py`
- `tests/interfaces/test_fastapi_workspace.py`
- `tests/interfaces/test_fastapi_traffic_live.py`

### Likely validation targets
- `uv run pytest -q`
- `uv run pytest tests/application/test_static_adapter.py tests/application/test_hook_plan_service.py tests/application/test_workspace_runtime_state.py tests/application/test_workspace_hook_plan_service.py tests/application/test_workspace_execution_service.py tests/application/test_workspace_traffic_service.py tests/application/test_workspace_report_service.py tests/interfaces/test_fastapi_workspace.py tests/interfaces/test_fastapi_traffic_live.py tests/infrastructure/test_traffic_flow_store.py -q`
- `npm run typecheck:web`
- `npm run test:web -- --run`
- `cargo check --manifest-path src-tauri/Cargo.toml` (only if Tauri-facing contracts need verification)

---

### Task 1: Converge docs and lock the architectural mainline

**Files:**
- Modify: `README.md`
- Reference: `docs/superpowers/specs/2026-04-22-apkhacker-refactor-convergence-design.md`

- [ ] **Step 1: Write the failing documentation assertion checklist**

```text
Expected README conditions:
- The primary architecture is `src/apk_hacker/domain|application|infrastructure|interfaces|static_engine`
- `static_engine` is described as a legacy/compatibility static-analysis entrypoint
- No section presents `core/rules/ai/report/sandbox/orchestrator.py` as the main implementation track
- The runtime hotspot and convergence goal are described in terms of workspace runtime decomposition
```

- [ ] **Step 2: Inspect the current conflicting README sections**

Run:
```bash
python - <<'PY'
from pathlib import Path
text = Path('README.md').read_text(encoding='utf-8')
for needle in ['core/', 'rules/', 'ai/', 'static_engine', 'workspace_runtime_service']:
    if needle in text:
        print(needle)
PY
```
Expected: detect which architecture descriptions need rewriting.

- [ ] **Step 3: Rewrite README architecture sections to match the convergence design**

```md
## Architecture

APKHacker evolves within a single repository structure:

```text
src/apk_hacker/
  domain/
  application/
  infrastructure/
  interfaces/
  static_engine/
```

- `static_engine` is the compatibility entrypoint for the legacy static pipeline.
- `application` owns use-case orchestration for workspace import, Hook planning, execution, traffic, and reporting.
- `workspace_runtime_service.py` is being reduced to a facade over focused runtime services.
```
```

- [ ] **Step 4: Verify the README no longer advertises a competing top-level architecture**

Run:
```bash
python - <<'PY'
from pathlib import Path
text = Path('README.md').read_text(encoding='utf-8')
assert 'core/ rules/ ai/ report/ sandbox/ orchestrator.py' not in text
assert 'static_engine' in text
assert 'workspace_runtime_service.py' in text
print('README architecture text verified')
PY
```
Expected: `README architecture text verified`

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: converge apkhacker architecture docs"
```

### Task 2: Finish normalized static artifact coverage and regression tests

**Files:**
- Modify: `src/apk_hacker/application/services/job_service.py`
- Modify: `src/apk_hacker/application/services/static_adapter.py`
- Modify: `src/apk_hacker/application/services/static_result_normalizer.py`
- Test: `tests/application/test_static_adapter.py`
- Test: `tests/application/test_mvp_flow.py`
- Test: `tests/static_engine/test_static_analyzer.py`

- [ ] **Step 1: Write failing tests for normalized artifact paths and payloads**

```python
def test_job_service_load_static_workspace_bundle_exposes_normalized_artifacts(tmp_path: Path) -> None:
    bundle = JobService(static_analyzer=fake_analyzer).load_static_workspace_bundle(sample_path, output_dir=tmp_path)
    assert bundle.static_result is not None
    assert bundle.artifact_manifest is not None
    assert bundle.static_inputs.artifact_paths.artifact_manifest is not None
    assert bundle.static_inputs.artifact_paths.static_result is not None
    assert bundle.static_inputs.artifact_paths.findings_jsonl is not None
    assert bundle.static_inputs.artifact_paths.evidence_jsonl is not None
    assert bundle.static_inputs.artifact_paths.method_index_jsonl is not None
    assert bundle.static_inputs.artifact_paths.class_index_jsonl is not None
```

- [ ] **Step 2: Run the focused static tests to confirm current gaps**

Run:
```bash
uv run pytest tests/application/test_static_adapter.py tests/application/test_mvp_flow.py tests/static_engine/test_static_analyzer.py -q
```
Expected: at least one failure or missing assertion proving normalized artifact coverage is not fully enforced.

- [ ] **Step 3: Make `JobService` and `StaticResultNormalizer` guarantee the normalized artifact set**

```python
static_inputs = replace(
    static_inputs,
    artifact_paths=coerce_artifact_paths(
        {
            **static_inputs.artifact_paths.__dict__,
            'artifact_manifest': normalized.manifest_path,
            'static_result': normalized.static_result_path,
            'findings_jsonl': normalized.findings_path,
            'evidence_jsonl': normalized.evidence_path,
            'method_index_jsonl': normalized.method_index_path,
            'class_index_jsonl': normalized.class_index_path,
        }
    ),
)
```

- [ ] **Step 4: Verify the normalized artifacts are written and tests pass**

Run:
```bash
uv run pytest tests/application/test_static_adapter.py tests/application/test_mvp_flow.py tests/static_engine/test_static_analyzer.py -q
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apk_hacker/application/services/job_service.py \
  src/apk_hacker/application/services/static_adapter.py \
  src/apk_hacker/application/services/static_result_normalizer.py \
  tests/application/test_static_adapter.py \
  tests/application/test_mvp_flow.py \
  tests/static_engine/test_static_analyzer.py
git commit -m "feat: finalize normalized static artifact outputs"
```

### Task 3: Extract Hook-plan orchestration from runtime service

**Files:**
- Create: `src/apk_hacker/application/services/workspace_hook_plan_service.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_service.py`
- Modify: `src/apk_hacker/application/services/workspace_state_service.py`
- Test: `tests/application/test_workspace_hook_plan_service.py`
- Test: `tests/application/test_hook_plan_service.py`

- [ ] **Step 1: Write failing tests for Hook-plan workspace operations behind a dedicated service**

```python
def test_workspace_hook_plan_service_adds_method_source_and_rerenders_plan(tmp_path: Path) -> None:
    service = WorkspaceHookPlanService(state_service=WorkspaceStateService(), hook_plan_service=HookPlanService())
    state = build_default_runtime_state('case-001', tmp_path / 'case-001')
    method = MethodIndexEntry(
        class_name='com.demo.net.Config',
        method_name='buildUploadUrl',
        parameter_types=('String',),
        return_type='String',
        is_constructor=False,
        overload_count=1,
        source_path='tests/fixtures/jadx_sources/com/demo/net/Config.java',
        line_hint=4,
    )
    updated = service.add_method_source(state, method)
    assert len(updated.selected_hook_sources) == 1
    assert updated.rendered_hook_plan.items[0].source_kind == 'selected_method'
```

- [ ] **Step 2: Run Hook-plan tests to verify the missing service boundary**

Run:
```bash
uv run pytest tests/application/test_hook_plan_service.py tests/application/test_workspace_hook_plan_service.py -q
```
Expected: fail because `WorkspaceHookPlanService` does not yet exist.

- [ ] **Step 3: Implement `WorkspaceHookPlanService` and route all Hook-source mutations through it**

```python
class WorkspaceHookPlanService:
    def __init__(self, hook_plan_service: HookPlanService | None = None) -> None:
        self._hook_plan_service = hook_plan_service or HookPlanService()

    def rerender(self, state: WorkspaceRuntimeState) -> WorkspaceRuntimeState:
        plan = self._hook_plan_service.plan_for_sources(list(state.selected_hook_sources), previous_plan=state.rendered_hook_plan)
        return replace(state, rendered_hook_plan=plan)
```
```

- [ ] **Step 4: Update `workspace_runtime_service.py` to delegate Hook-plan behavior**

```python
self._workspace_hook_plan_service = workspace_hook_plan_service or WorkspaceHookPlanService(
    hook_plan_service=self._hook_plan_service,
)

state = self._workspace_hook_plan_service.add_method_source(state, method)
state = self._state_service.save(state)
return state
```

- [ ] **Step 5: Re-run the Hook-plan test set**

Run:
```bash
uv run pytest tests/application/test_hook_plan_service.py tests/application/test_workspace_hook_plan_service.py tests/application/test_workspace_runtime_state.py -q
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apk_hacker/application/services/workspace_hook_plan_service.py \
  src/apk_hacker/application/services/workspace_runtime_service.py \
  src/apk_hacker/application/services/workspace_state_service.py \
  tests/application/test_workspace_hook_plan_service.py \
  tests/application/test_hook_plan_service.py \
  tests/application/test_workspace_runtime_state.py
git commit -m "refactor: extract workspace hook plan service"
```

### Task 4: Extract traffic orchestration and add the SQLite persistence seam

**Files:**
- Create: `src/apk_hacker/application/services/workspace_traffic_service.py`
- Create: `src/apk_hacker/infrastructure/persistence/traffic_flow_store.py`
- Modify: `src/apk_hacker/application/services/traffic_capture_service.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_service.py`
- Modify: `src/apk_hacker/interfaces/api_fastapi/routes_traffic.py`
- Test: `tests/application/test_workspace_traffic_service.py`
- Test: `tests/infrastructure/test_traffic_flow_store.py`
- Test: `tests/interfaces/test_fastapi_traffic_live.py`

- [ ] **Step 1: Write failing tests for flow persistence and workspace traffic coordination**

```python
def test_traffic_flow_store_persists_imported_har_flows(tmp_path: Path) -> None:
    store = TrafficFlowStore(tmp_path / 'flows.sqlite3')
    store.replace_capture('capture-001', flows)
    assert len(store.list_for_capture('capture-001')) == len(flows)
```

```python
def test_workspace_traffic_service_import_har_updates_runtime_state(tmp_path: Path) -> None:
    updated = service.import_har(state, har_path)
    assert updated.traffic_capture_summary_path is not None
    assert updated.traffic_capture_flow_count == 3
```

- [ ] **Step 2: Run the traffic-focused test targets to confirm the missing pieces**

Run:
```bash
uv run pytest tests/application/test_workspace_traffic_service.py tests/infrastructure/test_traffic_flow_store.py tests/interfaces/test_fastapi_traffic_live.py -q
```
Expected: fail because the store/service boundary does not exist yet.

- [ ] **Step 3: Implement `TrafficFlowStore` with a minimal replace/list API**

```python
class TrafficFlowStore:
    def replace_capture(self, capture_id: str, flows: Sequence[TrafficFlowSummary]) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute('DELETE FROM traffic_flows WHERE capture_id = ?', (capture_id,))
            conn.executemany(
                'INSERT INTO traffic_flows (capture_id, flow_id, method, url, status_code, mime_type, request_preview, response_preview, suspicious) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                [
                    (
                        capture_id,
                        flow.flow_id,
                        flow.method,
                        flow.url,
                        flow.status_code,
                        flow.mime_type,
                        flow.request_preview,
                        flow.response_preview,
                        int(flow.suspicious),
                    )
                    for flow in flows
                ],
            )

    def list_for_capture(self, capture_id: str) -> list[TrafficFlowSummary]:
        return self._load_capture_rows(capture_id)
```

- [ ] **Step 4: Implement `WorkspaceTrafficService` and delegate HAR import through it**

```python
class WorkspaceTrafficService:
    def import_har(self, state: WorkspaceRuntimeState, har_path: Path) -> WorkspaceRuntimeState:
        capture = self._traffic_capture_service.import_har(
            har_path=har_path,
            output_root=state.workspace_root / 'evidence' / 'traffic',
        )
        capture_id = har_path.stem
        self._traffic_flow_store.replace_capture(capture_id, capture.flows)
        return replace(
            state,
            traffic_capture_source_path=har_path,
            traffic_capture_summary_path=state.workspace_root / 'evidence' / 'traffic' / 'traffic-capture.json',
            traffic_capture_flow_count=capture.flow_count,
            traffic_capture_suspicious_count=capture.suspicious_count,
        )
```

- [ ] **Step 5: Re-run the traffic tests**

Run:
```bash
uv run pytest tests/application/test_workspace_traffic_service.py tests/infrastructure/test_traffic_flow_store.py tests/interfaces/test_fastapi_traffic_live.py -q
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apk_hacker/application/services/workspace_traffic_service.py \
  src/apk_hacker/infrastructure/persistence/traffic_flow_store.py \
  src/apk_hacker/application/services/traffic_capture_service.py \
  src/apk_hacker/application/services/workspace_runtime_service.py \
  src/apk_hacker/interfaces/api_fastapi/routes_traffic.py \
  tests/application/test_workspace_traffic_service.py \
  tests/infrastructure/test_traffic_flow_store.py \
  tests/interfaces/test_fastapi_traffic_live.py
git commit -m "refactor: extract workspace traffic service"
```

### Task 5: Extract report export orchestration

**Files:**
- Create: `src/apk_hacker/application/services/workspace_report_service.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_service.py`
- Test: `tests/application/test_workspace_report_service.py`
- Test: `tests/application/test_report_export_service.py`

- [ ] **Step 1: Write the failing test for report export through a dedicated workspace service**

```python
def test_workspace_report_service_exports_report_and_updates_runtime_state(tmp_path: Path) -> None:
    updated, report = service.export_report(state, record)
    assert updated.last_report_path == report.path
    assert report.path.exists()
```

- [ ] **Step 2: Run the report-focused tests to verify the missing boundary**

Run:
```bash
uv run pytest tests/application/test_report_export_service.py tests/application/test_workspace_report_service.py -q
```
Expected: fail because `WorkspaceReportService` does not exist yet.

- [ ] **Step 3: Implement report export coordination behind `WorkspaceReportService`**

```python
class WorkspaceReportService:
    def export(self, state: WorkspaceRuntimeState, record: WorkspaceInspectionRecord) -> tuple[WorkspaceRuntimeState, ExportableReport]:
        report = self._report_export_service.export(
            case_id=record.case_id,
            workspace_root=record.workspace_root,
            static_inputs=record.static_inputs,
            runtime_state=state,
        )
        return replace(state, last_report_path=report.path), report
```

- [ ] **Step 4: Delegate report export from `workspace_runtime_service.py`**

```python
updated_state, report = self._workspace_report_service.export(state, record)
self._state_service.save(updated_state)
return report
```

- [ ] **Step 5: Re-run the report tests**

Run:
```bash
uv run pytest tests/application/test_report_export_service.py tests/application/test_workspace_report_service.py -q
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apk_hacker/application/services/workspace_report_service.py \
  src/apk_hacker/application/services/workspace_runtime_service.py \
  tests/application/test_workspace_report_service.py \
  tests/application/test_report_export_service.py
git commit -m "refactor: extract workspace report service"
```

### Task 6: Extract execution orchestration and reduce runtime service to a facade

**Files:**
- Create: `src/apk_hacker/application/services/workspace_execution_service.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_service.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_state.py`
- Test: `tests/application/test_workspace_execution_service.py`
- Test: `tests/application/test_execution_runtime.py`
- Test: `tests/application/test_workspace_runtime_state.py`

- [ ] **Step 1: Write failing tests for execution orchestration behind a dedicated service**

```python
def test_workspace_execution_service_records_successful_run_metadata(tmp_path: Path) -> None:
    result = service.execute(state, record, options)
    assert result.state.last_execution_status == 'completed'
    assert result.state.last_execution_run_id is not None
    assert result.state.last_execution_db_path is not None
```

- [ ] **Step 2: Run execution-focused tests to expose the missing seam**

Run:
```bash
uv run pytest tests/application/test_execution_runtime.py tests/application/test_workspace_execution_service.py tests/application/test_workspace_runtime_state.py -q
```
Expected: fail because `WorkspaceExecutionService` does not exist yet.

- [ ] **Step 3: Implement `WorkspaceExecutionService` by moving routing, backend env, and result-persistence logic out of runtime service**

```python
class WorkspaceExecutionService:
    def execute(self, state: WorkspaceRuntimeState, record: WorkspaceInspectionRecord, options: ExecutionRuntimeOptions | None) -> ExecutionResult:
        routing = resolve_execution_routing(record.static_inputs, runtime_options=options)
        backend = build_execution_backend(routing)
        events = backend.execute(request)
        return ExecutionResult(
            state=updated_state,
            execution_mode=routing.mode,
            executed_backend_key=routing.backend_key,
            events=events,
        )
```

- [ ] **Step 4: Keep `workspace_runtime_service.py` as a thin facade over state, Hook plan, traffic, report, and execution services**

```python
class WorkspaceRuntimeService:
    def execute(self, case_id: str, runtime_options: ExecutionRuntimeOptions | None = None) -> ExecutionResult:
        state = self.get_state(case_id)
        result = self._workspace_execution_service.execute(state, record, runtime_options)
        self._state_service.save(result.state)
        return result
```

- [ ] **Step 5: Re-run the execution and runtime-state tests**

Run:
```bash
uv run pytest tests/application/test_execution_runtime.py tests/application/test_workspace_execution_service.py tests/application/test_workspace_runtime_state.py -q
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/apk_hacker/application/services/workspace_execution_service.py \
  src/apk_hacker/application/services/workspace_runtime_service.py \
  src/apk_hacker/application/services/workspace_runtime_state.py \
  tests/application/test_workspace_execution_service.py \
  tests/application/test_execution_runtime.py \
  tests/application/test_workspace_runtime_state.py
git commit -m "refactor: extract workspace execution service"
```

### Task 7: Remove FastAPI dependence on runtime-service internals

**Files:**
- Modify: `src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_service.py`
- Test: `tests/interfaces/test_fastapi_workspace.py`

- [ ] **Step 1: Write the failing route test for public Hook-plan access**

```python
def test_workspace_route_uses_runtime_public_api_for_hook_plan(client) -> None:
    response = client.get('/api/cases/case-001/workspace/hook-plan')
    assert response.status_code == 200
    assert 'items' in response.json()
```

- [ ] **Step 2: Run the FastAPI workspace tests**

Run:
```bash
uv run pytest tests/interfaces/test_fastapi_workspace.py -q
```
Expected: fail if route helpers still depend on private runtime-service members after the runtime refactor.

- [ ] **Step 3: Add explicit runtime-facade helpers and update the route layer to use them**

```python
def get_hook_plan_view(self, case_id: str) -> HookPlanView:
    state = self.get_state(case_id)
    source_by_item_id = self._workspace_hook_plan_service.source_by_item_id(state)
    return HookPlanView(state=state, source_by_item_id=source_by_item_id)
```

- [ ] **Step 4: Re-run the FastAPI workspace tests**

Run:
```bash
uv run pytest tests/interfaces/test_fastapi_workspace.py -q
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apk_hacker/interfaces/api_fastapi/routes_workspace.py \
  src/apk_hacker/application/services/workspace_runtime_service.py \
  tests/interfaces/test_fastapi_workspace.py
git commit -m "refactor: remove workspace route runtime internals coupling"
```

### Task 8: Preserve expanded Hook-plan metadata through model, state, service, and API boundaries

**Files:**
- Modify: `src/apk_hacker/domain/models/hook_plan.py`
- Modify: `src/apk_hacker/application/services/hook_plan_service.py`
- Modify: `src/apk_hacker/application/services/workspace_runtime_state.py`
- Modify: `src/apk_hacker/infrastructure/templates/script_renderer.py`
- Modify: `tests/application/test_hook_plan_service.py`
- Modify: `tests/application/test_workspace_runtime_state.py`

- [ ] **Step 1: Write failing tests for metadata round-tripping**

```python
def test_workspace_runtime_state_round_trips_hook_plan_metadata(tmp_path: Path) -> None:
    source = HookPlanSource.from_template(
        template_id='ssl.okhttp3_unpin',
        template_name='OkHttp3 SSL Unpinning',
        plugin_id='builtin.ssl-okhttp3-unpin',
        source_kind='framework_plugin',
    )
    state = WorkspaceRuntimeState(
        case_id='case-003',
        workspace_root=tmp_path / 'case-003',
        updated_at='2026-04-22T00:00:00+00:00',
        selected_hook_sources=(source,),
        rendered_hook_plan=HookPlanService().plan_for_sources([source]),
    )
    saved = save_workspace_runtime_state(state, state_path)
    loaded = load_workspace_runtime_state(
        case_id='case-003',
        workspace_root=tmp_path / 'case-003',
        path=state_path,
        hook_plan_service=HookPlanService(),
    )
    assert loaded.selected_hook_sources[0].source_kind == source.source_kind
    assert loaded.rendered_hook_plan.items[0].template_id == 'ssl.okhttp3_unpin'
```

- [ ] **Step 2: Run Hook-plan metadata tests**

Run:
```bash
uv run pytest tests/application/test_hook_plan_service.py tests/application/test_workspace_runtime_state.py -q
```
Expected: fail if metadata is dropped or not asserted today.

- [ ] **Step 3: Update models and renderers so metadata survives plan creation and rerendering**

```python
return HookPlanItem(
    item_id=item_id,
    kind='template_hook',
    source_kind=source.source_kind or 'framework_plugin',
    enabled=True,
    inject_order=inject_order,
    target=None,
    render_context={
        'template_id': template_id,
        'template_name': template_name,
    },
    plugin_id=plugin_id,
    template_id=template_id,
    evidence_ids=source.method.evidence if source.method else (),
    tags=source.method.tags if source.method else (),
)
```

- [ ] **Step 4: Re-run metadata tests**

Run:
```bash
uv run pytest tests/application/test_hook_plan_service.py tests/application/test_workspace_runtime_state.py -q
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apk_hacker/domain/models/hook_plan.py \
  src/apk_hacker/application/services/hook_plan_service.py \
  src/apk_hacker/application/services/workspace_runtime_state.py \
  src/apk_hacker/infrastructure/templates/script_renderer.py \
  tests/application/test_hook_plan_service.py \
  tests/application/test_workspace_runtime_state.py
git commit -m "feat: preserve hook plan metadata through runtime state"
```

### Task 9: Run repository-level verification and stabilize

**Files:**
- Validation only across files modified in Tasks 1-8
- Validation only: repo root

- [ ] **Step 1: Run the full backend suite**

Run:
```bash
uv run pytest -q
```
Expected: PASS

- [ ] **Step 2: Run the web typecheck**

Run:
```bash
npm run typecheck:web
```
Expected: PASS

- [ ] **Step 3: Run the web tests**

Run:
```bash
npm run test:web -- --run
```
Expected: PASS

- [ ] **Step 4: Run Tauri validation if contracts touched the desktop shell**

Run:
```bash
cargo check --manifest-path src-tauri/Cargo.toml
```
Expected: PASS or skipped if no shell-facing contract changed.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "refactor: converge runtime services and static schemas"
```
