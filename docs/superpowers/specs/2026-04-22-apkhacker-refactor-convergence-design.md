# APKHacker Refactor Convergence Design

**Date:** 2026-04-22
**Scope:** Refactor track B — convergence-first, pushing toward P1 without destabilizing the existing workspace loop.

## Goal

Stabilize APKHacker around its existing working product chain instead of introducing a second architecture. This refactor keeps the current FastAPI + React/Tauri workspace intact while making two foundational improvements:

1. Standardize static-analysis artifacts into stable schemas that future features can build on.
2. Split the oversized runtime orchestration layer into focused services so Hook planning, execution, traffic, and reporting can evolve independently.

## Current Reality

The repository already has a functioning product chain:

`WorkspaceService -> JobService -> StaticAnalyzer -> StaticAdapter -> MethodIndexer -> HookPlanService -> WorkspaceRuntimeService -> FastAPI -> React/Tauri`

This means the correct refactor strategy is not a rewrite. The codebase already contains:

- Stable top-level layers under `src/apk_hacker/domain`, `application`, `infrastructure`, `interfaces`, and `static_engine`
- Existing workspace artifacts such as `workspace.json`, `workspace-runtime.json`, `executions/run-*`, `reports/*.md`, and `evidence/traffic/traffic-capture.json`
- An existing Hook planning chain through `method_indexer.py`, `offline_rule_engine.py`, `hook_advisor.py`, and `hook_plan_service.py`
- Existing dynamic execution support through fake/real backends and Frida/ADB helper tools
- Existing traffic import and live-capture support

The major architectural hotspots are:

- `src/apk_hacker/application/services/workspace_runtime_service.py`
- `src/apk_hacker/application/services/workspace_runtime_state.py`
- `src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`

## Non-Goals

This refactor does **not**:

- Replace the current FastAPI + React/Tauri workspace with a new UI architecture
- Fully replace the existing execution backend model with a new `DeviceBackend` system in one pass
- Fully modularize the legacy static-analysis pipeline in this round
- Expand AI-specific modules before the underlying schemas are stable
- Perform a large frontend redesign ahead of backend contract convergence

## Architecture Direction

APKHacker continues to use a single architectural mainline:

```text
src/apk_hacker/
  domain/
  application/
  infrastructure/
  interfaces/
  static_engine/
```

The repository should stop describing a competing top-level architecture such as `core/ rules/ ai/ report/ sandbox/ orchestrator.py` as the primary future direction. Legacy static analysis remains available through `static_engine`, but `static_engine` is a compatibility and integration layer, not the long-term home for every static capability.

## Design Principles

### 1. Converge around the existing workspace loop

The current end-to-end flow must remain intact:

- import sample
- inspect static summary
- search methods
- generate Hook plan
- execute
- import or inspect traffic
- export report

### 2. Schema first, capability second

Stable intermediate data comes before broader feature expansion. The priority schemas for this round are:

- `ArtifactManifest`
- `StaticResult`
- `Finding`
- `Evidence`
- Hook plan metadata continuity
- initial traffic persistence boundaries

### 3. Migration over replacement

The refactor should prefer adapters, facades, and normalization over destructive rewrites. Existing legacy static outputs, current templates, and current fake/real execution backends remain in use during the transition.

### 4. Backend convergence before frontend redesign

The frontend should follow stabilized contracts rather than force the backend into premature UI-driven changes.

## Refactor Scope for This Round

This round follows the convergence-first option (track B):

### Required

- Unify architecture documentation around the real repository structure
- Complete and verify normalized static artifacts
- Reduce `workspace_runtime_service.py` to a coordination/facade layer
- Split runtime responsibilities into focused application services
- Remove API-layer dependence on runtime-service internals
- Carry expanded Hook plan metadata through state, services, and API

### Stretch

- Establish a first traffic persistence store (`flows.sqlite3`) or at minimum the storage interface and integration seam

### Deferred

- Full template registry system
- Full device abstraction replacement
- Full dynamic-event model replacement
- AI-specific expansion
- Large frontend refactors

## Data Model Strategy

### Static-analysis normalization

The existing `StaticInputs` model remains the minimal workspace-facing input for compatibility. In parallel, the refactor formalizes a richer normalized output used as the basis for future static, dynamic, and AI features.

