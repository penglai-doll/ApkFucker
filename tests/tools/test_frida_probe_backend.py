from pathlib import Path
import sys

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from tests.fake_cli_tools import prepend_path
from tests.fake_cli_tools import write_fake_frida_ps


def _write_fake_frida_ps(path: Path, script: str) -> Path:
    return write_fake_frida_ps(path, visible="com.demo.shell" in script)


def test_packaged_frida_probe_backend_reports_missing_target(tmp_path: Path) -> None:
    _write_fake_frida_ps(
        tmp_path,
        """#!/bin/sh
printf ' PID  Name  Identifier\\n'
printf '1234  Other  com.other.app\\n'
""",
    )
    env_path = prepend_path(tmp_path)
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_probe_backend",
        extra_env={"PATH": env_path},
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=HookPlan(items=()),
            package_name="com.demo.shell",
        )
    )

    assert len(events) == 1
    assert events[0].event_type == "frida_target"
    assert events[0].method_name == "missing"
    assert events[0].return_value == "com.demo.shell"


def test_packaged_frida_probe_backend_reports_visible_target(tmp_path: Path) -> None:
    _write_fake_frida_ps(
        tmp_path,
        """#!/bin/sh
printf ' PID  Name  Identifier\\n'
printf '4321  Demo  com.demo.shell\\n'
""",
    )
    env_path = prepend_path(tmp_path)
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_probe_backend",
        extra_env={"PATH": env_path},
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=HookPlan(items=()),
            package_name="com.demo.shell",
        )
    )

    assert len(events) == 1
    assert events[0].event_type == "frida_target"
    assert events[0].method_name == "visible"
    assert events[0].arguments == ("com.demo.shell", "4321")
