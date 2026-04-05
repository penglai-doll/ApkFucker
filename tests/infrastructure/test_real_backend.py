from pytest import raises

from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.infrastructure.execution.backend import ExecutionBackendUnavailable
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def test_real_backend_raises_clear_error_when_not_configured() -> None:
    backend = RealExecutionBackend()

    with raises(ExecutionBackendUnavailable, match="not configured"):
        backend.execute("job-1", HookPlan(items=()))
