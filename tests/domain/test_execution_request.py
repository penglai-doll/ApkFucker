from pathlib import Path

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_plan import HookPlan


def test_execution_request_keeps_runtime_context() -> None:
    request = ExecutionRequest(
        job_id="job-1",
        plan=HookPlan(items=()),
        package_name="com.demo.shell",
        sample_path=Path("/samples/demo.apk"),
        runtime_env={"APKHACKER_DEVICE_SERIAL": "serial-123"},
    )

    assert request.job_id == "job-1"
    assert request.package_name == "com.demo.shell"
    assert request.sample_path == Path("/samples/demo.apk")
    assert request.runtime_env == {"APKHACKER_DEVICE_SERIAL": "serial-123"}
