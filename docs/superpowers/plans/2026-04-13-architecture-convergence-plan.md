# APKHacker Architecture Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge APKHacker onto a single `Tauri + React + FastAPI` product line, freeze and retire `PyQt6`, and leave dynamic-analysis capability work hanging off the unified workspace/API model instead of split desktop stacks.

**Architecture:** Keep the Python analysis core and runner model, but make `FastAPI` the only application contract and `Tauri + React` the only user-facing shell. Treat `PyQt6` as a legacy reference during migration only; no new feature work lands there. Migrate missing user-visible capabilities into the API and React workspace, then remove PyQt entrypoints, tests, and documentation from the primary flow.

**Tech Stack:** Python 3.11+, FastAPI, React 18, TypeScript, Vite, Tauri v2, Vitest, pytest, existing APKHacker Python services and runner tools

---

## Scope Summary

This plan replaces the old implicit dual-track delivery model:

- Old model: `PyQt GUI` and `Tauri/React` both evolve while sharing Python internals
- New model: `FastAPI` is the single app surface, `Tauri/React` is the single desktop client, `PyQt` is frozen and then removed

Out of scope for this convergence plan:

- AI code analysis
- AI traffic analysis
- New unpacking families
- Full SSL unpinning productization
- New dynamic-analysis feature families not required to replace the PyQt path

Those items should be planned after convergence completes.

## File Map

### Product and migration documents

- Modify: `/Users/penglai/Documents/Objects/APKHacker/README.md`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/specs/2026-04-06-apk-hacker-tauri-redesign.md`
- Create or update as needed: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-13-architecture-convergence-plan.md`

### FastAPI application surface

- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/app.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_execution.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_reports.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_traffic.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/schemas.py`

### Python application services

- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_inspection_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_runtime_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/custom_script_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/traffic_capture_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/environment_service.py`

### React/Tauri desktop client

- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/api.ts`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/types.ts`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/desktop.ts`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseQueuePage.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseWorkspacePage.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/HookStudioPanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/ExecutionConsolePanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/ReportsPanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/EvidencePanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/TrafficEvidencePanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src-tauri/src/lib.rs`

### Legacy retirement surface

- Freeze then remove: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/main.py`
- Freeze then remove: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/main_window.py`
- Freeze then remove: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/viewmodels.py`
- Freeze then remove: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/widgets/`
- Modify then remove script references from: `/Users/penglai/Documents/Objects/APKHacker/pyproject.toml`

### Tests

- Modify: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_workspace.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_execution.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_reports.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/tests/application/test_workspace_controller.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/workspace-page.test.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/app-shell.test.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/api-adapters.test.ts`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_main_entry.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_main_window_smoke.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_workbench_flow.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_environment_widget_flow.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_execution_logs_widget.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_results_summary_widget.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_static_summary_widget.py`
- Freeze then remove after cutover: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_main_window_settings.py`

---

### Task 1: Declare Single-Track Product Ownership

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/README.md`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/specs/2026-04-06-apk-hacker-tauri-redesign.md`

- [ ] Add a short “current product direction” section that explicitly states:
  - `Tauri + React + FastAPI` is the only active UI/application architecture
  - `PyQt6` is frozen and scheduled for retirement
  - all new product tasks must target API + React
- [ ] Update the README feature/status list so it no longer presents `PyQt` as the main workbench path.
- [ ] Add a migration note that maps old workbench concepts to new equivalents:
  - `Task Center` -> `Case Queue` / `Case Workspace`
  - `Script Plan` -> `Hook Studio + Execution Console`
  - `Results Summary` -> `Reports + Evidence + Execution`
- [ ] Verify docs stay consistent by manually checking both files for conflicting language like “current GUI” or “workbench” pointing to PyQt.

### Task 2: Define the API as the Only Application Contract

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/app.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/schemas.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_execution.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_reports.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_traffic.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_workspace.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_execution.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_reports.py`

- [ ] Audit existing API routes and group them into four stable capability sets:
  - queue/import
  - workspace inspection/hook planning
  - execution/reporting
  - traffic/evidence
- [ ] Add or normalize response metadata needed by React so the frontend does not reconstruct state heuristically.
- [ ] Ensure all workspace screens can be hydrated from API responses alone, without reading Python internals or assuming PyQt-era behavior.
- [ ] Add or tighten FastAPI tests for:
  - workspace detail hydration
  - execution start success/failure states
  - report export state
  - traffic import and retrieval
- [ ] Run: `uv run pytest tests/interfaces/test_fastapi_workspace.py tests/interfaces/test_fastapi_execution.py tests/interfaces/test_fastapi_reports.py -q`

