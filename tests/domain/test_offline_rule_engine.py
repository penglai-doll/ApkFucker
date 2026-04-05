from pathlib import Path

from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.services.offline_rule_engine import OfflineRuleEngine


def _static_inputs(**overrides: object) -> StaticInputs:
    values: dict[str, object] = {
        "sample_path": Path("/samples/demo.apk"),
        "package_name": "com.demo.shell",
        "technical_tags": ("webview-hybrid", "network-callback"),
        "dangerous_permissions": ("android.permission.READ_SMS",),
        "callback_endpoints": ("https://demo-c2.example/api/upload",),
        "callback_clues": ("request body includes device_id and sms_body",),
        "crypto_signals": ("AES/CBC/PKCS5Padding",),
        "packer_hints": ("com.tencent.legu",),
        "limitations": (),
        "artifact_paths": ArtifactPaths(),
    }
    values.update(overrides)
    return StaticInputs(**values)


def test_offline_rule_engine_emits_template_recommendations_for_network_crypto_and_packer_signals() -> None:
    recommendations = OfflineRuleEngine().recommend(_static_inputs())

    titles = [item.title for item in recommendations]

    assert "OkHttp3 SSL Unpinning" in titles
    assert "Cipher Monitor" in titles
    assert "Frida Detection Bypass" in titles


def test_offline_rule_engine_skips_templates_without_matching_static_signals() -> None:
    recommendations = OfflineRuleEngine().recommend(
        _static_inputs(
            technical_tags=(),
            callback_endpoints=(),
            callback_clues=(),
            crypto_signals=(),
            packer_hints=(),
        )
    )

    assert recommendations == ()
