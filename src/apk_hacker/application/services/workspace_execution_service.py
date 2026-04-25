from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Event
from typing import Protocol

from apk_hacker.application.services.environment_service import EnvironmentService
from apk_hacker.application.services.execution_runtime import build_execution_backend
from apk_hacker.application.services.execution_runtime import build_execution_backend_env
from apk_hacker.application.services.execution_runtime import resolve_execution_routing
from apk_hacker.application.services.execution_runtime import ExecutionRouting
from apk_hacker.application.services.execution_presets import label_for_preset
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_runtime_state import ExecutionHistoryEntry
from apk_hacker.application.services.workspace_runtime_state import normalize_path
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.execution import ExecutionRuntimeOptions
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.infrastructure.execution.backend import ExecutionCancelled
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


class ExecutionBackend(Protocol):
    def execute(self, request: ExecutionRequest) -> list[HookEvent] | tuple[HookEvent, ...]: ...


class ExecutionBackendBuilder(Protocol):
    def __call__(
        self,
        execution_mode: str,
        *,
        artifact_root: Path | None = None,
        extra_env: Mapping[str, str] | None = None,
        real_device_command: str | None = None,
    ) -> ExecutionBackend: ...


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    state: WorkspaceRuntimeState
    execution_mode: str
    executed_backend_key: str
    run_id: str
    event_count: int
    db_path: Path
    bundle_path: Path
    executed_backend_label: str
    events: tuple[HookEvent, ...]


