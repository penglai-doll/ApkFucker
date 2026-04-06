import json
from pathlib import Path

from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.static_inputs import StaticInputs


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "static_outputs"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_static_adapter_normalizes_static_outputs(tmp_path: Path) -> None:
    adapter = StaticAdapter()
    sample_path = tmp_path / "samples" / "demo.apk"
    artifact_paths = {
        "analysis_report": tmp_path / "cache" / "demo" / "analysis.json",
        "callback_config": tmp_path / "cache" / "demo" / "callback-config.json",
        "noise_log": tmp_path / "cache" / "demo" / "noise-log.json",
        "static_markdown_report": tmp_path / "报告" / "demo" / "report.md",
        "static_docx_report": tmp_path / "报告" / "demo" / "report.docx",
    }

    result = adapter.adapt(
        sample_path=sample_path,
        analysis_report=_load_fixture("sample_analysis.json"),
        callback_config=_load_fixture("sample_callback-config.json"),
        artifact_paths=artifact_paths,
    )

    assert result == StaticInputs(
        sample_path=sample_path.resolve(),
        package_name="com.demo.shell",
        technical_tags=("webview-hybrid", "network-callback"),
        dangerous_permissions=(
            "android.permission.READ_SMS",
            "android.permission.RECORD_AUDIO",
        ),
        callback_endpoints=(
            "https://demo-c2.example/api/upload",
            "demo-c2.example",
            "1.2.3.4",
        ),
        callback_clues=(
            "sources/com/demo/net/Config.java: baseUrl = https://demo-c2.example/api/",
            'sources/com/demo/net/Api.java: "https://" + host + "/api/upload"',
            "sources/com/demo/net/Api.java: request body includes device_id and sms_body",
        ),
        crypto_signals=("AES/CBC/PKCS5Padding", "HMAC-SHA256"),
        packer_hints=("com.tencent.legu",),
        limitations=("jadx_sources_unavailable", "callback_config_partial"),
        artifact_paths=ArtifactPaths(
            analysis_report=(tmp_path / "cache" / "demo" / "analysis.json").resolve(),
            callback_config=(tmp_path / "cache" / "demo" / "callback-config.json").resolve(),
            noise_log=(tmp_path / "cache" / "demo" / "noise-log.json").resolve(),
            static_markdown_report=(tmp_path / "报告" / "demo" / "report.md").resolve(),
            static_docx_report=(tmp_path / "报告" / "demo" / "report.docx").resolve(),
        ),
    )


def test_static_adapter_supports_compatibility_fallbacks(tmp_path: Path) -> None:
    adapter = StaticAdapter()
    sample_path = tmp_path / "samples" / "compat.apk"

    result = adapter.adapt(
        sample_path=sample_path,
        analysis_report={
            "package_name": "com.compat.demo",
            "technical_tags": [],
            "technical_profile": {
                "primary_type": "hybrid",
                "types": [{"name": "bridge-heavy"}],
            },
            "dangerous_permissions": ["android.permission.CAMERA"],
            "packer": "com.tencent.legu",
        },
        callback_config={
            "endpoints": {
                "urls": ["https://compat.example/api"],
            },
            "code_inference": {
                "endpoints": {
                    "domains": ["compat.example"],
                    "ips": ["10.0.0.8"],
                }
            },
            "clues": [
                {
                    "source": "sources/com/compat/Net.java",
                    "value": "https://compat.example/api",
                }
            ],
        },
        artifact_paths=None,
    )

    assert result.package_name == "com.compat.demo"
    assert result.technical_tags == ("hybrid", "bridge-heavy")
    assert result.dangerous_permissions == ("android.permission.CAMERA",)
    assert result.packer_hints == ("com.tencent.legu",)
    assert result.callback_endpoints == (
        "https://compat.example/api",
        "compat.example",
        "10.0.0.8",
    )
    assert result.callback_clues == ("sources/com/compat/Net.java: https://compat.example/api",)


def test_static_adapter_keeps_declared_permissions_out_of_dangerous_permissions(tmp_path: Path) -> None:
    adapter = StaticAdapter()

    result = adapter.adapt(
        sample_path=tmp_path / "samples" / "manifest-only.apk",
        analysis_report={
            "package_name": "com.permissions.only",
            "permissions": [
                "android.permission.INTERNET",
                "android.permission.CAMERA",
            ],
        },
        callback_config={},
        artifact_paths=None,
    )

    assert result.dangerous_permissions == ()


def test_static_adapter_accepts_scalar_endpoint_values(tmp_path: Path) -> None:
    adapter = StaticAdapter()

    result = adapter.adapt(
        sample_path=tmp_path / "samples" / "scalar-endpoints.apk",
        analysis_report={"package_name": "com.scalar.endpoints"},
        callback_config={
            "endpoints": {
                "urls": "https://scalar.example/api",
                "domains": "scalar.example",
            },
            "code_inference": {
                "endpoints": {
                    "ips": "10.0.0.9",
                    "emails": ["ops@scalar.example"],
                }
            },
        },
        artifact_paths=None,
    )

    assert result.callback_endpoints == (
        "https://scalar.example/api",
        "scalar.example",
        "10.0.0.9",
        "ops@scalar.example",
    )


def test_static_adapter_falls_back_to_technical_profile_when_tags_are_empty(tmp_path: Path) -> None:
    adapter = StaticAdapter()
    sample_path = tmp_path / "samples" / "empty-tags.apk"

    result = adapter.adapt(
        sample_path=sample_path,
        analysis_report={
            "package_name": "com.empty.tags",
            "technical_tags": [],
            "technical_profile": {
                "primary_type": "webview-hybrid",
                "types": [{"name": "network-callback"}],
            },
        },
        callback_config={},
        artifact_paths=None,
    )

    assert result.technical_tags == ("webview-hybrid", "network-callback")


def test_static_adapter_raises_when_package_name_is_missing(tmp_path: Path) -> None:
    adapter = StaticAdapter()

    try:
        adapter.adapt(
            sample_path=tmp_path / "samples" / "missing-package.apk",
            analysis_report={},
            callback_config={},
            artifact_paths=None,
        )
    except ValueError as exc:
        assert "package name" in str(exc)
    else:
        raise AssertionError("Expected ValueError when package name is missing")
