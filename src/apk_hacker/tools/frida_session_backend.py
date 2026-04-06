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


def _select_script(scripts_dir: Path) -> Path:
    candidates = sorted(scripts_dir.glob("*.js"))
    if not candidates:
        raise RuntimeError(f"No rendered Frida scripts were found in {scripts_dir}")
    return candidates[0]


def _load_frida_module():
    try:
        import frida  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python frida module is not installed") from exc
    return frida


def _coerce_message(message: dict[str, Any]) -> dict[str, object] | None:
    if message.get("type") == "send":
        payload = message.get("payload")
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                return {
                    "event_type": "frida_message",
                    "class_name": "frida",
                    "method_name": "send",
                    "arguments": (payload,),
                    "return_value": None,
                    "stacktrace": "",
                }
            if isinstance(parsed, dict):
                return parsed
        if isinstance(payload, dict):
            return payload
    if message.get("type") == "error":
        return {
            "event_type": "frida_script_error",
            "class_name": "frida",
            "method_name": "script_error",
            "arguments": (),
            "return_value": None,
            "stacktrace": str(message.get("stack", "")),
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-frida-session-backend",
        description="Run a minimal Frida session and forward script messages as structured events.",
    )
    parser.parse_args()

    target_package = _require_env("APKHACKER_TARGET_PACKAGE")
    scripts_dir = Path(_require_env("APKHACKER_SCRIPTS_DIR")).expanduser().resolve()
    script_path = _select_script(scripts_dir)
    script_source = script_path.read_text(encoding="utf-8")
    frida = _load_frida_module()

    events: list[dict[str, object]] = []
    device = frida.get_usb_device(timeout=5)
    pid = device.spawn([target_package])
    session = device.attach(pid)

    def on_message(message: dict[str, Any], data: Any) -> None:
        del data
        event = _coerce_message(message)
        if event is not None:
            events.append(event)

    script = session.create_script(script_source)
    script.on("message", on_message)
    try:
        script.load()
        device.resume(pid)
        time.sleep(_session_seconds())
    finally:
        session.detach()

    if not events:
        events.append(
            {
                "event_type": "frida_session",
                "class_name": "frida",
                "method_name": "attached",
                "arguments": (target_package, script_path.name),
                "return_value": "attached",
                "stacktrace": "",
            }
        )

    for event in events:
        print(json.dumps(event, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
