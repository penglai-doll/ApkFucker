# APKHacker MVP Design

> Status: Draft approved in conversation, written for review
> Date: 2026-04-05

Implementation plan: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-05-apk-hacker-mvp-plan.md`

## Goal

Build a local-first Android APK analysis workstation that extends the existing `android-malware-analysis` skill into a standalone program. The MVP should prioritize a testable architecture and a function-centered Hook workflow over real-device execution.

## Product Direction

The product is not just a static analysis wrapper and not just a Frida script launcher. It is a local analyst workbench with three core abilities:

1. Run first-party static analysis on APK or decoded artifacts
2. Build a method-level Hook plan from analysis results and user selections
3. Execute a simulated dynamic workflow end-to-end, persist events, and summarize results

The long-term direction is:

- Phase 1: PyQt6 prototype
- Phase 2: optional FastAPI interface layer
- Phase 3: optional Tauri front end after backend contracts stabilize

## Scope

### In Scope for MVP

- Migrate the current `android-malware-analysis` skill into this repository as a first-party static engine
- Normalize static-analysis outputs into stable internal models
- Build class and method indexes from static outputs and JADX-derived source artifacts
- Support method-centered Hook planning
- Support project-bundled Hook strategy plugins
- Support user-authored Frida JavaScript scripts and one-click injection into the current plan
- Run the full orchestration flow with a fake execution backend
- Persist Hook events into SQLite
- Show results through a PyQt6 desktop interface
- Allow opening the current sample in local `jadx-gui`

### Explicitly Out of Scope for MVP

- Real ADB / Frida device execution
- SSL unpinning verification on a real target
- mitmproxy traffic capture
- unpacking / shell removal
- AI-powered semantic Hook recommendation
- public plugin marketplace
- Tauri front end
- full embedded code browser comparable to JADX

## Architecture

The system should be organized into four layers.

### 1. `static_engine`

This is the migrated and reorganized static analysis engine derived from the current skill. It becomes part of this repository and is the single source of truth for static analysis capabilities.

Responsibilities:

- accept APK, XAPK, decoded directories, or related supported inputs
- run the static pipeline
- emit structured artifacts
- expose a stable Python API for the rest of the application

This layer should not depend on GUI code or dynamic execution concerns.

### 2. `domain`

This layer defines the stable business models and core rules used across the whole application.

Key models:

- `StaticInputs`
- `ClassIndexEntry`
- `MethodIndexEntry`
- `MethodHookTarget`
- `HookPlanItem`
- `HookEvent`
- `AnalysisJob`
- `DynamicSummary`

This layer should stay small, explicit, and framework-agnostic.

### 3. `application`

This is the orchestration and use-case layer. It turns user actions into workflows and coordinates the static engine, planning logic, execution backend, persistence, and reporting.

Responsibilities:

- create and track jobs
- adapt static outputs to internal models
- build method indexes
- assemble Hook plans
- manage built-in plugins and user scripts
- call execution backends
- store and summarize results

This layer should not depend on PyQt widgets or HTTP routes.

### 4. `infrastructure` and `interfaces`

`infrastructure` holds concrete technical implementations. `interfaces` exposes user entry points.

Infrastructure examples:

- SQLite storage
- template rendering
- subprocess launching
- fake execution backend
- future real-device backend
- future AI clients

Interface examples:

- PyQt6 GUI
- CLI
- future FastAPI layer

## Repository Structure

```text
src/
  apk_hacker/
    static_engine/
      analyzer.py
      pipeline/
      reporting/
      tooling/
    domain/
      models/
      services/
    application/
      dto/
      services/
      jobs/
      plugins/
    infrastructure/
      execution/
      persistence/
      templates/
      filesystem/
      subprocesses/
      integrations/
    interfaces/
      gui_pyqt/
      cli/
      api_fastapi/

tests/
  static_engine/
  domain/
  application/
  infrastructure/
  interfaces/
  fixtures/

docs/
  superpowers/
    specs/
