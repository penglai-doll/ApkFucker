from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass

from apk_hacker.application.services.execution_presets import label_for_preset
from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.domain.models.execution import ExecutionRuntimeOptions
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.backend import ExecutionCancelled
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionCancelResponse
from apk_hacker.interfaces.api_fastapi.schemas import ExecutionStartResponse
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


class ExecutionConflictError(RuntimeError):
    pass


class ExecutionNotRunningError(RuntimeError):
    pass


@dataclass(slots=True)
class _ExecutionHandle:
    case_id: str
    execution_mode: str
    executed_backend_key: str
    runtime_options: ExecutionRuntimeOptions
    future: concurrent.futures.Future[dict[str, object]]
    cancellation_event: threading.Event


def _normalize_failure_message(message: str) -> str:
    prefix = "Real device execution failed: "
    return message[len(prefix) :] if message.startswith(prefix) else message


def _classify_failure(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, CaseNotFoundError):
        return "case_not_found", "Case not found"
    if isinstance(exc, ExecutionBackendUnavailable):
        error_code = getattr(exc, "error_code", None) or "backend_unavailable"
        message = getattr(exc, "message", None)
        return error_code, message or _normalize_failure_message(str(exc))
    if isinstance(exc, ValueError):
        return "validation_error", str(exc)
    return "unknown_execution_error", str(exc)


