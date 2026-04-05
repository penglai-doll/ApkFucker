from pathlib import Path

from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.services.hook_advisor import OfflineHookAdvisor
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer


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


def test_offline_hook_advisor_prioritizes_methods_from_static_callback_clues() -> None:
    method_index = JavaMethodIndexer().build(Path("tests/fixtures/jadx_sources"))

    recommendations = OfflineHookAdvisor().recommend(_static_inputs(), method_index)

    assert recommendations
    assert recommendations[0].method is not None
    assert recommendations[0].method.method_name == "buildUploadUrl"
    assert "callback" in recommendations[0].reason.lower()
    assert "upload" in recommendations[0].matched_terms
    assert "onCreate" not in [item.method.method_name for item in recommendations if item.method is not None]


def test_offline_hook_advisor_uses_permission_and_crypto_terms_for_scoring() -> None:
    method_index = MethodIndex(
        classes=(),
        methods=(
            MethodIndexEntry(
                class_name="com.demo.spy.AudioClient",
                method_name="recordAudioClip",
                parameter_types=("String",),
                return_type="byte[]",
                is_constructor=False,
                overload_count=1,
                source_path="sources/com/demo/spy/AudioClient.java",
                line_hint=12,
            ),
            MethodIndexEntry(
                class_name="com.demo.crypto.CipherBox",
                method_name="encryptPayload",
                parameter_types=("byte[]",),
                return_type="String",
                is_constructor=False,
                overload_count=1,
                source_path="sources/com/demo/crypto/CipherBox.java",
                line_hint=21,
            ),
        ),
    )

    recommendations = OfflineHookAdvisor().recommend(
        _static_inputs(
            technical_tags=(),
            callback_endpoints=(),
            callback_clues=(),
            dangerous_permissions=("android.permission.RECORD_AUDIO",),
            crypto_signals=("AES/CBC/PKCS5Padding", "HMAC-SHA256"),
        ),
        method_index,
    )
    method_recommendations = [item for item in recommendations if item.method is not None]

    assert [item.method.method_name for item in method_recommendations] == [
        "encryptPayload",
        "recordAudioClip",
    ]
    assert "crypto" in method_recommendations[0].reason.lower()
    assert "audio" in method_recommendations[1].matched_terms


def test_offline_hook_advisor_adds_template_recommendations_from_static_signals() -> None:
    method_index = JavaMethodIndexer().build(Path("tests/fixtures/jadx_sources"))

    recommendations = OfflineHookAdvisor().recommend(_static_inputs(), method_index)
    template_titles = [item.title for item in recommendations if item.kind == "template_hook"]

    assert "OkHttp3 SSL Unpinning" in template_titles
    assert "Cipher Monitor" in template_titles
    assert "Frida Detection Bypass" in template_titles
