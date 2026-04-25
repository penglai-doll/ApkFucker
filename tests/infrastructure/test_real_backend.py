from pathlib import Path
import os
import sys
import threading
import time

import pytest
from pytest import raises

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.backend import ExecutionCancelled
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from apk_hacker.infrastructure.execution.real_backend import _split_command


def test_real_backend_raises_clear_error_when_not_configured() -> None:
    backend = RealExecutionBackend()

    with raises(ExecutionBackendUnavailable, match="APKHACKER_REAL_BACKEND_COMMAND"):
        backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))


@pytest.mark.skipif(os.name != "nt", reason="Windows command splitting regression")
def test_real_backend_command_split_preserves_windows_paths() -> None:
    parts = _split_command(r"C:\Users\zhong\Python311\python.exe C:\tmp\helper.py")

    assert parts == [
        r"C:\Users\zhong\Python311\python.exe",
        r"C:\tmp\helper.py",
    ]


def test_real_backend_runs_configured_command_and_parses_json_events(tmp_path: Path) -> None:
    helper = tmp_path / "emit_events.py"
    helper.write_text(
        """
import json
import os
from pathlib import Path

plan_path = Path(os.environ["APKHACKER_PLAN_PATH"])
scripts_dir = Path(os.environ["APKHACKER_SCRIPTS_DIR"])
package_name = os.environ["APKHACKER_TARGET_PACKAGE"]
plan = json.loads(plan_path.read_text(encoding="utf-8"))
script_names = sorted(path.name for path in scripts_dir.glob("*.js"))
print("helper-started")
print(json.dumps({
    "event_type": "method_call",
    "class_name": "com.demo.net.Config",
    "method_name": "buildUploadUrl",
    "arguments": script_names + [package_name],
    "return_value": str(len(plan["items"])),
    "stacktrace": "com.demo.net.Config.buildUploadUrl:1"
}))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    backend = RealExecutionBackend(command=f"{sys.executable} {helper}")
    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=HookPlan(items=()),
            package_name="com.demo.shell",
        )
    )

    assert len(events) == 1
    assert events[0].job_id == "job-1"
    assert events[0].source == "real"
    assert events[0].method_name == "buildUploadUrl"
    assert events[0].return_value == "0"
    assert events[0].arguments[-1] == "com.demo.shell"


def test_real_backend_surfaces_command_failures(tmp_path: Path) -> None:
    helper = tmp_path / "fail.py"
    helper.write_text("import sys\nsys.stderr.write('backend failed\\n')\nsys.exit(2)\n", encoding="utf-8")

    backend = RealExecutionBackend(command=f"{sys.executable} {helper}")

    with raises(ExecutionBackendUnavailable, match="backend failed"):
        backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))


def test_real_backend_classifies_structured_runner_errors(tmp_path: Path) -> None:
    helper = tmp_path / "structured_fail.py"
    helper.write_text(
        """
import json
import sys

print(json.dumps({
    "event_type": "app_install_error",
    "class_name": "adb.package",
    "method_name": "com.demo.shell",
    "arguments": ["/tmp/sample.apk"],
    "return_value": "INSTALL_FAILED_TEST_ONLY",
    "stacktrace": "",
}))
sys.exit(2)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    backend = RealExecutionBackend(command=f"{sys.executable} {helper}")

    with raises(ExecutionBackendUnavailable, match="INSTALL_FAILED_TEST_ONLY") as exc_info:
        backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))

    assert exc_info.value.error_code == "app_install_error"
    assert exc_info.value.message == "INSTALL_FAILED_TEST_ONLY"


