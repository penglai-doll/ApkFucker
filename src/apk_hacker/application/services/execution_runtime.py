from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import sys

from apk_hacker.application.services.execution_presets import build_execution_preset_statuses
from apk_hacker.application.services.execution_presets import label_for_preset
from apk_hacker.application.services.execution_presets import resolve_real_device_backend
from apk_hacker.domain.models.environment import EnvironmentSnapshot
from apk_hacker.infrastructure.execution.backend import ExecutionBackend
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


PRESET_COMMAND_MODULES: dict[str, str] = {
    "real_adb_probe": "apk_hacker.tools.adb_probe_backend",
    "real_frida_bootstrap": "apk_hacker.tools.frida_bootstrap_backend",
    "real_frida_probe": "apk_hacker.tools.frida_probe_backend",
    "real_frida_inject": "apk_hacker.tools.frida_inject_backend",
    "real_frida_session": "apk_hacker.tools.frida_session_backend",
}


@dataclass(frozen=True, slots=True)
class ExecutionRouting:
    requested_mode: str
    executed_backend_key: str
    executed_backend_label: str


def build_execution_backend_env(
    *,
    device_serial: str | None = None,
    frida_server_binary: Path | None = None,
    frida_server_remote_path: str | None = None,
    frida_session_seconds: float | None = None,
) -> dict[str, str]:
    env: dict[str, str] = {}
    if device_serial:
        env["APKHACKER_DEVICE_SERIAL"] = device_serial
    if frida_server_binary is not None:
        env["APKHACKER_FRIDA_SERVER_BINARY"] = str(frida_server_binary)
    if frida_server_remote_path:
        env["APKHACKER_FRIDA_SERVER_REMOTE_PATH"] = frida_server_remote_path
    if frida_session_seconds is not None:
        env["APKHACKER_FRIDA_SESSION_SECONDS"] = str(frida_session_seconds)
    return env


def build_execution_backend(
    execution_mode: str,
    *,
    artifact_root: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
    real_device_command: str | None = None,
) -> ExecutionBackend:
    if execution_mode == "fake_backend":
        return FakeExecutionBackend()
    if execution_mode == "real_device":
        return RealExecutionBackend(
            command=real_device_command,
            extra_env=extra_env,
            artifact_root=artifact_root,
        )
    module_name = PRESET_COMMAND_MODULES.get(execution_mode)
    if module_name is None:
        raise ValueError(f"Unsupported execution mode: {execution_mode}")
    return RealExecutionBackend(
        command=f"{sys.executable} -m {module_name}",
        extra_env=extra_env,
        artifact_root=artifact_root,
    )


def build_execution_backends(
    *,
    artifact_root: Path | None = None,
    extra_env: Mapping[str, str] | None = None,
    real_device_command: str | None = None,
) -> dict[str, ExecutionBackend]:
    backends: dict[str, ExecutionBackend] = {}
    for execution_mode in ("fake_backend", "real_device", *PRESET_COMMAND_MODULES.keys()):
        backends[execution_mode] = build_execution_backend(
            execution_mode,
            artifact_root=artifact_root,
            extra_env=extra_env,
            real_device_command=real_device_command,
        )
    return backends


def build_execution_runtime_availability(
    *,
    extra_env: Mapping[str, str] | None = None,
    real_device_command: str | None = None,
) -> dict[str, bool]:
    backends = build_execution_backends(
        artifact_root=None,
        extra_env=extra_env,
        real_device_command=real_device_command,
    )
    availability: dict[str, bool] = {}
    for execution_mode, backend in backends.items():
        if isinstance(backend, RealExecutionBackend):
            availability[execution_mode] = backend.configured
        else:
            availability[execution_mode] = True
    return availability


def resolve_execution_routing(
    requested_mode: str,
    *,
    snapshot: EnvironmentSnapshot,
    runtime_availability: Mapping[str, bool],
) -> ExecutionRouting:
    if requested_mode != "real_device":
        return ExecutionRouting(
            requested_mode=requested_mode,
            executed_backend_key=requested_mode,
            executed_backend_label=label_for_preset(requested_mode),
        )

    if runtime_availability.get("real_device", False):
        return ExecutionRouting(
            requested_mode=requested_mode,
            executed_backend_key="real_device",
            executed_backend_label=label_for_preset("real_device"),
        )

    statuses = build_execution_preset_statuses(snapshot, dict(runtime_availability))
    resolved_backend_key = resolve_real_device_backend(statuses) or "real_device"
    return ExecutionRouting(
        requested_mode=requested_mode,
        executed_backend_key=resolved_backend_key,
        executed_backend_label=label_for_preset(resolved_backend_key),
    )
