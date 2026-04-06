from apk_hacker.application.services.execution_presets import (
    build_execution_preset_statuses,
    resolve_real_device_backend,
)
from apk_hacker.domain.models.environment import EnvironmentSnapshot, ToolStatus


def test_execution_presets_select_best_real_device_backend() -> None:
    snapshot = EnvironmentSnapshot(
        tools=(
            ToolStatus(name="adb", label="adb", available=True, path="/opt/android/adb"),
            ToolStatus(name="frida", label="frida", available=True, path="/opt/homebrew/bin/frida"),
            ToolStatus(name="python-frida", label="python-frida", available=True, path="module:frida"),
        )
    )

    statuses = build_execution_preset_statuses(snapshot, runtime_availability={})

    assert resolve_real_device_backend(statuses) == "real_frida_session"
    real_device_status = next(status for status in statuses if status.key == "real_device")
    assert real_device_status.available is True
    assert real_device_status.detail == "ready (Frida Session)"


def test_execution_presets_fall_back_to_adb_probe_when_frida_is_missing() -> None:
    snapshot = EnvironmentSnapshot(
        tools=(
            ToolStatus(name="adb", label="adb", available=True, path="/opt/android/adb"),
            ToolStatus(name="frida", label="frida", available=False, path=None),
            ToolStatus(name="python-frida", label="python-frida", available=False, path=None),
        )
    )

    statuses = build_execution_preset_statuses(snapshot, runtime_availability={})

    assert resolve_real_device_backend(statuses) == "real_adb_probe"
    real_device_status = next(status for status in statuses if status.key == "real_device")
    assert real_device_status.available is True
    assert real_device_status.detail == "ready (ADB Probe)"
