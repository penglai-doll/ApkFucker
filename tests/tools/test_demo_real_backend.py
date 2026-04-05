from pathlib import Path
import sys

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.hook_plan import HookPlanSource
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def test_packaged_demo_real_backend_runs_via_command_bridge(tmp_path: Path) -> None:
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
            HookPlanSource.from_template(
                template_id="ssl.okhttp3_unpin",
                template_name="OkHttp3 SSL Unpinning",
                plugin_id="builtin.ssl-okhttp3-unpin",
            ),
            HookPlanSource.from_method(method),
        ]
    )

    backend = RealExecutionBackend(command=f"{sys.executable} -m apk_hacker.tools.demo_real_backend")
    events = backend.execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name="com.demo.shell",
        )
    )

    assert [event.event_type for event in events] == ["template_loaded", "method_call"]
    assert events[0].method_name == "OkHttp3 SSL Unpinning"
    assert events[1].method_name == "buildUploadUrl"
