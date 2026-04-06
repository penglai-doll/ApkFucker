from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem
from apk_hacker.infrastructure.execution.backend import ExecutionBackend, ExecutionBackendUnavailable


ENV_COMMAND = "APKHACKER_REAL_BACKEND_COMMAND"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "script"


def _serialize_plan(plan: HookPlan) -> dict[str, object]:
    def serialize_item(item: HookPlanItem) -> dict[str, object]:
        target = None
        if item.target is not None:
            target = {
                "target_id": item.target.target_id,
                "class_name": item.target.class_name,
                "method_name": item.target.method_name,
                "parameter_types": list(item.target.parameter_types),
                "return_type": item.target.return_type,
                "source_origin": item.target.source_origin,
                "notes": item.target.notes,
            }
        return {
            "item_id": item.item_id,
            "kind": item.kind,
            "enabled": item.enabled,
            "inject_order": item.inject_order,
            "target": target,
            "render_context": dict(item.render_context),
            "plugin_id": item.plugin_id,
        }

    return {"items": [serialize_item(item) for item in plan.items]}


def _coerce_event(job_id: str, payload: Mapping[str, object]) -> HookEvent | None:
    event_type = payload.get("event_type")
    class_name = payload.get("class_name", payload.get("class"))
    method_name = payload.get("method_name", payload.get("method"))
    if not event_type or not class_name or not method_name:
        return None

    raw_arguments = payload.get("arguments", payload.get("args", ()))
    if isinstance(raw_arguments, (list, tuple)):
        arguments = tuple(str(value) for value in raw_arguments)
    elif raw_arguments is None:
        arguments = ()
    else:
        arguments = (str(raw_arguments),)

    return HookEvent(
        timestamp=str(payload.get("timestamp") or _now_iso()),
        job_id=str(payload.get("job_id") or job_id),
        event_type=str(event_type),
        source=str(payload.get("source") or "real"),
        class_name=str(class_name),
        method_name=str(method_name),
        arguments=arguments,
        return_value=(
            None
            if payload.get("return_value", payload.get("return")) is None
            else str(payload.get("return_value", payload.get("return")))
        ),
        stacktrace=str(payload.get("stacktrace", payload.get("stack", ""))),
        raw_payload=dict(payload),
    )


def _parse_events(job_id: str, stdout: str) -> tuple[HookEvent, ...]:
    events: list[HookEvent] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        event = _coerce_event(job_id, payload)
        if event is not None:
            events.append(event)
    return tuple(events)


def _run_bundle_event(
    job_id: str,
    workdir: Path,
    plan_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    command: str,
) -> HookEvent:
    return HookEvent(
        timestamp=_now_iso(),
        job_id=job_id,
        event_type="execution_bundle",
        source="real",
        class_name="backend",
        method_name="artifacts",
        arguments=(str(workdir), str(plan_path), str(stdout_path), str(stderr_path)),
        return_value=command,
        stacktrace="",
        raw_payload={
            "event_type": "execution_bundle",
            "class_name": "backend",
            "method_name": "artifacts",
            "arguments": (str(workdir), str(plan_path), str(stdout_path), str(stderr_path)),
            "return_value": command,
            "stacktrace": "",
        },
    )


class CommandExecutionRunner:
    def __init__(
        self,
        command: str,
        extra_env: Mapping[str, str] | None = None,
        artifact_root: Path | None = None,
    ) -> None:
        self._command = command
        self._extra_env = dict(extra_env or {})
        self._artifact_root = artifact_root

    def _make_workdir(self, job_id: str) -> tuple[Path, Callable[[], None]]:
        if self._artifact_root is None:
            temp_dir = TemporaryDirectory(prefix="apkhacker-real-backend-")
            return Path(temp_dir.name), temp_dir.cleanup

        self._artifact_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        workdir = self._artifact_root / f"{job_id}-{stamp}-{uuid4().hex[:8]}"
        workdir.mkdir(parents=True, exist_ok=False)
        return workdir, (lambda: None)

    def __call__(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        workdir, cleanup = self._make_workdir(request.job_id)
        try:
            scripts_dir = workdir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)

            for item in sorted(request.plan.items, key=lambda plan_item: plan_item.inject_order):
                rendered_script = str(item.render_context.get("rendered_script", ""))
                stem = item.kind
                if item.target is not None:
                    stem = item.target.method_name
                elif item.kind == "template_hook":
                    stem = str(item.render_context.get("template_name", item.kind))
                elif item.kind == "custom_script":
                    stem = str(item.render_context.get("script_name", item.kind))
                script_path = scripts_dir / f"{item.inject_order:02d}_{_slug(stem)}.js"
                script_path.write_text(rendered_script, encoding="utf-8")

            plan_path = workdir / "plan.json"
            plan_path.write_text(
                json.dumps(_serialize_plan(request.plan), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            stdout_path = workdir / "stdout.log"
            stderr_path = workdir / "stderr.log"

            env = os.environ.copy()
            env.update(self._extra_env)
            env.update(request.runtime_env)
            env.update(
                {
                    "APKHACKER_JOB_ID": request.job_id,
                    "APKHACKER_PLAN_PATH": str(plan_path),
                    "APKHACKER_SCRIPTS_DIR": str(scripts_dir),
                    "APKHACKER_WORKDIR": str(workdir),
                }
            )
            if request.package_name:
                env["APKHACKER_TARGET_PACKAGE"] = request.package_name
            if request.sample_path is not None:
                env["APKHACKER_SAMPLE_PATH"] = str(request.sample_path)
            completed = subprocess.run(
                shlex.split(self._command),
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            if completed.returncode != 0:
                stderr = completed.stderr.strip()
                stdout = completed.stdout.strip()
                detail = stderr or stdout or f"exit code {completed.returncode}"
                if self._artifact_root is not None:
                    detail = f"{detail}. Artifacts saved to {workdir}"
                raise ExecutionBackendUnavailable(f"Real device execution failed: {detail}")
            parsed_events = _parse_events(request.job_id, completed.stdout)
            if self._artifact_root is None:
                return parsed_events
            return (
                _run_bundle_event(
                    request.job_id,
                    workdir=workdir,
                    plan_path=plan_path,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    command=self._command,
                ),
                *parsed_events,
            )
        finally:
            cleanup()


class RealExecutionBackend(ExecutionBackend):
    def __init__(
        self,
        runner: Callable[[ExecutionRequest], tuple[HookEvent, ...]] | None = None,
        command: str | None = None,
        extra_env: Mapping[str, str] | None = None,
        artifact_root: Path | None = None,
    ) -> None:
        resolved_runner = runner
        resolved_command = command or os.environ.get(ENV_COMMAND)
        if resolved_runner is None and resolved_command:
            resolved_runner = CommandExecutionRunner(
                resolved_command,
                extra_env=extra_env,
                artifact_root=artifact_root,
            )
        self._runner = resolved_runner

    @property
    def configured(self) -> bool:
        return self._runner is not None

    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        if self._runner is None:
            raise ExecutionBackendUnavailable(
                f"Real device execution is not available because the backend is not configured. "
                f"Set {ENV_COMMAND} or inject a real backend runner."
            )
        return self._runner(request)