### Task 3: Shrink Python Application Logic Around Workspace State

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_inspection_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_runtime_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/custom_script_service.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/traffic_capture_service.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/application/test_workspace_controller.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/application/test_traffic_capture_service.py`

- [ ] Refactor any PyQt-shaped assumptions out of application services so they speak only in workspace records, runtime state, and API-friendly DTOs.
- [ ] Split or helper-extract `workspace_runtime_service.py` if continued growth makes it the new coupling hotspot.
- [ ] Preserve the existing runner model, rendered script artifacts, and report export behavior while making the state model easier for FastAPI to serialize.
- [ ] Add tests around workspace runtime transitions:
  - hook plan mutation
  - traffic import persistence
  - execution metadata persistence
  - report export persistence
- [ ] Run: `uv run pytest tests/application/test_workspace_controller.py tests/application/test_traffic_capture_service.py -q`

### Task 4: Reach Feature Parity for the New Workspace

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/api.ts`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/types.ts`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseWorkspacePage.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/HookStudioPanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/ExecutionConsolePanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/ReportsPanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/EvidencePanel.tsx`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/TrafficEvidencePanel.tsx`
- Test: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/workspace-page.test.tsx`
- Test: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/api-adapters.test.ts`

- [ ] Build a parity checklist from current PyQt-visible workflows and verify each one exists in `Case Workspace`.
- [ ] Close remaining gaps in these user flows:
  - search methods and add to hook plan
  - add recommendation to hook plan
  - save custom script and insert into plan
  - start execution and observe status
  - inspect evidence/events
  - import HAR and inspect suspicious traffic
  - export report
  - open in JADX
- [ ] Remove any React-side fallback logic that exists only because the API contract is incomplete once Task 2 lands.
- [ ] Keep the UI Chinese-first and desktop-native; do not reintroduce PyQt naming.
- [ ] Run:
  - `npm run typecheck:web`
  - `npm run test:web -- --run`

### Task 5: Make Tauri the Real Desktop Entry

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src-tauri/src/lib.rs`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/desktop.ts`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/package.json`
- Modify as needed: `/Users/penglai/Documents/Objects/APKHacker/src-tauri/tauri.conf.json`
- Test: `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/app-shell.test.tsx`

- [ ] Treat the Tauri shell as the default local desktop runtime, not as an optional experimental wrapper.
- [ ] Stabilize sidecar startup assumptions:
  - API start command
  - skip-sidecar behavior for dev/test
  - dialog availability in runtime vs browser test mode
- [ ] Make sure developer workflows are explicit:
  - web-only dev
  - tauri dev
  - tauri build
- [ ] Add or update app-shell tests if any startup-state messaging changes.

### Task 6: Freeze PyQt and Block Further Drift

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/README.md`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/pyproject.toml`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/main.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/main_window.py`

- [ ] Mark PyQt entrypoints as legacy/frozen in docs and any user-facing help text.
- [ ] Remove PyQt from default setup and launch instructions once Tauri startup is verified.
- [ ] If the CLI or script surface still points users toward PyQt, update wording to point to Tauri first.
- [ ] Do not add new behavior here; only add deprecation messaging or temporary guardrails.

### Task 7: Remove Legacy PyQt as a Product Dependency

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/pyproject.toml`
- Delete or retire: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/`
- Delete or retire: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_main_entry.py`
- Delete or retire: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_main_window_smoke.py`
- Delete or retire: `/Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_workbench_flow.py`
- Delete or retire related PyQt-only tests/widgets after cutover

- [ ] Remove `PyQt6` from runtime dependencies after feature parity is confirmed on the new stack.
- [ ] Remove PyQt script entrypoints that are no longer supported.
- [ ] Remove or archive PyQt-only tests once they stop representing a supported product path.
- [ ] Run the remaining Python and web test suites to confirm nothing still imports PyQt accidentally.

### Task 8: Stabilize the Real Dynamic Backend Behind the New Surface

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/infrastructure/execution/real_backend.py`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/tools/frida_inject_backend.py`
- Modify as needed: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/tools/frida_probe_backend.py`
- Modify as needed: `/Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/tools/frida_session_backend.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/tools/test_frida_inject_backend.py`
- Test: `/Users/penglai/Documents/Objects/APKHacker/tests/tools/test_frida_session_backend.py`

- [ ] Fix the currently failing selected-device serial path in the Frida inject runner.
- [ ] Treat runner stability as a convergence blocker because the new UI already exposes these execution modes.
- [ ] Normalize emitted events so the frontend can render them without mode-specific hacks.
- [ ] Run:
  - `uv run pytest tests/tools/test_frida_inject_backend.py -q`
  - `uv run pytest tests/tools/test_frida_session_backend.py -q`

### Task 9: Define Cutover Readiness and Execute the Removal

**Files:**
- Modify: `/Users/penglai/Documents/Objects/APKHacker/README.md`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/specs/2026-04-06-apk-hacker-tauri-redesign.md`
- Modify: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-13-architecture-convergence-plan.md`

- [ ] Declare cutover complete only when all of these are true:
  - Tauri is the default desktop launch path
  - React workspace covers the supported user flows
  - FastAPI is the only application contract
  - PyQt is removed from runtime dependencies and main docs
  - Python and web test suites pass without PyQt support
- [ ] After cutover, create a fresh follow-up roadmap for:
  - stronger real-device execution
  - richer traffic analysis
  - AI augmentation

---

## Recommended Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 8
6. Task 5
7. Task 6
8. Task 7
9. Task 9

## Risks to Watch

- `workspace_runtime_service.py` is already large and can become the next bottleneck if API state keeps accreting there.
- The project currently has a passing web suite but a failing Python tool-path test in the Frida inject runner; do not claim desktop convergence while that remains unstable.
- Removing PyQt too early, before feature parity and startup stability, would turn a product convergence effort into a regression.

## Verification Gate

Before declaring this plan complete in implementation:

- Run: `uv run pytest -q`
- Run: `npm run typecheck:web`
- Run: `npm run test:web -- --run`
- Run a manual Tauri smoke launch with the local API sidecar

## Spec Coverage Check

- Architecture convergence: covered by Tasks 1, 2, 5, 6, 7, 9
- React/FastAPI product completion: covered by Tasks 2, 3, 4, 5
- PyQt retirement: covered by Tasks 6, 7, 9
- Dynamic runner stability needed by the new shell: covered by Task 8

## Placeholder Scan

This plan intentionally avoids future-feature placeholders and focuses only on convergence work. AI expansion, unpacking, and full traffic intelligence are explicitly out of scope until post-cutover planning.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-13-architecture-convergence-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints
