from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from apk_hacker.tools.frida_bootstrap_backend import (
    FRIDA_SERVER_BINARY_ENV,
    bootstrap_succeeded,
    collect_bootstrap_events,
    install_apk,
    list_connected_devices,
    package_path,
    pick_device_serial,
)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _warmup_seconds() -> float:
    raw_value = os.environ.get("APKHACKER_FRIDA_WARMUP_SECONDS", "1.5").strip()
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError("APKHACKER_FRIDA_WARMUP_SECONDS must be a number") from exc
    return max(value, 0.1)


def _select_script(scripts_dir: Path) -> Path:
    candidates = sorted(scripts_dir.glob("*.js"))
    if not candidates:
        raise RuntimeError(f"No rendered Frida scripts were found in {scripts_dir}")
    return candidates[0]


def _command_path(name: str) -> str:
    return shutil.which(name) or name


def _build_command(target_package: str, script_path: Path) -> list[str]:
    device_serial = os.environ.get("APKHACKER_DEVICE_SERIAL", "").strip()
    if device_serial:
        return [_command_path("frida"), "-D", device_serial, "-f", target_package, "-l", str(script_path)]
    return [_command_path("frida"), "-U", "-f", target_package, "-l", str(script_path)]


def _run_injection_probe(command: list[str], warmup_seconds: float) -> str:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        completed = process.wait(timeout=warmup_seconds)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)
        return "started"

    stdout, stderr = process.communicate()
    if completed != 0:
        detail = (stderr or stdout or f"exit code {completed}").strip()
        raise RuntimeError(detail)
    return "exited"


def _emit_events(events: list[dict[str, object]]) -> int:
    for event in events:
        print(json.dumps(event, ensure_ascii=False))
    return 0


def _install_status_event(
    target_package: str,
    sample_path: Path,
    detail: str,
    event_type: str = "app_install_status",
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "class_name": "adb.package",
        "method_name": target_package,
        "arguments": (str(sample_path),),
        "return_value": detail,
        "stacktrace": "",
    }


def _injection_error_event(target_package: str, detail: str) -> dict[str, object]:
    return {
        "event_type": "frida_injection_error",
        "class_name": "frida",
        "method_name": "spawn_attach",
        "arguments": (target_package,),
        "return_value": detail,
        "stacktrace": "",
    }


def _maybe_install_sample(target_package: str, events: list[dict[str, object]]) -> None:
    raw_sample_path = os.environ.get("APKHACKER_SAMPLE_PATH", "").strip()
    if not raw_sample_path:
        return
    sample_path = Path(raw_sample_path).expanduser().resolve()
    if not sample_path.exists():
        events.append(_install_status_event(target_package, sample_path, "missing-sample", event_type="app_install_error"))
        return
    try:
        serial = pick_device_serial(list_connected_devices())
        if package_path(serial, target_package) is not None:
            return
        install_apk(serial, sample_path)
        events.append(_install_status_event(target_package, sample_path, "installed"))
    except Exception as exc:
        events.append(_install_status_event(target_package, sample_path, str(exc), event_type="app_install_error"))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-frida-inject-backend",
        description="Run a minimal Frida spawn+load probe and emit a structured injection event.",
    )
    parser.parse_args()

    target_package = _require_env("APKHACKER_TARGET_PACKAGE")
    scripts_dir = Path(_require_env("APKHACKER_SCRIPTS_DIR")).expanduser().resolve()
    script_path = _select_script(scripts_dir)
    events: list[dict[str, object]] = []
    _maybe_install_sample(target_package, events)

    bootstrap_binary = os.environ.get(FRIDA_SERVER_BINARY_ENV, "").strip()
    if bootstrap_binary:
        bootstrap_events = collect_bootstrap_events()
        events.extend(bootstrap_events)
        if not bootstrap_succeeded(bootstrap_events):
            return _emit_events(events)

    try:
        status = _run_injection_probe(
            _build_command(target_package, script_path),
            _warmup_seconds(),
        )
    except Exception as exc:
        events.append(_injection_error_event(target_package, str(exc)))
        return _emit_events(events)

    events.append(
        {
            "event_type": "frida_injection",
            "class_name": "frida",
            "method_name": "spawn_attach",
            "arguments": (target_package, script_path.name),
            "return_value": status,
            "stacktrace": "",
        }
    )
    return _emit_events(events)


if __name__ == "__main__":
    raise SystemExit(main())