```

## Static Engine Strategy

The project should not call a machine-local skill path at runtime. Instead, the current `android-malware-analysis` implementation should be migrated into `src/apk_hacker/static_engine/` and adapted into a first-party module.

This avoids hidden environment dependencies and makes the repository portable. It also prevents future feature work from constantly crossing a `vendor` boundary.

Migration principle:

- preserve working behavior first
- refactor structure second
- keep the public API stable for the rest of the system

Suggested public API:

```python
class StaticAnalyzer:
    def analyze(self, target_path: str, output_dir: str, mode: str = "auto") -> "StaticArtifacts":
        ...
```

## Core Internal Models

### `StaticInputs`

Normalized static result consumed by all later stages.

Suggested fields:

- `sample_path`
- `package_name`
- `technical_tags`
- `dangerous_permissions`
- `callback_endpoints`
- `callback_clues`
- `crypto_signals`
- `packer_hints`
- `limitations`
- `artifact_paths`

### `ClassIndexEntry`

- `class_name`
- `package_name`
- `source_path`
- `method_count`
- `tags`

### `MethodIndexEntry`

- `class_name`
- `method_name`
- `parameter_types`
- `return_type`
- `is_constructor`
- `overload_count`
- `source_path`
- `line_hint`
- `tags`
- `evidence`

### `MethodHookTarget`

- `target_id`
- `class_name`
- `method_name`
- `parameter_types`
- `return_type`
- `source_origin`
- `notes`

### `HookPlanItem`

- `item_id`
- `kind`
- `enabled`
- `inject_order`
- `target`
- `render_context`
- `plugin_id`

Kinds should include at least:

- `method_hook`
- `template_hook`
- `script_plugin`
- `custom_script`

### `HookEvent`

- `timestamp`
- `job_id`
- `event_type`
- `source`
- `class_name`
- `method_name`
- `arguments`
- `return_value`
- `stacktrace`
- `raw_payload`

### `AnalysisJob`

- `job_id`
- `status`
- `created_at`
- `updated_at`
- `input_target`
- `artifacts`
- `summary`
- `error`

## Job Model and Data Flow

The application should be task-driven from the start.

Primary flow:

1. User selects a target and starts a job
2. Application runs `static_engine`
3. Static artifacts are normalized into `StaticInputs`
4. Method indexes are built
5. User selects methods or loads built-in/custom scripts
6. Application builds a `HookPlan`
7. Fake execution backend simulates injection and emits `HookEvent`s
8. Events are stored in SQLite
9. Reporting creates a minimal dynamic summary
10. UI shows job state, events, and summary

Initial job states:

- `queued`
- `running_static`
- `adapting_static`
- `indexing_methods`
- `planning_hooks`
- `executing_dynamic`
- `persisting_results`
- `completed`
- `failed`
- `cancelled`

## Hook Capability Design

Hook is a core product capability and should remain in the core architecture. However, specific Hook strategies should be plugin-based.

### Core Responsibilities

These belong in core modules:

- method indexing
- function selection
- Hook plan assembly
- session execution flow
- event collection
- event-to-stacktrace feedback loop
- user custom script management

### Plugin Responsibilities

These should be implemented as project-bundled plugins:

- specific Frida templates
- framework-specific Hook strategies
- crypto-related Hook helpers
- anti-detection helpers
- stacktrace-to-Hook candidate expanders
- future analysis enrichers

## Plugin Model

Two plugin classes should exist.

### 1. Analysis Plugins

Python plugins that run inside the application workflow.

Use cases:

- enrich method tags
- detect family-specific patterns
- derive additional Hook candidates
- enrich final report sections

### 2. Frida Script Plugins

JavaScript-based Hook units that can be injected as part of a Hook plan.

Use cases:

- bundled helper scripts
- reusable project scripts
- user-authored custom scripts

The MVP should support:

- built-in plugins
- local user scripts

The MVP should not support:

- marketplace-style installation
- remote download
- capability sandboxing

## Function-Centered Hook Workflow

The primary Hook workflow should be based on methods, not natural-language goals.

Target interaction:

1. User searches or filters the method index
2. User selects a method
3. Application shows method details and related static evidence
4. User adds the method to the Hook plan
5. Application generates the Hook item
6. User optionally adds built-in or custom Frida scripts
7. User runs the plan
8. Events and stacktraces can be used to append more Hook targets

This is closer to products like "算法助手Pro" than to a purely prompt-driven AI assistant.

## Custom Frida Script Support

The product must support the case where auto-generated Hook logic is insufficient.

Required behavior:

- users can create and save local Frida JavaScript files
- users can enable or disable each custom script
- users can add a script into the current plan with one action
- execution should inject custom scripts together with auto-generated items

This capability is not a temporary debug tool. It is a first-class extension path.

## GUI Strategy

Phase 1 should use PyQt6 for a fast local workstation prototype.

The GUI should remain a thin shell over `application` services. It should not contain analysis logic.

Suggested primary pages:

- `Task Center`
- `Static Summary`
- `Method Index`
- `Hook Assistant`
- `Script Plan`
- `Custom Frida Scripts`
- `Execution & Logs`
- `Results Summary`

### Code Navigation Strategy

The application should not implement a full embedded code browser in the MVP.

Instead:

- provide method and class indexes
- provide search over package, class, method, and signature
- offer `Open in JADX` for deep code reading

This keeps the GUI simpler and avoids building a code editor that would later be replaced in a web-based front end.

### JADX Integration

The application should support a configured local `jadx-gui` path and expose an action to open the current sample in JADX.

This should be treated as an advanced external viewer, not as part of the core UI stack.

## Future FastAPI and Tauri Compatibility

The project should be designed as Tauri-compatible without adopting Tauri in the MVP.

Rules:

- core workflows must live in `application`
- GUI calls use application-service boundaries
- future HTTP endpoints should wrap the same application services
- the UI should consume job-oriented contracts, not low-level static-engine objects

This makes the later transition path:

- PyQt6 -> optional FastAPI
- FastAPI -> optional Tauri frontend

The cost of future migration should mainly be UI work, not backend rework.

## MVP Phase Plan

### Phase 1: PyQt6 Prototype, Testability First

Must deliver:

- first-party static engine migration
- normalized internal models
- method indexing
- method-centered Hook planning
- built-in plugin support
- local custom Frida script support
- fake execution backend
- SQLite event storage
- PyQt6 workstation UI
- local JADX open action

### Phase 2: API Layer If Needed

May deliver:

- FastAPI wrapper for application services
- job status and artifact APIs
- event query endpoints

### Phase 3: Frontend Rewrite If Needed

May deliver:

- Tauri front end
- same backend contracts through API or local service bridge

## Test Strategy

The MVP should be designed around automated tests before real-device integration.

### Unit Tests

- static normalization
- method indexing
- Hook plan construction
- plugin registration and dispatch
- SQLite persistence

### Integration Tests

- fixture static artifacts -> normalized models -> Hook plan -> fake execution -> SQLite -> summary

### GUI Smoke Tests

- open main window
- create task
- switch key views
- add a Hook target
- run fake execution

### Contract Tests

Lock down schemas for:

- `StaticInputs`
- `MethodIndexEntry`
- `HookPlanItem`
- `HookEvent`

## Risks

### 1. Static Engine Migration Drift

Moving the current skill into a first-party module may accidentally change output behavior.

Mitigation:

- preserve fixtures from the existing skill
- keep artifact-shape regression tests

### 2. Method Index Quality

Method-level indexing may be incomplete or inconsistent depending on available source artifacts.

Mitigation:

- treat source indexing as a best-effort enhancement over static artifacts
- keep method metadata explicit about source confidence

### 3. UI Overreach

Trying to replicate JADX inside the MVP would slow delivery and complicate future frontend migration.

Mitigation:

- keep in-app browsing limited to indexes and details
- delegate deep code reading to local JADX

## Decisions Captured

- Do not call the machine-local skill path at runtime
- Migrate the skill into a first-party static engine module
- Use PyQt6 first, but keep service boundaries compatible with FastAPI and future Tauri
- Treat Hook as a core product capability
- Implement Hook strategies and script units as built-in plugin-style extensions
- Use a function-centered Hook workflow
- Support user-authored Frida scripts as a first-class feature
- Do not build a full embedded code browser in the MVP
- Support opening samples in local JADX instead
