from __future__ import annotations

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_allows_vite_dev_origin_for_local_api() -> None:
    client = TestClient(build_app())

    response = client.options(
        "/api/settings/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_allows_tauri_packaged_origin_for_local_api() -> None:
    client = TestClient(build_app())

    response = client.options(
        "/api/settings/health",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"


def test_environment_endpoint_exposes_live_capture_guidance() -> None:
    client = TestClient(build_app())

    response = client.get("/api/settings/environment")

    assert response.status_code == 200
    payload = response.json()
    live_capture = payload["live_capture"]
    assert "setup_steps" in live_capture
    assert "proxy_steps" in live_capture
    assert "certificate_steps" in live_capture
    assert "recommended_actions" in live_capture
    assert "setup_step_details" in live_capture
    assert "proxy_step_details" in live_capture
    assert "certificate_step_details" in live_capture
    assert "network_summary" in live_capture
    assert "ssl_hook_guidance" in live_capture
    assert isinstance(live_capture["setup_steps"], list)
    assert isinstance(live_capture["setup_step_details"], list)
    assert isinstance(live_capture["network_summary"], dict)
    assert isinstance(live_capture["ssl_hook_guidance"], dict)
    assert {
        "supports_https_intercept",
        "supports_packet_capture",
        "supports_ssl_hooking",
        "proxy_ready",
        "certificate_ready",
        "https_capture_ready",
    } <= set(live_capture["network_summary"].keys())
    assert {
        "recommended",
        "summary",
        "reason",
        "suggested_templates",
        "suggested_template_entries",
        "suggested_terms",
    } <= set(live_capture["ssl_hook_guidance"].keys())
    assert isinstance(live_capture["ssl_hook_guidance"]["suggested_template_entries"], list)
    for entry in live_capture["ssl_hook_guidance"]["suggested_template_entries"]:
        assert {
            "template_id",
            "template_name",
            "plugin_id",
        } <= set(entry.keys())
