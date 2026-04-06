from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any


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
    try:
        frida = _load_frida_module()
    except Exception as exc:
        events.append(_session_error_event("module_import", target_package, str(exc)))
        return _emit_events(events)

    try:
        device = frida.get_usb_device(timeout=5)
    except Exception as exc:
        events.append(_session_error_event("device_connect", target_package, str(exc)))
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
