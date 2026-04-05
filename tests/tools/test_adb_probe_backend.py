from pathlib import Path
import os
import sys

from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def _write_fake_adb(path: Path, script: str) -> Path:
    adb_path = path / "adb"
    adb_path.write_text(script, encoding="utf-8")
    adb_path.chmod(0o755)
    return adb_path


def test_packaged_adb_probe_backend_reports_missing_devices(tmp_path: Path) -> None:
    _write_fake_adb(
        tmp_path,
        """#!/bin/sh
if [ "$1" = "devices" ]; then
  printf 'List of devices attached\\n\\n'
  exit 0
fi
exit 1
""",
    )
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.adb_probe_backend",
        extra_env={"PATH": env_path},
    )

    events = backend.execute("job-1", HookPlan(items=()))

    assert len(events) == 1
    assert events[0].event_type == "device_status"
    assert events[0].method_name == "no_device"
    assert events[0].return_value == "no-device"


def test_packaged_adb_probe_backend_reports_connected_device_and_arch(tmp_path: Path) -> None:
    _write_fake_adb(
        tmp_path,
        """#!/bin/sh
if [ "$1" = "devices" ]; then
  printf 'List of devices attached\\nserial-123\\tdevice\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$3" = "shell" ] && [ "$4" = "getprop" ] && [ "$5" = "ro.product.cpu.abi" ]; then
  printf 'arm64-v8a\\n'
  exit 0
fi
exit 1
""",
    )
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.adb_probe_backend",
        extra_env={"PATH": env_path},
    )

    events = backend.execute("job-1", HookPlan(items=()))

    assert [event.event_type for event in events] == ["device_connected", "device_property"]
    assert events[0].method_name == "serial-123"
    assert events[1].arguments == ("ro.product.cpu.abi",)
    assert events[1].return_value == "arm64-v8a"
