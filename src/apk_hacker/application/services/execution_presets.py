from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionPreset:
    key: str
    label: str


EXECUTION_PRESETS: tuple[ExecutionPreset, ...] = (
    ExecutionPreset(key="fake_backend", label="Fake Backend"),
    ExecutionPreset(key="real_device", label="Real Device"),
    ExecutionPreset(key="real_adb_probe", label="ADB Probe"),
    ExecutionPreset(key="real_frida_probe", label="Frida Probe"),
    ExecutionPreset(key="real_frida_inject", label="Frida Inject"),
    ExecutionPreset(key="real_frida_session", label="Frida Session"),
)
