from pathlib import Path
import os
import sys

from pytest import raises

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def _write_fake_frida(path: Path) -> Path:
    frida_path = path / "frida"
    frida_path.write_text(
        """#!/bin/sh
printf '%s\n' "$@" > "$APKHACKER_FRIDA_ARGS_FILE"
sleep 5
""",
        encoding="utf-8",
    )
    frida_path.chmod(0o755)
    return frida_path


def test_packaged_frida_inject_backend_invokes_frida_with_target_and_script(tmp_path: Path) -> None:
    args_file = tmp_path / "frida-args.txt"
    _write_fake_frida(tmp_path)
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
        command=f"{sys.executable} -m apk_hacker.tools.frida_inject_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_FRIDA_ARGS_FILE": str(args_file),
            "APKHACKER_FRIDA_WARMUP_SECONDS": "0.5",
        },
    )

    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
        )
    )

    recorded_args = args_file.read_text(encoding="utf-8").splitlines()
    assert recorded_args[:3] == ["-U", "-f", "com.demo.shell"]
    assert "-l" in recorded_args
    assert any(argument.endswith(".js") for argument in recorded_args)
    assert len(events) == 1
    assert events[0].event_type == "frida_injection"
    assert events[0].method_name == "spawn_attach"
    assert events[0].arguments[0] == "com.demo.shell"


def test_packaged_frida_inject_backend_requires_rendered_script(tmp_path: Path) -> None:
    _write_fake_frida(tmp_path)
    env_path = f"{tmp_path}:{os.environ['PATH']}"
    backend = RealExecutionBackend(
        command=f"{sys.executable} -m apk_hacker.tools.frida_inject_backend",
        extra_env={
            "PATH": env_path,
            "APKHACKER_FRIDA_WARMUP_SECONDS": "0.5",
        },
    )

    with raises(ExecutionBackendUnavailable, match="No rendered Frida scripts"):
        backend.execute(
            ExecutionRequest(
                job_id="job-1",
                plan=HookPlan(items=()),
                package_name="com.demo.shell",
            )
        )
