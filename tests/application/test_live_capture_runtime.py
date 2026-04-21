from pathlib import Path

from apk_hacker.application.services.live_capture_runtime import build_builtin_mitmdump_command_template
from apk_hacker.application.services.live_capture_runtime import normalize_live_capture_listen_host
from apk_hacker.application.services.live_capture_runtime import normalize_live_capture_listen_port
from apk_hacker.application.services.live_capture_runtime import resolve_live_capture_runtime


def test_live_capture_runtime_prefers_explicit_command_template() -> None:
    runtime = resolve_live_capture_runtime(
        command_template="python fake_runner.py {output_path}",
        resolver=lambda name: "/usr/bin/mitmdump" if name == "mitmdump" else None,
    )

    assert runtime.available is True
    assert runtime.source == "configured_command"
    assert runtime.detail == "已配置自定义抓包命令"
    assert runtime.listen_host == "0.0.0.0"
    assert runtime.listen_port == 8080
    assert runtime.command_template == "python fake_runner.py {output_path}"
    assert runtime.proxy_ready is True
    assert runtime.certificate_ready is False
    assert runtime.https_capture_ready is False
    assert runtime.setup_steps[0].key == "capture-command"
    assert runtime.setup_steps[0].emphasis == "required"
    assert len(runtime.setup_steps) >= 2
    assert len(runtime.recommended_actions) >= 1


def test_live_capture_runtime_falls_back_to_builtin_mitmdump() -> None:
    cert_root = Path("/tmp/apkhacker-mitm")
    runtime = resolve_live_capture_runtime(
        command_template=None,
        resolver=lambda name: "/usr/bin/mitmdump" if name == "mitmdump" else None,
        listen_host="127.0.0.1",
        listen_port="9090",
        cert_root=cert_root,
    )

    assert runtime.available is True
    assert runtime.source == "builtin_mitmdump"
    assert runtime.detail == "内置 Mitmdump 已就绪（监听 127.0.0.1:9090）"
    assert runtime.listen_host == "127.0.0.1"
    assert runtime.listen_port == 9090
    assert runtime.command_template == build_builtin_mitmdump_command_template(listen_host="127.0.0.1", listen_port=9090)
    assert runtime.proxy_address_hint == "分析机局域网 IP:9090"
    assert runtime.install_url == "http://mitm.it"
    assert runtime.certificate_path == str((cert_root / "mitmproxy-ca-cert.cer").resolve())
    assert runtime.certificate_directory_path == str(cert_root.resolve())
    assert runtime.certificate_exists is False
    assert runtime.proxy_ready is True
    assert runtime.certificate_ready is True
    assert runtime.https_capture_ready is True
    assert any(step.key == "builtin-proxy" for step in runtime.setup_steps)
    assert any("9090" in step.detail for step in runtime.setup_steps)
    assert any(step.key == "certificate-followup" for step in runtime.certificate_steps)
    assert any("SSL" in action or "HTTPS" in action for action in runtime.recommended_actions)


def test_live_capture_runtime_reports_existing_certificate_when_available() -> None:
    cert_root = Path("/tmp/apkhacker-mitm-ready")
    certificate_path = cert_root / "mitmproxy-ca-cert.cer"
    cert_root.mkdir(parents=True, exist_ok=True)
    certificate_path.write_text("demo", encoding="utf-8")

    runtime = resolve_live_capture_runtime(
        command_template=None,
        resolver=lambda name: "/usr/bin/mitmdump" if name == "mitmdump" else None,
        cert_root=cert_root,
    )

    assert runtime.certificate_exists is True
    assert runtime.certificate_path == str(certificate_path.resolve())
    assert runtime.certificate_help_text == "可直接把该证书安装到测试设备，或在设备浏览器访问 http://mitm.it。"
    assert len(runtime.certificate_steps) >= 1


def test_live_capture_runtime_reports_unavailable_when_no_backend_exists() -> None:
    runtime = resolve_live_capture_runtime(
        command_template=None,
        resolver=lambda _name: None,
    )

    assert runtime.available is False
    assert runtime.source == "unavailable"
    assert runtime.command_template is None
    assert runtime.proxy_address_hint is None
    assert runtime.install_url is None
    assert runtime.certificate_path is None
    assert runtime.proxy_ready is False
    assert runtime.certificate_ready is False
    assert runtime.https_capture_ready is False
    assert len(runtime.setup_steps) >= 1
    assert len(runtime.recommended_actions) >= 1


def test_normalize_live_capture_settings_fall_back_to_defaults_for_invalid_values() -> None:
    assert normalize_live_capture_listen_host("   ") == "0.0.0.0"
    assert normalize_live_capture_listen_port("") == 8080
    assert normalize_live_capture_listen_port("abc") == 8080
    assert normalize_live_capture_listen_port("70000") == 8080
