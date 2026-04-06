from pathlib import Path
import json
import os
import sys

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def _write_fake_frida_module(path: Path) -> Path:
    module_path = path / "frida.py"
    module_path.write_text(
        """
from __future__ import annotations

import json
import os
from pathlib import Path


STATE_PATH = Path(os.environ["APKHACKER_FAKE_FRIDA_STATE"])


def _append(record: dict[str, object]) -> None:
    with STATE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\\n")


class FakeScript:
    def __init__(self, source: str) -> None:
        self._source = source
        self._callback = None

    def on(self, event_name: str, callback) -> None:
        _append({"op": "script.on", "event_name": event_name})
        self._callback = callback

    def load(self) -> None:
        _append({"op": "script.load", "source_length": len(self._source)})
        payload = json.dumps(
            {
                "event_type": "method_call",
                "class_name": "com.demo.net.Config",
                "method_name": "buildUploadUrl",
                "arguments": ["plaintext"],
                "return_value": "ciphertext",
                "stacktrace": "com.demo.net.Config.buildUploadUrl:1",
            },
            ensure_ascii=False,
        )
        self._callback({"type": "send", "payload": payload}, None)


class FakeSession:
    def create_script(self, source: str) -> FakeScript:
        _append({"op": "session.create_script"})
        return FakeScript(source)

    def detach(self) -> None:
        _append({"op": "session.detach"})


class FakeDevice:
    def spawn(self, argv: list[str]) -> int:
        _append({"op": "device.spawn", "argv": argv})
        return 4321

    def attach(self, pid: int) -> FakeSession:
        _append({"op": "device.attach", "pid": pid})
        return FakeSession()

    def resume(self, pid: int) -> None:
        _append({"op": "device.resume", "pid": pid})


def get_usb_device(timeout: int | None = None) -> FakeDevice:
    _append({"op": "frida.get_usb_device", "timeout": timeout})
    return FakeDevice()
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return module_path


def test_packaged_frida_session_backend_forwards_script_messages(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-state.jsonl"
    _write_fake_frida_module(tmp_path)
    pythonpath = os.environ.get("PYTHONPATH", "")
    env_pythonpath = f"{tmp_path}:{pythonpath}" if pythonpath else str(tmp_path)
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="sources/com/demo/net/Config.java",
        line_hint=4,
    )
    plan = HookPlanService().plan_for_methods([method])
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_session_backend",
        extra_env={
            "PYTHONPATH": env_pythonpath,
            "APKHACKER_FAKE_FRIDA_STATE": str(state_file),
            "APKHACKER_FRIDA_SESSION_SECONDS": "0.1",
        },
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
        )
    )

    records = [
        json.loads(line)
        for line in state_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["op"] for record in records] == [
        "frida.get_usb_device",
        "device.spawn",
        "device.attach",
        "session.create_script",
        "script.on",
        "script.load",
        "device.resume",
        "session.detach",
    ]
    assert records[1]["argv"] == ["com.demo.shell"]
    assert len(events) == 1
    assert events[0].event_type == "method_call"
    assert events[0].method_name == "buildUploadUrl"
    assert events[0].arguments == ("plaintext",)
