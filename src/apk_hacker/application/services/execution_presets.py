from __future__ import annotations

from dataclasses import dataclass

from apk_hacker.domain.models.environment import EnvironmentSnapshot


@dataclass(frozen=True, slots=True)
class ExecutionPreset:
    key: str
    label: str
    required_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExecutionPresetStatus:
    key: str
    label: str
    available: bool
    detail: str


EXECUTION_PRESETS: tuple[ExecutionPreset, ...] = (
    ExecutionPreset(key="fake_backend", label="Fake Backend"),
    ExecutionPreset(key="real_device", label="Real Device"),
    ExecutionPreset(key="real_adb_probe", label="ADB Probe", required_tools=("adb",)),
    ExecutionPreset(key="real_frida_probe", label="Frida Probe", required_tools=("frida",)),
    ExecutionPreset(key="real_frida_inject", label="Frida Inject", required_tools=("frida",)),
    ExecutionPreset(key="real_frida_session", label="Frida Session", required_tools=("python-frida",)),
)

REAL_DEVICE_PRIORITY: tuple[str, ...] = (
    "real_frida_session",
    "real_frida_inject",
    "real_frida_probe",
    "real_adb_probe",
)


def resolve_real_device_backend(statuses: tuple[ExecutionPresetStatus, ...]) -> str | None:
    by_key = {status.key: status for status in statuses}
    for key in REAL_DEVICE_PRIORITY:
        status = by_key.get(key)
        if status is not None and status.available:
            return key
    return None


def build_execution_preset_statuses(
    snapshot: EnvironmentSnapshot,
    runtime_availability: dict[str, bool] | None = None,
) -> tuple[ExecutionPresetStatus, ...]:
    runtime_flags = runtime_availability or {}
    statuses_by_key: dict[str, ExecutionPresetStatus] = {}
    for preset in EXECUTION_PRESETS:
        if preset.key == "real_device":
            continue
        missing_tools = [tool for tool in preset.required_tools if not snapshot.tool_available(tool)]
        runtime_ready = runtime_flags.get(preset.key, True)
        if missing_tools:
            statuses_by_key[preset.key] = ExecutionPresetStatus(
                key=preset.key,
                label=preset.label,
                available=False,
                detail=f"unavailable (missing {', '.join(missing_tools)})",
            )
            continue
        if not runtime_ready:
            statuses_by_key[preset.key] = ExecutionPresetStatus(
                key=preset.key,
                label=preset.label,
                available=False,
                detail="unavailable (not configured)",
            )
            continue
        statuses_by_key[preset.key] = ExecutionPresetStatus(
            key=preset.key,
            label=preset.label,
            available=True,
            detail="ready",
        )

    real_device_runtime_ready = runtime_flags.get("real_device", False)
    if real_device_runtime_ready:
        statuses_by_key["real_device"] = ExecutionPresetStatus(
            key="real_device",
            label="Real Device",
            available=True,
            detail="ready (custom)",
        )
    else:
        recommended_key = resolve_real_device_backend(tuple(statuses_by_key.values()))
        if recommended_key is None:
            statuses_by_key["real_device"] = ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=False,
                detail="unavailable (no ready backend)",
            )
        else:
            recommended_label = statuses_by_key[recommended_key].label
            statuses_by_key["real_device"] = ExecutionPresetStatus(
                key="real_device",
                label="Real Device",
                available=True,
                detail=f"ready ({recommended_label})",
            )

    ordered_statuses: list[ExecutionPresetStatus] = []
    for preset in EXECUTION_PRESETS:
        ordered_statuses.append(statuses_by_key[preset.key])
    return tuple(ordered_statuses)