@pytest.mark.parametrize(
    ("event_type", "return_value", "expected_error_code"),
    (
        ("frida_session_error", "attach failed", "frida_session_error"),
        ("frida_injection_error", "inject failed", "frida_injection_error"),
        ("frida_server_error", "server failed", "frida_server_error"),
        ("custom_runner_error", "runner failed", "custom_runner_error"),
    ),
)
def test_real_backend_treats_structured_fatal_events_as_failures_even_on_exit_zero(
    tmp_path: Path,
    event_type: str,
    return_value: str,
    expected_error_code: str,
) -> None:
    helper = tmp_path / "structured_zero_exit.py"
    helper.write_text(
        f"""
import json

print(json.dumps({{
    "event_type": "{event_type}",
    "class_name": "real.backend",
    "method_name": "run",
    "arguments": [],
    "return_value": "{return_value}",
    "stacktrace": "",
}}))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    backend = RealExecutionBackend(command=f"{sys.executable} {helper}")

    with raises(ExecutionBackendUnavailable, match=return_value) as exc_info:
        backend.execute(ExecutionRequest(job_id="job-structured", plan=HookPlan(items=())))

    assert exc_info.value.error_code == expected_error_code
    assert exc_info.value.message == return_value


def test_real_backend_persists_execution_bundle_when_artifact_root_is_configured(tmp_path: Path) -> None:
    helper = tmp_path / "emit_events.py"
    helper.write_text(
        """
import json
print("helper-started")
print(json.dumps({
    "event_type": "method_call",
    "class_name": "com.demo.net.Config",
    "method_name": "buildUploadUrl",
    "arguments": ["ok"],
    "return_value": "1",
    "stacktrace": "com.demo.net.Config.buildUploadUrl:1"
}))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    artifact_root = tmp_path / "runs"
    backend = RealExecutionBackend(command=f"{sys.executable} {helper}", artifact_root=artifact_root)
    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=HookPlan(items=()),
            package_name="com.demo.shell",
        )
    )

    assert len(events) == 2
    bundle_event = events[0]
    assert bundle_event.event_type == "execution_bundle"
    bundle_dir = Path(bundle_event.arguments[0])
    assert bundle_dir.exists()
    assert (bundle_dir / "plan.json").exists()
    assert (bundle_dir / "scripts").is_dir()
    assert (bundle_dir / "stdout.log").read_text(encoding="utf-8").startswith("helper-started")
    assert (bundle_dir / "stderr.log").read_text(encoding="utf-8") == ""
    assert events[1].event_type == "method_call"


def test_real_backend_surfaces_artifact_bundle_path_on_failure(tmp_path: Path) -> None:
    helper = tmp_path / "fail.py"
    helper.write_text("import sys\nprint('helper-started')\nsys.stderr.write('backend failed\\n')\nsys.exit(2)\n", encoding="utf-8")

    artifact_root = tmp_path / "runs"
    backend = RealExecutionBackend(command=f"{sys.executable} {helper}", artifact_root=artifact_root)

    with raises(ExecutionBackendUnavailable, match="Artifacts saved to"):
        backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))

    [bundle_dir] = list(artifact_root.iterdir())
    assert (bundle_dir / "stdout.log").read_text(encoding="utf-8").startswith("helper-started")
    assert "backend failed" in (bundle_dir / "stderr.log").read_text(encoding="utf-8")


def test_real_backend_terminates_running_command_when_cancellation_is_requested(tmp_path: Path) -> None:
    helper = tmp_path / "sleep.py"
    helper.write_text(
        "import time\nprint('helper-started', flush=True)\ntime.sleep(10)\n",
        encoding="utf-8",
    )

    backend = RealExecutionBackend(command=f"{sys.executable} {helper}")
    cancellation_event = threading.Event()
    caught: list[BaseException] = []

    def run_backend() -> None:
        try:
            backend.execute(
                ExecutionRequest(
                    job_id="job-2",
                    plan=HookPlan(items=()),
                    cancellation_event=cancellation_event,
                )
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            caught.append(exc)

    worker = threading.Thread(target=run_backend)
    worker.start()
    time.sleep(0.2)
    cancellation_event.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert len(caught) == 1
    assert isinstance(caught[0], ExecutionCancelled)
