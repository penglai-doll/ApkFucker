from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


DEVICE_SERIAL_ENV = "APKHACKER_DEVICE_SERIAL"
FRIDA_SERVER_BINARY_ENV = "APKHACKER_FRIDA_SERVER_BINARY"
FRIDA_SERVER_REMOTE_PATH_ENV = "APKHACKER_FRIDA_SERVER_REMOTE_PATH"
FRIDA_SERVER_START_DELAY_ENV = "APKHACKER_FRIDA_SERVER_START_DELAY"
DEFAULT_REMOTE_PATH = "/data/local/tmp/frida-server"


def _command_path(name: str) -> str:
    return shutil.which(name) or name


def _event(
    event_type: str,
    class_name: str,
    method_name: str,
    arguments: tuple[str, ...] = (),
    return_value: str | None = None,
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "class_name": class_name,
        "method_name": method_name,
        "arguments": arguments,
        "return_value": return_value,
        "stacktrace": "",
    }


def _emit_events(events: list[dict[str, object]]) -> int:
    for event in events:
        print(json.dumps(event, ensure_ascii=False))
    return 0


def run_adb(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_command_path("adb"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def list_connected_devices() -> list[str]:
    completed = run_adb("devices")
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


def shell(serial: str, *args: str) -> subprocess.CompletedProcess[str]:
    return run_adb("-s", serial, "shell", *args)


def shell_su(serial: str, command: str) -> subprocess.CompletedProcess[str]:
    return shell(serial, "su", "-c", command)


def _first_line(completed: subprocess.CompletedProcess[str]) -> str | None:
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def getprop(serial: str, key: str) -> str | None:
    return _first_line(shell(serial, "getprop", key))


def is_rooted(serial: str) -> bool:
    completed = shell_su(serial, "id")
    return completed.returncode == 0 and "uid=0" in completed.stdout


def frida_server_pid(serial: str) -> str | None:
    return _first_line(shell_su(serial, "pidof frida-server"))


def _start_delay_seconds() -> float:
    raw_value = os.environ.get(FRIDA_SERVER_START_DELAY_ENV, "0.2").strip()
    try:
        value = float(raw_value)
    except ValueError:
        return 0.2
    return max(value, 0.0)


def pick_device_serial(devices: list[str]) -> str:
    preferred = os.environ.get(DEVICE_SERIAL_ENV, "").strip()
    if preferred:
        if preferred not in devices:
            raise RuntimeError(f"Requested device {preferred} is not connected")
        return preferred
    return devices[0]


def push_frida_server(serial: str, local_binary: Path, remote_path: str) -> None:
    completed = run_adb("-s", serial, "push", str(local_binary), remote_path)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "adb push failed")


def run_shell_step(serial: str, command: str) -> None:
    completed = shell_su(serial, command)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"Command failed: {command}")


def package_path(serial: str, package_name: str) -> str | None:
    return _first_line(shell(serial, "pm", "path", package_name))


def install_apk(serial: str, sample_path: Path) -> None:
    completed = run_adb("-s", serial, "install", "-r", str(sample_path))
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "adb install failed")


def collect_bootstrap_events() -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    try:
        devices = list_connected_devices()
    except Exception as exc:
        events.append(_event("device_error", "adb", "devices", return_value=str(exc)))
        return events

    if not devices:
        events.append(_event("device_status", "adb", "no_device", return_value="no-device"))
        return events

    try:
        serial = pick_device_serial(devices)
    except Exception as exc:
        events.append(_event("device_error", "adb", "select_device", return_value=str(exc)))
        return events

    events.append(_event("device_connected", "adb.device", serial, ("device",), "connected"))

    arch = getprop(serial, "ro.product.cpu.abi")
    if arch is not None:
        events.append(_event("device_property", "adb.device", serial, ("ro.product.cpu.abi",), arch))

    rooted = is_rooted(serial)
    root_value = "rooted" if rooted else "not-rooted"
    events.append(_event("device_root_status", "adb.device", serial, ("root",), root_value))
    if not rooted:
        events.append(_event("frida_server_status", "frida-server", serial, (DEFAULT_REMOTE_PATH,), "root-required"))
        return events

    pid = frida_server_pid(serial)
    remote_path = os.environ.get(FRIDA_SERVER_REMOTE_PATH_ENV, DEFAULT_REMOTE_PATH).strip() or DEFAULT_REMOTE_PATH
    if pid is not None:
        events.append(_event("frida_server_status", "frida-server", serial, (remote_path,), f"running:{pid}"))
        return events

    local_binary_raw = os.environ.get(FRIDA_SERVER_BINARY_ENV, "").strip()
    if not local_binary_raw:
        events.append(_event("frida_server_status", "frida-server", serial, (remote_path,), "missing-binary"))
        return events

    local_binary = Path(local_binary_raw).expanduser().resolve()
    if not local_binary.exists():
        events.append(_event("frida_server_error", "frida-server", serial, ("binary",), f"missing:{local_binary}"))
        return events

    try:
        push_frida_server(serial, local_binary, remote_path)
        events.append(_event("frida_server_action", "frida-server", serial, ("push", remote_path), str(local_binary)))
        run_shell_step(serial, f"chmod 755 {remote_path}")
        events.append(_event("frida_server_action", "frida-server", serial, ("chmod", remote_path), "ok"))
        run_shell_step(serial, f"{remote_path} >/dev/null 2>&1 &")
        events.append(_event("frida_server_action", "frida-server", serial, ("start", remote_path), "ok"))
        time.sleep(_start_delay_seconds())
        pid = frida_server_pid(serial)
        status = f"running:{pid}" if pid is not None else "start-failed"
        events.append(_event("frida_server_status", "frida-server", serial, (remote_path,), status))
    except Exception as exc:
        events.append(_event("frida_server_error", "frida-server", serial, ("bootstrap", remote_path), str(exc)))
    return events


def bootstrap_succeeded(events: list[dict[str, object]]) -> bool:
    return any(
        event.get("event_type") == "frida_server_status"
        and str(event.get("return_value", "")).startswith("running:")
        for event in events
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-frida-bootstrap-backend",
        description="Probe a connected Android device and optionally push/start frida-server.",
    )
    parser.parse_args()

    return _emit_events(collect_bootstrap_events())


if __name__ == "__main__":
    raise SystemExit(main())