class WorkspaceExecutionService:
    def __init__(
        self,
        *,
        execution_backend_env: Mapping[str, str] | None = None,
        real_device_command: str | None = None,
        environment_service: EnvironmentService | None = None,
        backend_builder: ExecutionBackendBuilder | None = None,
    ) -> None:
        self._execution_backend_env = dict(execution_backend_env or {})
        self._real_device_command = real_device_command
        self._environment_service = environment_service or EnvironmentService()
        self._backend_builder = backend_builder or build_execution_backend

    def resolve_execution_routing(self, execution_mode: str | None = None) -> ExecutionRouting:
        requested_mode = execution_mode or "fake_backend"
        return resolve_execution_routing(
            requested_mode,
            snapshot=self._environment_service.inspect(),
            runtime_availability=self.runtime_availability(),
        )

    def runtime_availability(self) -> dict[str, bool]:
        from apk_hacker.application.services.execution_runtime import build_execution_runtime_availability

        return build_execution_runtime_availability(
            extra_env=self._execution_backend_env,
            real_device_command=self._real_device_command,
        )

    def execute(
        self,
        state: WorkspaceRuntimeState,
        record: WorkspaceInspectionRecord,
        execution_mode: str | None = None,
        *,
        executed_backend_key: str | None = None,
        runtime_options: ExecutionRuntimeOptions | None = None,
        cancellation_event: Event | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> ExecutionResult:
        resolved_mode = execution_mode or "fake_backend"
        routing = self.resolve_execution_routing(resolved_mode)
        resolved_backend_key = executed_backend_key or routing.executed_backend_key
        run_index = state.execution_count + 1
        run_id = f"run-{run_index}"
        bundle_path = record.workspace_root / "executions" / run_id
        bundle_path.mkdir(parents=True, exist_ok=True)

        runtime_env = self._build_runtime_env(runtime_options)
        backend_env = dict(self._execution_backend_env)
        backend_env.update(runtime_env)
        backend = self._backend_builder(
            resolved_backend_key,
            artifact_root=bundle_path,
            extra_env=backend_env,
            real_device_command=self._real_device_command,
        )

        if progress_callback is not None:
            progress_callback("executing")
        request = ExecutionRequest(
            job_id=record.bundle.job.job_id,
            plan=state.rendered_hook_plan,
            package_name=record.bundle.static_inputs.package_name,
            sample_path=record.sample_path,
            runtime_env=runtime_env,
            cancellation_event=cancellation_event,
        )
        events = backend.execute(request)
        if cancellation_event is not None and cancellation_event.is_set():
            raise ExecutionCancelled("Execution was cancelled by the user.")

        bundle_from_backend = next(
            (
                normalize_path(event.arguments[0])
                for event in events
                if event.event_type == "execution_bundle" and event.arguments
            ),
            None,
        )
        if bundle_from_backend is not None:
            bundle_path = bundle_from_backend
            bundle_path.mkdir(parents=True, exist_ok=True)

        db_path = bundle_path / "hook-events.sqlite3"
        if progress_callback is not None:
            progress_callback("persisting")
        store = HookLogStore(db_path)
        persisted_events = tuple(event for event in events if event.event_type != "execution_bundle")
        for event in persisted_events:
            store.insert(replace(event, job_id=record.bundle.job.job_id))

        updated_state = self._mark_execution_completed(
            state,
            run_index=run_index,
            run_id=run_id,
            execution_mode=resolved_mode,
            executed_backend_key=resolved_backend_key,
            event_count=len(persisted_events),
            db_path=db_path,
            bundle_path=bundle_path,
        )
        return ExecutionResult(
            state=updated_state,
            execution_mode=resolved_mode,
            executed_backend_key=resolved_backend_key,
            run_id=run_id,
            event_count=len(persisted_events),
            db_path=db_path,
            bundle_path=bundle_path,
            executed_backend_label=label_for_preset(resolved_backend_key),
            events=persisted_events,
        )

    def _build_runtime_env(self, runtime_options: ExecutionRuntimeOptions | None) -> dict[str, str]:
        if runtime_options is None:
            return {}

        frida_server_binary = runtime_options.frida_server_binary_path.strip()
        frida_server_remote_path = runtime_options.frida_server_remote_path.strip()
        frida_session_seconds = runtime_options.frida_session_seconds.strip()
        parsed_session_seconds: float | None = None
        if frida_session_seconds:
            parsed_session_seconds = float(frida_session_seconds)

        return build_execution_backend_env(
            device_serial=runtime_options.device_serial.strip() or None,
            frida_server_binary=Path(frida_server_binary).expanduser() if frida_server_binary else None,
            frida_server_remote_path=frida_server_remote_path or None,
            frida_session_seconds=parsed_session_seconds,
        )

    def _mark_execution_completed(
        self,
        state: WorkspaceRuntimeState,
        *,
        run_index: int,
        run_id: str,
        execution_mode: str,
        executed_backend_key: str,
        event_count: int,
        db_path: Path,
        bundle_path: Path,
    ) -> WorkspaceRuntimeState:
        history_id = state.current_execution_history_id or f"exec-{len(state.execution_history) + 1}"
        history = self._upsert_execution_history(
            state.execution_history,
            history_id=history_id,
            run_id=run_id,
            execution_mode=execution_mode,
            executed_backend_key=executed_backend_key,
            status="completed",
            stage="completed",
            event_count=event_count,
            db_path=db_path,
            bundle_path=bundle_path,
        )
        return replace(
            state,
            current_execution_history_id=None,
            execution_history=history,
            execution_count=run_index,
            last_execution_run_id=run_id,
            last_execution_mode=execution_mode,
            last_executed_backend_key=executed_backend_key,
            last_execution_status="completed",
            last_execution_stage="completed",
            last_execution_error_code=None,
            last_execution_error_message=None,
            last_execution_event_count=event_count,
            last_execution_result_path=bundle_path,
            last_execution_db_path=db_path,
            last_execution_bundle_path=bundle_path,
        )

    def _upsert_execution_history(
        self,
        history: tuple[ExecutionHistoryEntry, ...],
        *,
        history_id: str,
        run_id: str,
        execution_mode: str,
        executed_backend_key: str,
        status: str,
        stage: str,
        event_count: int,
        db_path: Path,
        bundle_path: Path,
    ) -> tuple[ExecutionHistoryEntry, ...]:
        updated_entries = list(history)
        for index, entry in enumerate(updated_entries):
            if entry.history_id != history_id:
                continue
            updated_entries[index] = replace(
                entry,
                run_id=run_id,
                execution_mode=execution_mode,
                executed_backend_key=executed_backend_key,
                status=status,
                stage=stage,
                error_code=None,
                error_message=None,
                event_count=event_count,
                db_path=db_path,
                bundle_path=bundle_path,
            )
            return tuple(updated_entries)
        return (*history, ExecutionHistoryEntry(
            history_id=history_id,
            run_id=run_id,
            execution_mode=execution_mode,
            executed_backend_key=executed_backend_key,
            status=status,
            stage=stage,
            error_code=None,
            error_message=None,
            event_count=event_count,
            db_path=db_path,
            bundle_path=bundle_path,
        ))
