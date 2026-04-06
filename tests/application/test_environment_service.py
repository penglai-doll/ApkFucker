from apk_hacker.application.services.environment_service import EnvironmentService


def test_environment_service_reports_available_and_missing_tools() -> None:
    known_tools = {
        "jadx": "/opt/tools/jadx",
        "adb": "/opt/android/platform-tools/adb",
    }
    known_modules = {"frida": object()}

    service = EnvironmentService(resolver=known_tools.get, module_resolver=known_modules.get)
    snapshot = service.inspect()

    statuses = {item.name: item for item in snapshot.tools}
    assert statuses["jadx"].available is True
    assert statuses["jadx"].path == "/opt/tools/jadx"
    assert statuses["apktool"].available is False
    assert statuses["python-frida"].available is True
    assert snapshot.available_count == 3
    assert snapshot.missing_count >= 1
    assert "available" in snapshot.summary.lower()
