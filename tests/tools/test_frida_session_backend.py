from pathlib import Path
import json
import os
import sys

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlanSource
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
        method_name = "unknown"
        arguments = []
        if "custom-one" in self._source:
            method_name = "custom-one"
            arguments = ["custom-one"]
        elif "custom-two" in self._source:
            method_name = "custom-two"
            arguments = ["custom-two"]
        elif "buildUploadUrl" in self._source:
            method_name = "buildUploadUrl"
            arguments = ["plaintext"]
        payload = json.dumps(
            {
                "event_type": "method_call",
                "class_name": "com.demo.net.Config",
                "method_name": method_name,
                "arguments": arguments,
                "return_value": "ciphertext",
                "stacktrace": f"com.demo.net.Config.{method_name}:1",
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


def test_packaged_frida_session_backend_honors_selected_device_serial(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-serial.jsonl"
    module_path = tmp_path / "frida.py"
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
                "arguments": ["serial"],
                "return_value": "ok",
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
        return 7777

    def attach(self, pid: int) -> FakeSession:
        _append({"op": "device.attach", "pid": pid})
        return FakeSession()

    def resume(self, pid: int) -> None:
        _append({"op": "device.resume", "pid": pid})


def get_device(device_id: str, timeout: int | None = None) -> FakeDevice:
    _append({"op": "frida.get_device", "device_id": device_id, "timeout": timeout})
    return FakeDevice()


def get_usb_device(timeout: int | None = None):
    _append({"op": "frida.get_usb_device", "timeout": timeout})
    raise AssertionError("get_usb_device should not be used when device serial is set")
""".strip()
        + "\n",
        encoding="utf-8",
    )
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
            "APKHACKER_DEVICE_SERIAL": "serial-123",
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
    assert records[0] == {
        "op": "frida.get_device",
        "device_id": "serial-123",
        "timeout": 5,
    }
    assert events[0].arguments == ("serial",)


def test_packaged_frida_session_backend_loads_all_scripts_in_plan_order(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-state.jsonl"
    _write_fake_frida_module(tmp_path)
    pythonpath = os.environ.get("PYTHONPATH", "")
    env_pythonpath = f"{tmp_path}:{pythonpath}" if pythonpath else str(tmp_path)
    custom_one = tmp_path / "custom-one.js"
    custom_one.write_text("send('custom-one');\n", encoding="utf-8")
    custom_two = tmp_path / "custom-two.js"
    custom_two.write_text("send('custom-two');\n", encoding="utf-8")
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
    plan = HookPlanService().plan_for_sources(
        [
            HookPlanSource.from_custom_script("custom-one", str(custom_one)),
            HookPlanSource.from_method(method),
            HookPlanSource.from_custom_script("custom-two", str(custom_two)),
        ]
    )
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
        "session.create_script",
        "script.on",
        "script.load",
        "session.create_script",
        "script.on",
        "script.load",
        "device.resume",
        "session.detach",
    ]
    assert [event.method_name for event in events] == [
        "custom-one",
        "buildUploadUrl",
        "custom-two",
    ]
    assert [event.raw_payload["source_script"] for event in events] == [
        "01_custom-one.js",
        "02_builduploadurl.js",
        "03_custom-two.js",
    ]


def test_packaged_frida_session_backend_emits_timeout_when_no_script_messages(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-timeout.jsonl"
    module_path = tmp_path / "frida.py"
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

    def on(self, event_name: str, callback) -> None:
        del callback
        _append({"op": "script.on", "event_name": event_name})

    def load(self) -> None:
        _append({"op": "script.load", "source_length": len(self._source)})


class FakeSession:
    def create_script(self, source: str) -> FakeScript:
        _append({"op": "session.create_script"})
        return FakeScript(source)

    def detach(self) -> None:
        _append({"op": "session.detach"})


class FakeDevice:
    def spawn(self, argv: list[str]) -> int:
        _append({"op": "device.spawn", "argv": argv})
        return 1001

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

    assert len(events) == 1
    assert events[0].event_type == "frida_session_timeout"
    assert events[0].method_name == "idle"
    assert events[0].arguments[0] == "com.demo.shell"


def test_packaged_frida_session_backend_classifies_device_connect_failures(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-connect-error.jsonl"
    module_path = tmp_path / "frida.py"
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


def get_usb_device(timeout: int | None = None):
    _append({"op": "frida.get_usb_device", "timeout": timeout})
    raise RuntimeError("usb device unavailable")
""".strip()
        + "\n",
        encoding="utf-8",
    )
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

    assert len(events) == 1
    assert events[0].event_type == "frida_session_error"
    assert events[0].method_name == "device_connect"
    assert "usb device unavailable" in (events[0].return_value or "")


def test_packaged_frida_session_backend_forwards_script_error_with_source(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-script-error.jsonl"
    module_path = tmp_path / "frida.py"
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
        self._callback({"type": "error", "stack": "boom"}, None)


class FakeSession:
    def create_script(self, source: str) -> FakeScript:
        _append({"op": "session.create_script"})
        return FakeScript(source)

    def detach(self) -> None:
        _append({"op": "session.detach"})


class FakeDevice:
    def spawn(self, argv: list[str]) -> int:
        _append({"op": "device.spawn", "argv": argv})
        return 2002

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
    pythonpath = os.environ.get("PYTHONPATH", "")
    env_pythonpath = f"{tmp_path}:{pythonpath}" if pythonpath else str(tmp_path)
    custom_one = tmp_path / "custom-one.js"
    custom_one.write_text("send('custom-one');\n", encoding="utf-8")
    plan = HookPlanService().plan_for_sources(
        [
            HookPlanSource.from_custom_script("custom-one", str(custom_one)),
        ]
    )
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

    assert len(events) == 1
    assert events[0].event_type == "frida_script_error"
    assert events[0].stacktrace == "boom"
    assert events[0].raw_payload["source_script"] == "01_custom-one.js"


def test_packaged_frida_session_backend_can_bootstrap_frida_server_before_retry(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-bootstrap.jsonl"
    marker_file = tmp_path / "frida-ready.marker"
    module_path = tmp_path / "frida.py"
    module_path.write_text(
        f"""
from __future__ import annotations

import json
import os
from pathlib import Path


STATE_PATH = Path(os.environ["APKHACKER_FAKE_FRIDA_STATE"])
READY_MARKER = Path({str(marker_file)!r})


def _append(record: dict[str, object]) -> None:
    with STATE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\\n")


class FakeScript:
    def __init__(self, source: str) -> None:
        self._source = source
        self._callback = None

    def on(self, event_name: str, callback) -> None:
        _append({{"op": "script.on", "event_name": event_name}})
        self._callback = callback

    def load(self) -> None:
        _append({{"op": "script.load", "source_length": len(self._source)}})
        payload = json.dumps(
            {{
                "event_type": "method_call",
                "class_name": "com.demo.net.Config",
                "method_name": "buildUploadUrl",
                "arguments": ["bootstrap"],
                "return_value": "ok",
                "stacktrace": "com.demo.net.Config.buildUploadUrl:1",
            }},
            ensure_ascii=False,
        )
        self._callback({{"type": "send", "payload": payload}}, None)


class FakeSession:
    def create_script(self, source: str) -> FakeScript:
        _append({{"op": "session.create_script"}})
        return FakeScript(source)

    def detach(self) -> None:
        _append({{"op": "session.detach"}})


class FakeDevice:
    def spawn(self, argv: list[str]) -> int:
        _append({{"op": "device.spawn", "argv": argv}})
        return 4242

    def attach(self, pid: int) -> FakeSession:
        _append({{"op": "device.attach", "pid": pid}})
        return FakeSession()

    def resume(self, pid: int) -> None:
        _append({{"op": "device.resume", "pid": pid}})


def get_device(device_id: str, timeout: int | None = None) -> FakeDevice:
    _append({{"op": "frida.get_device", "device_id": device_id, "timeout": timeout, "ready": READY_MARKER.exists()}})
    if not READY_MARKER.exists():
        raise RuntimeError("frida-server is not running")
    return FakeDevice()


def get_usb_device(timeout: int | None = None) -> FakeDevice:
    _append({{"op": "frida.get_usb_device", "timeout": timeout, "ready": READY_MARKER.exists()}})
    if not READY_MARKER.exists():
        raise RuntimeError("frida-server is not running")
    return FakeDevice()
""".strip()
        + "\n",
        encoding="utf-8",
    )
    adb_path = tmp_path / "adb"
    frida_server_binary = tmp_path / "frida-server"
    frida_server_binary.write_text("fake-binary", encoding="utf-8")
    adb_path.write_text(
        f"""#!/bin/sh
READY_MARKER="{marker_file}"
if [ "$1" = "devices" ]; then
  printf 'List of devices attached\\nserial-123\\tdevice\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "getprop" ] && [ "$5" = "ro.product.cpu.abi" ]; then
  printf 'arm64-v8a\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ] && [ "$6" = "id" ]; then
  printf 'uid=0(root) gid=0(root)\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ] && [ "$6" = "pidof frida-server" ]; then
  if [ -f "$READY_MARKER" ]; then
    printf '31337\\n'
  fi
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "push" ]; then
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "su" ] && [ "$5" = "-c" ]; then
  case "$6" in
    "chmod 755 /data/local/tmp/frida-server")
      exit 0
      ;;
    "/data/local/tmp/frida-server >/dev/null 2>&1 &")
      : > "$READY_MARKER"
      exit 0
      ;;
  esac
fi
exit 1
""",
        encoding="utf-8",
    )
    adb_path.chmod(0o755)
    pythonpath = os.environ.get("PYTHONPATH", "")
    env_pythonpath = f"{tmp_path}:{pythonpath}" if pythonpath else str(tmp_path)
    env_path = f"{tmp_path}:{os.environ['PATH']}"
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
            "PATH": env_path,
            "PYTHONPATH": env_pythonpath,
            "APKHACKER_FAKE_FRIDA_STATE": str(state_file),
            "APKHACKER_FRIDA_SERVER_BINARY": str(frida_server_binary),
            "APKHACKER_DEVICE_SERIAL": "serial-123",
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
        "frida.get_device",
        "frida.get_device",
        "device.spawn",
        "device.attach",
        "session.create_script",
        "script.on",
        "script.load",
        "device.resume",
        "session.detach",
    ]
    assert [event.event_type for event in events[:4]] == [
        "device_connected",
        "device_property",
        "device_root_status",
        "frida_server_action",
    ]
    assert events[-1].event_type == "method_call"
    assert events[-1].arguments == ("bootstrap",)


def test_packaged_frida_session_backend_installs_sample_when_package_is_missing(tmp_path: Path) -> None:
    frida_state = tmp_path / "fake-frida-install.jsonl"
    adb_state = tmp_path / "fake-adb-install.jsonl"
    module_path = tmp_path / "frida.py"
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
                "arguments": ["install"],
                "return_value": "ok",
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
        return 5151

    def attach(self, pid: int) -> FakeSession:
        _append({"op": "device.attach", "pid": pid})
        return FakeSession()

    def resume(self, pid: int) -> None:
        _append({"op": "device.resume", "pid": pid})


def get_device(device_id: str, timeout: int | None = None) -> FakeDevice:
    _append({"op": "frida.get_device", "device_id": device_id, "timeout": timeout})
    return FakeDevice()


def get_usb_device(timeout: int | None = None) -> FakeDevice:
    _append({"op": "frida.get_usb_device", "timeout": timeout})
    return FakeDevice()
""".strip()
        + "\n",
        encoding="utf-8",
    )
    adb_path = tmp_path / "adb"
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    adb_path.write_text(
        f"""#!/bin/sh
STATE_FILE="{adb_state}"
append() {{
  printf '%s\\n' "$1" >> "$STATE_FILE"
}}
if [ "$1" = "devices" ]; then
  printf 'List of devices attached\\nserial-123\\tdevice\\n'
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "shell" ] && [ "$4" = "pm" ] && [ "$5" = "path" ] && [ "$6" = "com.demo.shell" ]; then
  append "pm-path:$6"
  exit 0
fi
if [ "$1" = "-s" ] && [ "$2" = "serial-123" ] && [ "$3" = "install" ] && [ "$4" = "-r" ] && [ "$5" = "{sample_path}" ]; then
  append "install:$5"
  printf 'Success\\n'
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    adb_path.chmod(0o755)
    pythonpath = os.environ.get("PYTHONPATH", "")
    env_pythonpath = f"{tmp_path}:{pythonpath}" if pythonpath else str(tmp_path)
    env_path = f"{tmp_path}:{os.environ['PATH']}"
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
            "PATH": env_path,
            "PYTHONPATH": env_pythonpath,
            "APKHACKER_FAKE_FRIDA_STATE": str(frida_state),
            "APKHACKER_DEVICE_SERIAL": "serial-123",
            "APKHACKER_FRIDA_SESSION_SECONDS": "0.1",
        },
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
            sample_path=sample_path,
        )
    )

    adb_records = [line.strip() for line in adb_state.read_text(encoding="utf-8").splitlines() if line.strip()]
    frida_records = [
        json.loads(line)
        for line in frida_state.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert adb_records == [
        "pm-path:com.demo.shell",
        f"install:{sample_path}",
    ]
    assert [event.event_type for event in events[:1]] == ["app_install_status"]
    assert events[0].return_value == "installed"
    assert [record["op"] for record in frida_records] == [
        "frida.get_device",
        "device.spawn",
        "device.attach",
        "session.create_script",
        "script.on",
        "script.load",
        "device.resume",
        "session.detach",
    ]


def test_packaged_frida_session_backend_falls_back_to_attach_when_spawn_fails(tmp_path: Path) -> None:
    state_file = tmp_path / "fake-frida-attach-fallback.jsonl"
    module_path = tmp_path / "frida.py"
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
                "arguments": ["attach-fallback"],
                "return_value": "ok",
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
        raise RuntimeError("spawn blocked")

    def attach(self, target) -> FakeSession:
        _append({"op": "device.attach", "target": target})
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
        "session.detach",
    ]
    assert records[2]["target"] == "com.demo.shell"
    assert events[0].event_type == "frida_session_status"
    assert events[0].method_name == "attach_fallback"
    assert events[-1].event_type == "method_call"
    assert events[-1].arguments == ("attach-fallback",)
