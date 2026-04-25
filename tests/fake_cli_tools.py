from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import textwrap


def prepend_path(path: Path) -> str:
    return f"{path}{os.pathsep}{os.environ['PATH']}"


def _write_python_tool(directory: Path, name: str, code: str) -> Path:
    script_path = directory / f"{name}.py"
    script_path.write_text(code, encoding="utf-8")
    if os.name == "nt":
        wrapper_path = directory / f"{name}.cmd"
        wrapper_path.write_text(
            f'@echo off\r\n"{sys.executable}" "{script_path}" %*\r\n',
            encoding="utf-8",
        )
        return wrapper_path

    wrapper_path = directory / name
    wrapper_path.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{script_path}" "$@"\n',
        encoding="utf-8",
    )
    wrapper_path.chmod(0o755)
    return wrapper_path


def write_fake_frida(directory: Path, args_file: Path) -> Path:
    code = textwrap.dedent(
        f"""
        from __future__ import annotations

        import pathlib
        import sys
        pathlib.Path({str(args_file)!r}).write_text("\\n".join(sys.argv[1:]) + "\\n", encoding="utf-8")
        """
    ).strip() + "\n"
    return _write_python_tool(directory, "frida", code)


def write_fake_frida_ps(directory: Path, *, visible: bool) -> Path:
    target_line = "4321  Demo  com.demo.shell\n" if visible else "1234  Other  com.other.app\n"
    code = textwrap.dedent(
        f"""
        from __future__ import annotations

        import sys

        sys.stdout.write(" PID  Name  Identifier\\n")
        sys.stdout.write({target_line!r})
        """
    ).strip() + "\n"
    return _write_python_tool(directory, "frida-ps", code)


def write_fake_adb_from_shell(directory: Path, script: str) -> Path:
    state_file = _extract_state_file(script)
    ready_marker = _extract_ready_marker(script)
    config = {
        "devices": _extract_devices(script),
        "arch": "arm64-v8a" if "arm64-v8a" in script else None,
        "rooted": "uid=0(root)" in script,
        "running_pid": _extract_literal_pid(script, "2451"),
        "start_pid": (
            _extract_literal_pid(script, "9001")
            or _extract_literal_pid(script, "9999")
            or _extract_literal_pid(script, "31337")
        ),
        "state_file": state_file,
        "ready_marker": ready_marker,
        "record_pm_path": "pm-path:" in script,
        "record_install": "install:" in script,
        "record_push": "push:" in script,
        "record_shell": "shell:" in script,
    }
    code = textwrap.dedent(
        f"""
        from __future__ import annotations

        import json
        from pathlib import Path
        import sys

        CONFIG = json.loads({json.dumps(config)!r})
        args = sys.argv[1:]

        def append(record: str) -> None:
            state_file = CONFIG.get("state_file")
            if not state_file:
                return
            path = Path(state_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(record + "\\n")

        def started_path() -> Path | None:
            ready_marker = CONFIG.get("ready_marker")
            if ready_marker:
                return Path(ready_marker)
            state_file = CONFIG.get("state_file")
            if not state_file:
                return None
            return Path(str(state_file) + ".started")

        def selected_serial() -> str:
            devices = CONFIG.get("devices") or []
            return devices[0] if devices else "serial-123"

        if args == ["devices"]:
            sys.stdout.write("List of devices attached\\n")
            for serial in CONFIG.get("devices") or []:
                sys.stdout.write(f"{{serial}}\\tdevice\\n")
            raise SystemExit(0)

        if len(args) >= 5 and args[0] == "-s" and args[2:5] == ["shell", "getprop", "ro.product.cpu.abi"]:
            arch = CONFIG.get("arch")
            if arch:
                sys.stdout.write(str(arch) + "\\n")
                raise SystemExit(0)
            raise SystemExit(1)

        if len(args) >= 6 and args[0] == "-s" and args[2:5] == ["shell", "su", "-c"]:
            command = args[5]
            if command == "id":
                if CONFIG.get("rooted"):
                    sys.stdout.write("uid=0(root) gid=0(root)\\n")
                    raise SystemExit(0)
                raise SystemExit(1)
            if command == "pidof frida-server":
                running_pid = CONFIG.get("running_pid")
                start_pid = CONFIG.get("start_pid")
                marker = started_path()
                if running_pid:
                    sys.stdout.write(str(running_pid) + "\\n")
                elif start_pid and marker is not None and marker.exists():
                    sys.stdout.write(str(start_pid) + "\\n")
                raise SystemExit(0)
            if CONFIG.get("record_shell"):
                append(f"shell:{{command}}")
            if command == "chmod 755 /data/local/tmp/frida-server":
                raise SystemExit(0)
            if command == "/data/local/tmp/frida-server >/dev/null 2>&1 &":
                marker = started_path()
                if marker is not None:
                    marker.touch()
                raise SystemExit(0)
            raise SystemExit(1)

        if len(args) >= 6 and args[0] == "-s" and args[2:5] == ["shell", "pm", "path"]:
            if CONFIG.get("record_pm_path"):
                append(f"pm-path:{{args[5]}}")
            raise SystemExit(0)

        if len(args) >= 5 and args[0] == "-s" and args[2:4] == ["install", "-r"]:
            if CONFIG.get("record_install"):
                append(f"install:{{args[4]}}")
            sys.stdout.write("Success\\n")
            raise SystemExit(0)

        if len(args) >= 5 and args[0] == "-s" and args[2] == "push":
            if CONFIG.get("record_push"):
                append(f"push:{{args[3]}}->{{args[4]}}")
            raise SystemExit(0)

        raise SystemExit(1)
        """
    ).strip() + "\n"
    return _write_python_tool(directory, "adb", code)


def _extract_state_file(script: str) -> str | None:
    match = re.search(r'STATE_FILE="([^"]+)"', script)
    return match.group(1) if match else None


def _extract_ready_marker(script: str) -> str | None:
    match = re.search(r'READY_MARKER="([^"]+)"', script)
    return match.group(1) if match else None


def _extract_devices(script: str) -> list[str]:
    if "serial-123\\tdevice" in script or "serial-123\tdevice" in script:
        return ["serial-123"]
    return []


def _extract_literal_pid(script: str, pid: str) -> str | None:
    return pid if pid in script else None
