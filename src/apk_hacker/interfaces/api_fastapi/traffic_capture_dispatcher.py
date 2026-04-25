from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import signal
import subprocess
import uuid

from apk_hacker.application.services.live_capture_runtime import LiveCaptureRuntimeAvailability
from apk_hacker.application.services.live_capture_runtime import build_live_capture_preview_path
from apk_hacker.application.services.live_capture_runtime import resolve_live_capture_runtime
from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_CASE_ID_ENV
from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_LISTEN_HOST_ENV
from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_LISTEN_PORT_ENV
from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_OUTPUT_PATH_ENV
from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_PREVIEW_PATH_ENV
from apk_hacker.application.services.live_capture_runtime import TRAFFIC_CAPTURE_SESSION_ID_ENV
from apk_hacker.domain.models.traffic import TrafficLiveCaptureState

TRAFFIC_CAPTURE_NOT_CONFIGURED_MESSAGE = (
    "未配置实时抓包命令，请设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND。"
)
TRAFFIC_CAPTURE_RUNNING_MESSAGE = "实时抓包进行中。"
TRAFFIC_CAPTURE_STARTED_MESSAGE = "已开始实时抓包。"
TRAFFIC_CAPTURE_ALREADY_RUNNING_MESSAGE = "实时抓包已在进行中。"
TRAFFIC_CAPTURE_NOT_RUNNING_MESSAGE = "当前没有正在进行的实时抓包。"


def _split_command_template(command_template: str) -> list[str]:
    parts = shlex.split(command_template, posix=os.name != "nt")
    if os.name != "nt":
        return parts
    return [
        part[1:-1] if len(part) >= 2 and part[0] == part[-1] and part[0] in {"'", '"'} else part
        for part in parts
    ]


