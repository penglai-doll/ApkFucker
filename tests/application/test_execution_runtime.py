from pathlib import Path

from apk_hacker.application.services.execution_runtime import build_execution_backend
from apk_hacker.application.services.execution_runtime import build_execution_backends
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend


def test_build_execution_backend_returns_fake_backend_for_fake_mode() -> None:
    backend = build_execution_backend("fake_backend")

    assert isinstance(backend, FakeExecutionBackend)


def test_build_execution_backend_routes_named_real_presets_to_packaged_modules(tmp_path: Path) -> None:
    backend = build_execution_backend(
        "real_frida_session",
        artifact_root=tmp_path / "runs",
        extra_env={"APKHACKER_DEVICE_SERIAL": "serial-123"},
    )

    assert isinstance(backend, RealExecutionBackend)
    assert backend.configured is True


def test_build_execution_backends_includes_named_real_presets_and_real_device(tmp_path: Path) -> None:
    backends = build_execution_backends(
        artifact_root=tmp_path / "runs",
        real_device_command="python /tmp/custom-runner.py",
    )

    assert set(backends) >= {
        "fake_backend",
        "real_device",
        "real_adb_probe",
        "real_frida_bootstrap",
        "real_frida_probe",
        "real_frida_inject",
        "real_frida_session",
    }
    assert isinstance(backends["real_device"], RealExecutionBackend)
    assert backends["real_device"].configured is True