The normalized static output set is:

- `artifact-manifest.json`
- `static-result.v1.json`
- `findings.jsonl`
- `evidence.jsonl`
- `method-index.jsonl`
- `class-index.jsonl`

`JobService.load_static_workspace_bundle()` should continue to return `StaticInputs` for the current workspace workflow while also writing normalized artifacts and exposing them through `artifact_paths`.

### Stable models

This round adopts the following models as the canonical normalized static layer:

- `ArtifactManifest`
- `ArtifactRef`
- `StaticResult`
- `Finding`
- `Evidence`

The practical contract is:

- `StaticInputs` = compatibility and minimum working input for the existing workspace
- `StaticResult` = long-term structured basis for downstream capabilities

### Hook plan continuity

The Hook plan model should remain API-compatible while carrying richer metadata through the stack:

- `source_kind`
- `template_id`
- `plugin_id`
- `evidence_ids`
- `tags`

This does not require a complete template registry in this round. It does require that state serialization, plan services, and API responses preserve these fields.

### Traffic persistence

Traffic currently behaves primarily as a summary artifact. This round introduces a persistence seam so traffic can become first-class evidence later. The minimum acceptable result is an initial `traffic_flow_store.py` boundary and a path for HAR-imported flows to persist beyond summary-only JSON.

## Service Decomposition

### `workspace_runtime_service.py`

After refactor, this service becomes a facade/orchestration layer. It should:

- resolve the workspace record/state for a case
- delegate Hook plan operations to a Hook plan-specific service
- delegate execution operations to an execution-specific service
- delegate traffic operations to a traffic-specific service
- delegate report export to a report-specific service
- provide stable public methods used by FastAPI routes

It should no longer directly own large blocks of state serialization, traffic import details, report-export details, or plan-editing internals.

### `workspace_state_service.py`

Responsibilities:

- resolve `workspace-runtime.json` path
- load/save runtime state
- provide default state creation
- centralize compatibility handling around persisted state

### `workspace_hook_plan_service.py`

Responsibilities:

- manage selected Hook sources
- add/remove/update/reorder Hook plan items
- rerender plans
- unify method-based, template-based, and custom-script sources

Dependencies:

- `HookPlanService`
- `CustomScriptService`

### `workspace_execution_service.py`

Responsibilities:

- preflight and execution routing
- execution backend env construction
- execution result handling
- run history persistence updates
- hook-log/result-bundle path management

Dependencies:

- `execution_runtime.py`
- `HookLogStore`
- `EnvironmentService`
- `DeviceInventoryService`

### `workspace_traffic_service.py`

Responsibilities:

- HAR import
- traffic summary persistence
- live-capture state updates
- future integration with SQLite traffic flow persistence

Dependencies:

- `TrafficCaptureService`
- `live_capture_runtime.py`

### `workspace_report_service.py`

Responsibilities:

- build export inputs from static/runtime/traffic state
- delegate actual report creation to `ReportExportService`
- own report-export coordination instead of leaving it in runtime orchestration

### `workspace_runtime_state.py`

This file should converge toward a state codec and compatibility layer. It should continue to define persisted state structures and serialization/deserialization helpers, but it should no longer accumulate growing business orchestration logic.

## API-Layer Convergence

`src/apk_hacker/interfaces/api_fastapi/routes_workspace.py` currently contains both route logic and accumulated presenter/assembler behavior. This round does not require a complete presenter-layer rewrite, but it does require two improvements:

1. routes stop reaching into runtime-service internals such as private service attributes
2. route-level mapping logic is consolidated around runtime facade public methods and local response helpers

The route layer should depend on stable public application-service APIs, not on implementation details.

## Implementation Sequence

### Phase A: Documentation and normalized static artifacts

Files expected to change:

- `README.md`
- `AGENTS.md` if architectural wording needs alignment
- `src/apk_hacker/application/services/job_service.py`
- `src/apk_hacker/application/services/static_adapter.py`
- `src/apk_hacker/application/services/static_result_normalizer.py`
- `src/apk_hacker/domain/models/artifact.py`
- `src/apk_hacker/domain/models/evidence.py`
- `src/apk_hacker/domain/models/finding.py`
- `src/apk_hacker/domain/models/static_result.py`
- corresponding tests

