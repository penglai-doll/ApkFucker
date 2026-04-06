from __future__ import annotations

from pathlib import Path


def build_execution_backend_env(
    *,
    device_serial: str | None = None,
    frida_server_binary: Path | None = None,
    frida_server_remote_path: str | None = None,
    frida_session_seconds: float | None = None,
) -> dict[str, str]:
    env: dict[str, str] = {}
    if device_serial:
        env["APKHACKER_DEVICE_SERIAL"] = device_serial
    if frida_server_binary is not None:
        env["APKHACKER_FRIDA_SERVER_BINARY"] = str(frida_server_binary)
    if frida_server_remote_path:
        env["APKHACKER_FRIDA_SERVER_REMOTE_PATH"] = frida_server_remote_path
    if frida_session_seconds is not None:
        env["APKHACKER_FRIDA_SESSION_SECONDS"] = str(frida_session_seconds)
    return env
