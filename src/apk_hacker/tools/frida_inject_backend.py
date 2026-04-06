from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess


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


def _build_command(target_package: str, script_path: Path) -> list[str]:
    return ["frida", "-U", "-f", target_package, "-l", str(script_path)]


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


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-frida-inject-backend",
        description="Run a minimal Frida spawn+load probe and emit a structured injection event.",
    )
    parser.parse_args()

    target_package = _require_env("APKHACKER_TARGET_PACKAGE")
    scripts_dir = Path(_require_env("APKHACKER_SCRIPTS_DIR")).expanduser().resolve()
    script_path = _select_script(scripts_dir)
    status = _run_injection_probe(
        _build_command(target_package, script_path),
        _warmup_seconds(),
    )
    print(
        json.dumps(
            {
                "event_type": "frida_injection",
                "class_name": "frida",
                "method_name": "spawn_attach",
                "arguments": (target_package, script_path.name),
                "return_value": status,
                "stacktrace": "",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