Expected result:

- normalized static artifacts are always written and discoverable after static import
- compatibility with the existing workspace import flow is preserved

### Phase B: Runtime decomposition

Files expected to be added:

- `src/apk_hacker/application/services/workspace_hook_plan_service.py`
- `src/apk_hacker/application/services/workspace_execution_service.py`
- `src/apk_hacker/application/services/workspace_traffic_service.py`
- `src/apk_hacker/application/services/workspace_report_service.py`

Files expected to change:

- `src/apk_hacker/application/services/workspace_runtime_service.py`
- `src/apk_hacker/application/services/workspace_state_service.py`
- `src/apk_hacker/application/services/workspace_runtime_state.py`

Recommended decomposition order:

1. Hook plan service
2. traffic service
3. report service
4. execution service

This order minimizes risk while reducing the largest coordination bottlenecks first.

### Phase C: API-layer convergence

Files expected to change:

- `src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- possibly `src/apk_hacker/interfaces/api_fastapi/schemas.py`

Expected result:

- no route depends on runtime-service private members
- public facade methods provide the application data needed by routes

### Phase D: P1 minimal landing zone

Files expected to change:

- `src/apk_hacker/domain/models/hook_plan.py`
- `src/apk_hacker/application/services/hook_plan_service.py`
- `src/apk_hacker/application/services/workspace_runtime_state.py`
- `src/apk_hacker/infrastructure/templates/script_renderer.py`
- `src/apk_hacker/application/services/traffic_capture_service.py`
- `src/apk_hacker/application/services/workspace_traffic_service.py`
- optionally `src/apk_hacker/interfaces/api_fastapi/routes_traffic.py`

Files expected to be added:

- `src/apk_hacker/infrastructure/persistence/traffic_flow_store.py`

Expected result:

- Hook plan metadata is carried end-to-end
- traffic persistence has an initial stable storage boundary

## Risks and Mitigations

### Risk 1: Runtime behavior regressions during service extraction

Mitigation:

- extract behavior into new services before changing route contracts
- keep `workspace_runtime_service.py` as a stable facade
- validate after each extracted responsibility

### Risk 2: State-format breakage

Mitigation:

- preserve compatibility handling in `workspace_runtime_state.py`
- treat it as the single codec/compatibility boundary for persisted runtime state

### Risk 3: API breakage from private coupling

Mitigation:

- replace private-member access with explicit public methods on the runtime facade
- keep response-model assembly stable while internals move behind the facade

### Risk 4: Traffic scope explosion

Mitigation:

- limit the first traffic-store landing to persistence seams and HAR-import persistence
- defer advanced correlation and query capabilities

### Risk 5: Interference with large in-progress local changes

Mitigation:

- align changes with the direction already visible in the repository
- avoid unrelated restructuring
- keep the refactor tightly scoped to convergence targets

## Validation Gates

Repository-level validation for this refactor:

```bash
uv run pytest -q
npm run typecheck:web
npm run test:web -- --run
```

If desktop-shell behavior changes are touched:

```bash
cargo check --manifest-path src-tauri/Cargo.toml
```

Priority targeted test areas:

- static normalization and import flow
- runtime state serialization/compatibility
- workspace runtime orchestration
- traffic import/live-capture integration
- FastAPI workspace/execution/report/traffic endpoints

## Acceptance Criteria

This refactor round is complete when all of the following are true:

1. Project documentation reflects a single architectural mainline.
2. Static imports produce stable normalized artifacts in addition to compatibility inputs.
3. `workspace_runtime_service.py` is visibly reduced to an orchestration/facade role.
4. Runtime state, Hook planning, execution, traffic, and report responsibilities are no longer concentrated in one file.
5. FastAPI workspace routes no longer depend on runtime-service internals.
6. Hook plan metadata is preserved through model, state, service, and API boundaries.
7. The existing workspace loop remains functional:
   - import sample
   - inspect static summary
   - search methods
   - build Hook plan
   - execute
   - import or inspect traffic
   - export report

## Summary

This refactor is not about inventing a new idealized APKHacker structure. It is about converging the current working workspace into a maintainable architecture: stabilize schemas first, split runtime responsibilities second, and create a controlled landing zone for P1 capabilities without breaking the existing product loop.
