from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any

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


def _session_seconds() -> float:
    raw_value = os.environ.get("APKHACKER_FRIDA_SESSION_SECONDS", "2.0").strip()
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError("APKHACKER_FRIDA_SESSION_SECONDS must be a number") from exc
    return max(value, 0.1)


def _select_scripts(scripts_dir: Path) -> list[Path]:
    candidates = sorted(scripts_dir.glob("*.js"))
    if not candidates:
        raise RuntimeError(f"No rendered Frida scripts were found in {scripts_dir}")
    return candidates


def _load_frida_module():
    try:
        import frida  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python frida module is not installed") from exc
    return frida


def _coerce_message(message: dict[str, Any], source_script: str | None = None) -> dict[str, object] | None:
    if message.get("type") == "send":
        payload = message.get("payload")
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                event = {
                    "event_type": "frida_message",
                    "class_name": "frida",
                    "method_name": "send",
                    "arguments": (payload,),
                    "return_value": None,
                    "stacktrace": "",
                }
                if source_script is not None:
                    event["source_script"] = source_script
                return event
            if isinstance(parsed, dict):
                if source_script is not None and "source_script" not in parsed:
                    parsed = {**parsed, "source_script": source_script}
                return parsed
        if isinstance(payload, dict):
            if source_script is not None and "source_script" not in payload:
                payload = {**payload, "source_script": source_script}
            return payload
    if message.get("type") == "error":
        event = {
            "event_type": "frida_script_error",
            "class_name": "frida",
            "method_name": "script_error",
            "arguments": (),
            "return_value": None,
            "stacktrace": str(message.get("stack", "")),
        }
        if source_script is not None:
            event["source_script"] = source_script
        return event
    return None


def _session_error_event(
    step: str,
    target_package: str,
    detail: str,
    source_script: str | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        "event_type": "frida_session_error",
        "class_name": "frida",
        "method_name": step,
        "arguments": (target_package,),
        "return_value": detail,
        "stacktrace": "",
    }
    if source_script is not None:
        event["source_script"] = source_script
    return event


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
        prog="apk-hacker-frida-session-backend",
        description="Run a minimal Frida session and forward script messages as structured events.",
    )
    parser.parse_args()

    target_package = _require_env("APKHACKER_TARGET_PACKAGE")
    scripts_dir = Path(_require_env("APKHACKER_SCRIPTS_DIR")).expanduser().resolve()
    script_paths = _select_scripts(scripts_dir)

    events: list[dict[str, object]] = []
    _maybe_install_sample(target_package, events)
    try:
        frida = _load_frida_module()
    except Exception as exc:
        events.append(_session_error_event("module_import", target_package, str(exc)))
        return _emit_events(events)

    try:
        device = frida.get_usb_device(timeout=5)
    except Exception as exc:
        bootstrap_binary = os.environ.get(FRIDA_SERVER_BINARY_ENV, "").strip()
        if not bootstrap_binary:
            events.append(_session_error_event("device_connect", target_package, str(exc)))
            return _emit_events(events)
        bootstrap_events = collect_bootstrap_events()
        events.extend(bootstrap_events)
        if not bootstrap_succeeded(bootstrap_events):
            events.append(_session_error_event("device_connect", target_package, str(exc)))
            return _emit_events(events)
        try:
            device = frida.get_usb_device(timeout=5)
        except Exception as retry_exc:
            events.append(_session_error_event("device_connect", target_package, str(retry_exc)))
            return _emit_events(events)

    try:
        pid = device.spawn([target_package])
    except Exception as exc:
        events.append(_session_error_event("spawn", target_package, str(exc)))
        return _emit_events(events)

    try:
        session = device.attach(pid)
    except Exception as exc:
        events.append(_session_error_event("attach", target_package, str(exc)))
        return _emit_events(events)

    for script_path in script_paths:
        def on_message(message: dict[str, Any], data: Any, *, _script_name: str = script_path.name) -> None:
            del data
            event = _coerce_message(message, source_script=_script_name)
            if event is not None:
                events.append(event)

        try:
            script = session.create_script(script_path.read_text(encoding="utf-8"))
            script.on("message", on_message)
            script.load()
        except Exception as exc:
            events.append(_session_error_event("script_load", target_package, str(exc), source_script=script_path.name))
            try:
                session.detach()
            except Exception as detach_exc:
                events.append(_session_error_event("detach", target_package, str(detach_exc)))
            return _emit_events(events)
    try:
        device.resume(pid)
    except Exception as exc:
        events.append(_session_error_event("resume", target_package, str(exc)))
        try:
            session.detach()
        except Exception as detach_exc:
            events.append(_session_error_event("detach", target_package, str(detach_exc)))
        return _emit_events(events)

    try:
        time.sleep(_session_seconds())
    finally:
        try:
            session.detach()
        except Exception as exc:
            events.append(_session_error_event("detach", target_package, str(exc)))

    if not events:
        events.append(
            {
                "event_type": "frida_session_timeout",
                "class_name": "frida",
                "method_name": "idle",
                "arguments": (target_package, f"{_session_seconds():.1f}s"),
                "return_value": "timeout",
                "stacktrace": "",
            }
        )

    return _emit_events(events)


if __name__ == "__main__":
    raise SystemExit(main())
