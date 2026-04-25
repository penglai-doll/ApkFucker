from __future__ import annotations

import argparse
import json
import shutil
import subprocess


def _command_path(name: str) -> str:
    return shutil.which(name) or name


def _run_adb(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_command_path("adb"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _list_devices() -> list[str]:
    completed = _run_adb("devices")
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "adb devices failed")
    devices: list[str] = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("List of devices"):
            continue
        serial, _, state = stripped.partition("\t")
        if state == "device":
            devices.append(serial)
    return devices


def _getprop(serial: str, key: str) -> str | None:
    completed = _run_adb("-s", serial, "shell", "getprop", key)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-adb-probe-backend",
        description="Emit structured device status events using adb.",
    )
    parser.parse_args()

    devices = _list_devices()
    if not devices:
        print(
            json.dumps(
                {
                    "event_type": "device_status",
                    "class_name": "adb",
                    "method_name": "no_device",
                    "arguments": (),
                    "return_value": "no-device",
                    "stacktrace": "",
                },
                ensure_ascii=False,
            )
        )
        return 0

    for serial in devices:
        print(
            json.dumps(
                {
                    "event_type": "device_connected",
                    "class_name": "adb.device",
                    "method_name": serial,
                    "arguments": ("device",),
                    "return_value": "connected",
                    "stacktrace": "",
                },
                ensure_ascii=False,
            )
        )
        arch = _getprop(serial, "ro.product.cpu.abi")
        if arch is not None:
            print(
                json.dumps(
                    {
                        "event_type": "device_property",
                        "class_name": "adb.device",
                        "method_name": serial,
                        "arguments": ("ro.product.cpu.abi",),
                        "return_value": arch,
                        "stacktrace": "",
                    },
                    ensure_ascii=False,
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