class ExecutionDispatcher:
    def __init__(
        self,
        *,
        hub: WebSocketHub,
        workspace_runtime_service: WorkspaceRuntimeService,
    ) -> None:
        self._hub = hub
        self._workspace_runtime_service = workspace_runtime_service
        self._lock = threading.Lock()
        self._active_by_case: dict[str, _ExecutionHandle] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="apk-hacker-execution",
        )

    async def start_execution(
        self,
        case_id: str,
        execution_mode: str,
        runtime_options: ExecutionRuntimeOptions,
    ) -> ExecutionStartResponse:
        routing = self._workspace_runtime_service.resolve_execution_routing(execution_mode)
        with self._lock:
            existing = self._active_by_case.get(case_id)
            if existing is not None and not existing.future.done():
                raise ExecutionConflictError("Execution is already running for this case.")

            cancellation_event = threading.Event()
            self._workspace_runtime_service.mark_execution_started(
                case_id,
                execution_mode=execution_mode,
                executed_backend_key=routing.executed_backend_key,
                stage="queued",
            )
            future = self._executor.submit(
                self._execute_and_build_payload,
                case_id,
                execution_mode,
                routing.executed_backend_key,
                runtime_options,
                cancellation_event,
            )
            future.add_done_callback(
                lambda finished_future, *, target_case_id=case_id: self._on_execution_done(
                    target_case_id,
                    finished_future,
                )
            )
            self._active_by_case[case_id] = _ExecutionHandle(
                case_id=case_id,
                execution_mode=execution_mode,
                executed_backend_key=routing.executed_backend_key,
                runtime_options=runtime_options,
                future=future,
                cancellation_event=cancellation_event,
            )

        started_payload = {
            "type": "execution.started",
            "case_id": case_id,
            "status": "started",
            "stage": "queued",
            "execution_mode": execution_mode,
            "executed_backend_key": routing.executed_backend_key,
            "executed_backend_label": routing.executed_backend_label,
        }
        await self._hub.broadcast(started_payload)
        return ExecutionStartResponse(
            case_id=case_id,
            status="started",
            stage="queued",
            execution_mode=execution_mode,
            executed_backend_key=routing.executed_backend_key,
            executed_backend_label=routing.executed_backend_label,
        )

    async def cancel_execution(self, case_id: str) -> ExecutionCancelResponse:
        with self._lock:
            handle = self._active_by_case.get(case_id)
            if handle is None or handle.future.done():
                raise ExecutionNotRunningError("No execution is currently running for this case.")
            handle.cancellation_event.set()
            self._workspace_runtime_service.mark_execution_progress(
                case_id,
                execution_mode=handle.execution_mode,
                executed_backend_key=handle.executed_backend_key,
                status="cancelling",
                stage="cancelling",
            )

        payload = {
            "type": "execution.cancelling",
            "case_id": case_id,
            "status": "cancelling",
            "stage": "cancelling",
            "execution_mode": handle.execution_mode,
            "executed_backend_key": handle.executed_backend_key,
            "executed_backend_label": label_for_preset(handle.executed_backend_key),
        }
        await self._hub.broadcast(payload)
        return ExecutionCancelResponse(
            case_id=case_id,
            status="cancelling",
            stage="cancelling",
            execution_mode=handle.execution_mode,
            executed_backend_key=handle.executed_backend_key,
        )

    def _emit_progress(self, case_id: str, execution_mode: str, executed_backend_key: str, stage: str) -> None:
        with self._lock:
            handle = self._active_by_case.get(case_id)
            if handle is None or handle.future.done() or handle.cancellation_event.is_set():
                return
        self._workspace_runtime_service.mark_execution_progress(
            case_id,
            execution_mode=execution_mode,
            executed_backend_key=executed_backend_key,
            status="started",
            stage=stage,
        )
        self._hub.broadcast_nowait(
            {
                "type": "execution.progress",
                "case_id": case_id,
                "status": "started",
                "stage": stage,
                "execution_mode": execution_mode,
                "executed_backend_key": executed_backend_key,
                "executed_backend_label": label_for_preset(executed_backend_key),
            }
        )

    def _execute_and_build_payload(
        self,
        case_id: str,
        execution_mode: str,
        executed_backend_key: str,
        runtime_options: ExecutionRuntimeOptions,
        cancellation_event: threading.Event,
    ) -> dict[str, object]:
        try:
            result = self._workspace_runtime_service.execute_current_plan(
                case_id,
                execution_mode,
                executed_backend_key=executed_backend_key,
                runtime_options=runtime_options,
                cancellation_event=cancellation_event,
                progress_callback=lambda stage: self._emit_progress(
                    case_id,
                    execution_mode,
                    executed_backend_key,
                    stage,
                ),
            )
        except ExecutionCancelled as exc:
            self._workspace_runtime_service.mark_execution_cancelled(
                case_id,
                execution_mode,
                executed_backend_key=executed_backend_key,
            )
            return {
                "type": "execution.cancelled",
                "case_id": case_id,
                "status": "cancelled",
                "stage": "cancelled",
                "execution_mode": execution_mode,
                "executed_backend_key": executed_backend_key,
                "executed_backend_label": label_for_preset(executed_backend_key),
                "message": str(exc),
            }
        except CaseNotFoundError as exc:
            error_code, message = _classify_failure(exc)
            self._workspace_runtime_service.mark_execution_failed(
                case_id,
                execution_mode,
                executed_backend_key=executed_backend_key,
                stage="failed",
                error_code=error_code,
                message=message,
            )
            return {
                "type": "execution.failed",
                "case_id": case_id,
                "status": "error",
                "stage": "failed",
                "execution_mode": execution_mode,
                "executed_backend_key": executed_backend_key,
                "executed_backend_label": label_for_preset(executed_backend_key),
                "error_code": error_code,
                "message": message,
            }
        except (ValueError, ExecutionBackendUnavailable) as exc:
            error_code, message = _classify_failure(exc)
            self._workspace_runtime_service.mark_execution_failed(
                case_id,
                execution_mode,
                executed_backend_key=executed_backend_key,
                stage="failed",
                error_code=error_code,
                message=message,
            )
            return {
                "type": "execution.failed",
                "case_id": case_id,
                "status": "error",
                "stage": "failed",
                "execution_mode": execution_mode,
                "executed_backend_key": executed_backend_key,
                "executed_backend_label": label_for_preset(executed_backend_key),
                "error_code": error_code,
                "message": message,
            }

        return {
            "type": "execution.completed",
            "case_id": case_id,
            "status": "completed",
            "stage": "completed",
            "execution_mode": result.execution_mode,
            "executed_backend_key": result.executed_backend_key,
            "run_id": result.run_id,
            "event_count": result.event_count,
            "db_path": str(result.db_path),
            "bundle_path": str(result.bundle_path),
            "executed_backend_label": result.executed_backend_label,
        }

    def _on_execution_done(
        self,
        case_id: str,
        future: concurrent.futures.Future[dict[str, object]],
    ) -> None:
        try:
            payload = future.result()
        except Exception as exc:  # pragma: no cover - defensive fallback
            with self._lock:
                handle = self._active_by_case.get(case_id)
                execution_mode = handle.execution_mode if handle is not None else "fake_backend"
                executed_backend_key = handle.executed_backend_key if handle is not None else execution_mode
            error_code, message = _classify_failure(exc)
            self._workspace_runtime_service.mark_execution_failed(
                case_id,
                execution_mode,
                executed_backend_key=executed_backend_key,
                stage="failed",
                error_code=error_code,
                message=message,
            )
            payload = {
                "type": "execution.failed",
                "case_id": case_id,
                "status": "error",
                "stage": "failed",
                "execution_mode": execution_mode,
                "executed_backend_key": executed_backend_key,
                "executed_backend_label": label_for_preset(executed_backend_key),
                "error_code": error_code,
                "message": message,
            }

        try:
            self._hub.broadcast_nowait(payload)
        finally:
            with self._lock:
                existing = self._active_by_case.get(case_id)
                if existing is not None and existing.future is future:
                    self._active_by_case.pop(case_id, None)
