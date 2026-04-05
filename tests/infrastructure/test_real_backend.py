from pathlib import Path
import os
import sys

from pytest import raises

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def test_real_backend_raises_clear_error_when_not_configured() -> None:
    backend = RealExecutionBackend()

    with raises(ExecutionBackendUnavailable, match="APKHACKER_REAL_BACKEND_COMMAND"):
        backend.execute(ExecutionRequest(job_id="job-1", plan=HookPlan(items=())))


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