def _popen_creationflags() -> int:
    if os.name != "nt":
        return 0
    return int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def _request_process_stop(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
        if ctrl_break is not None:
            try:
                process.send_signal(ctrl_break)
                return
            except OSError:
                pass
    process.terminate()


@dataclass(slots=True)
class _LiveTrafficCaptureSession:
    session_id: str
    output_path: Path
    preview_path: Path
    process: subprocess.Popen[bytes]


class TrafficCaptureDispatcher:
    def __init__(
        self,
        *,
        command_template: str | None = None,
        resolver=None,
        runtime_resolver: Callable[[], LiveCaptureRuntimeAvailability] | None = None,
    ) -> None:
        self._runtime_resolver = runtime_resolver
        self._runtime = resolve_live_capture_runtime(
            command_template=command_template,
            resolver=resolver,
        )
        self._sessions: dict[str, _LiveTrafficCaptureSession] = {}

    def is_configured(self) -> bool:
        return self._resolve_runtime().command_template is not None

    def runtime(self) -> LiveCaptureRuntimeAvailability:
        return self._resolve_runtime()

    def _resolve_runtime(self) -> LiveCaptureRuntimeAvailability:
        if self._runtime_resolver is not None:
            return self._runtime_resolver()
        return self._runtime

    def snapshot(self, *, case_id: str, persisted_state: TrafficLiveCaptureState) -> TrafficLiveCaptureState:
        session = self._sessions.get(case_id)
        if session is None:
            if persisted_state.status == "running":
                return TrafficLiveCaptureState(
                    status="stopped",
                    session_id=persisted_state.session_id,
                    output_path=persisted_state.output_path,
                    preview_path=persisted_state.preview_path,
                    message="实时抓包会话已与当前 API 进程断开。",
                )
            if not self.is_configured() and persisted_state.status in {"idle", "unavailable"}:
                return TrafficLiveCaptureState(
                    status="unavailable",
                    message=TRAFFIC_CAPTURE_NOT_CONFIGURED_MESSAGE,
                )
            if self.is_configured() and persisted_state.status == "unavailable":
                return TrafficLiveCaptureState(status="idle")
            return persisted_state

        return_code = session.process.poll()
        if return_code is None:
            return TrafficLiveCaptureState(
                status="running",
                session_id=session.session_id,
                output_path=session.output_path,
                preview_path=session.preview_path,
                message=TRAFFIC_CAPTURE_RUNNING_MESSAGE,
            )

        self._sessions.pop(case_id, None)
        return TrafficLiveCaptureState(
            status="stopped",
            session_id=session.session_id,
            output_path=session.output_path,
            preview_path=session.preview_path,
            message=f"实时抓包进程已退出，退出码 {return_code}。",
        )

    def start(self, *, case_id: str, output_path: Path) -> TrafficLiveCaptureState:
        runtime = self._resolve_runtime()
        if runtime.command_template is None:
            return TrafficLiveCaptureState(
                status="unavailable",
                message=TRAFFIC_CAPTURE_NOT_CONFIGURED_MESSAGE,
            )

        current = self.snapshot(case_id=case_id, persisted_state=TrafficLiveCaptureState(status="idle"))
        if current.status == "running":
            return TrafficLiveCaptureState(
                status="running",
                session_id=current.session_id,
                output_path=current.output_path,
                message=TRAFFIC_CAPTURE_ALREADY_RUNNING_MESSAGE,
            )

        session_id = output_path.stem
        preview_path = build_live_capture_preview_path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()
        if preview_path.exists():
            preview_path.unlink()
        process = subprocess.Popen(
            self._build_command(
                case_id=case_id,
                session_id=session_id,
                output_path=output_path,
                preview_path=preview_path,
                runtime=runtime,
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self._build_env(
                case_id=case_id,
                session_id=session_id,
                output_path=output_path,
                preview_path=preview_path,
                runtime=runtime,
            ),
            creationflags=_popen_creationflags(),
        )
        self._sessions[case_id] = _LiveTrafficCaptureSession(
            session_id=session_id,
            output_path=output_path,
            preview_path=preview_path,
            process=process,
        )
        return TrafficLiveCaptureState(
            status="running",
            session_id=session_id,
            output_path=output_path,
            preview_path=preview_path,
            message=TRAFFIC_CAPTURE_STARTED_MESSAGE,
        )

    def stop(self, *, case_id: str, persisted_state: TrafficLiveCaptureState) -> TrafficLiveCaptureState:
        session = self._sessions.pop(case_id, None)
        if session is None:
            if not self.is_configured() and persisted_state.status in {"idle", "unavailable"}:
                return TrafficLiveCaptureState(
                    status="unavailable",
                    message=TRAFFIC_CAPTURE_NOT_CONFIGURED_MESSAGE,
                )
            if persisted_state.status == "running":
                return TrafficLiveCaptureState(
                    status="stopped",
                    session_id=persisted_state.session_id,
                    output_path=persisted_state.output_path,
                    preview_path=persisted_state.preview_path,
                    message="实时抓包会话已与当前 API 进程断开。",
                )
            if persisted_state.status == "idle":
                return TrafficLiveCaptureState(
                    status="idle",
                    message=TRAFFIC_CAPTURE_NOT_RUNNING_MESSAGE,
                )
            return persisted_state

        return_code = session.process.poll()
        if return_code is None:
            _request_process_stop(session.process)
            try:
                return_code = session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                session.process.kill()
                return_code = session.process.wait(timeout=5)

        message = None
        if return_code not in (0, None):
            message = f"实时抓包进程已退出，退出码 {return_code}。"
        return TrafficLiveCaptureState(
            status="stopped",
            session_id=session.session_id,
            output_path=session.output_path,
            preview_path=session.preview_path,
            message=message,
        )

    @staticmethod
    def new_session_id() -> str:
        return uuid.uuid4().hex

    def _build_command(
        self,
        *,
        case_id: str,
        session_id: str,
        output_path: Path,
        preview_path: Path,
        runtime: LiveCaptureRuntimeAvailability,
    ) -> list[str]:
        if runtime.command_template is None:
            raise RuntimeError(TRAFFIC_CAPTURE_NOT_CONFIGURED_MESSAGE)
        parts = _split_command_template(runtime.command_template)
        if not parts:
            raise RuntimeError(TRAFFIC_CAPTURE_NOT_CONFIGURED_MESSAGE)
        replacements = {
            "{case_id}": case_id,
            "{session_id}": session_id,
            "{output_path}": str(output_path),
            "{preview_path}": str(preview_path),
            "{listen_host}": runtime.listen_host,
            "{listen_port}": str(runtime.listen_port),
        }
        resolved_parts: list[str] = []
        for part in parts:
            resolved = part
            for placeholder, value in replacements.items():
                resolved = resolved.replace(placeholder, value)
            resolved_parts.append(resolved)
        return resolved_parts

    def _build_env(
        self,
        *,
        case_id: str,
        session_id: str,
        output_path: Path,
        preview_path: Path,
        runtime: LiveCaptureRuntimeAvailability,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env[TRAFFIC_CAPTURE_CASE_ID_ENV] = case_id
        env[TRAFFIC_CAPTURE_SESSION_ID_ENV] = session_id
        env[TRAFFIC_CAPTURE_OUTPUT_PATH_ENV] = str(output_path)
        env[TRAFFIC_CAPTURE_PREVIEW_PATH_ENV] = str(preview_path)
        env[TRAFFIC_CAPTURE_LISTEN_HOST_ENV] = runtime.listen_host
        env[TRAFFIC_CAPTURE_LISTEN_PORT_ENV] = str(runtime.listen_port)
        return env
