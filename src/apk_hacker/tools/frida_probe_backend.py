from __future__ import annotations

import argparse
import json
import os
import subprocess


def _run_frida_ps() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["frida-ps", "-Uai"],
        capture_output=True,
        text=True,
        check=False,
    )


def _find_target_pid(stdout: str, target_package: str) -> str | None:
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("PID"):
            continue
        columns = stripped.split()
        if len(columns) < 3:
            continue
        package_name = columns[-1]
        pid = columns[0]
        if package_name == target_package:
            return pid
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-frida-probe-backend",
        description="Probe connected devices with frida-ps and emit structured target visibility events.",
    )
    parser.parse_args()

    target_package = os.environ.get("APKHACKER_TARGET_PACKAGE", "").strip()
    if not target_package:
        raise RuntimeError("APKHACKER_TARGET_PACKAGE is required")

    completed = _run_frida_ps()
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "frida-ps failed"
        raise RuntimeError(detail)

    pid = _find_target_pid(completed.stdout, target_package)
    if pid is None:
        print(
            json.dumps(
                {
                    "event_type": "frida_target",
                    "class_name": "frida",
                    "method_name": "missing",
                    "arguments": (),
                    "return_value": target_package,
                    "stacktrace": "",
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "event_type": "frida_target",
                "class_name": "frida",
                "method_name": "visible",
                "arguments": (target_package, pid),
                "return_value": "visible",
                "stacktrace": "",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
