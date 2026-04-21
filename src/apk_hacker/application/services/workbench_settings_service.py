from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkbenchSettings:
    sample_path: str = ""
    execution_mode: str = "fake_backend"
    device_serial: str = ""
    frida_server_binary_path: str = ""
    frida_server_remote_path: str = ""
    frida_session_seconds: str = ""
    live_capture_listen_host: str = "0.0.0.0"
    live_capture_listen_port: str = "8080"


class WorkbenchSettingsService:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> WorkbenchSettings:
        if not self._path.exists():
            return WorkbenchSettings()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return WorkbenchSettings()
        if not isinstance(payload, dict):
            return WorkbenchSettings()
        return WorkbenchSettings(
            sample_path=str(payload.get("sample_path", "") or ""),
            execution_mode=str(payload.get("execution_mode", "fake_backend") or "fake_backend"),
            device_serial=str(payload.get("device_serial", "") or ""),
            frida_server_binary_path=str(payload.get("frida_server_binary_path", "") or ""),
            frida_server_remote_path=str(payload.get("frida_server_remote_path", "") or ""),
            frida_session_seconds=str(payload.get("frida_session_seconds", "") or ""),
            live_capture_listen_host=str(payload.get("live_capture_listen_host", "0.0.0.0") or "0.0.0.0"),
            live_capture_listen_port=str(payload.get("live_capture_listen_port", "8080") or "8080"),
        )

    def save(self, settings: WorkbenchSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._path)
