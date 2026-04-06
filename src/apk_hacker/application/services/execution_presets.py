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


def build_execution_preset_statuses(
    snapshot: EnvironmentSnapshot,
    runtime_availability: dict[str, bool] | None = None,
) -> tuple[ExecutionPresetStatus, ...]:
    runtime_flags = runtime_availability or {}
    statuses: list[ExecutionPresetStatus] = []
    for preset in EXECUTION_PRESETS:
        missing_tools = [tool for tool in preset.required_tools if not snapshot.tool_available(tool)]
        runtime_ready = runtime_flags.get(preset.key, True)
        if missing_tools:
            statuses.append(
                ExecutionPresetStatus(
                    key=preset.key,
                    label=preset.label,
                    available=False,
                    detail=f"unavailable (missing {', '.join(missing_tools)})",
                )
            )
            continue
        if not runtime_ready:
            statuses.append(
                ExecutionPresetStatus(
                    key=preset.key,
                    label=preset.label,
                    available=False,
                    detail="unavailable (not configured)",
                )
            )
            continue
        statuses.append(
            ExecutionPresetStatus(
                key=preset.key,
                label=preset.label,
                available=True,
                detail="ready",
            )
        )
    return tuple(statuses)
