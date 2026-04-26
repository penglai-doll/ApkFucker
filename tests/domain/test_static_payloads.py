from apk_hacker.domain.models.artifact import ArtifactManifest, ArtifactRef
from apk_hacker.domain.models.evidence import Evidence
from apk_hacker.domain.models.finding import Finding
from apk_hacker.domain.models.static_result import StaticResult


def test_artifact_manifest_payload_uses_canonical_nested_shape() -> None:
    metadata = {"schema": "dynamic-event.v1"}
    manifest = ArtifactManifest(
        schema_version="artifact-manifest.v1",
        case_id="case-1",
        sample_path="D:/samples/demo.apk",
        artifacts=(
            ArtifactRef(
                artifact_id="dynamic-hook-events-sqlite",
                kind="dynamic.hook_events_sqlite",
                path="D:/cases/case-1/executions/run-1/hook-events.sqlite3",
                producer="hook_log_store",
                created_at="2026-04-26T00:00:00+00:00",
                metadata=metadata,
            ),
        ),
    )

    payload = manifest.to_payload()
    metadata["schema"] = "changed-after-serialization"

    assert payload == {
        "schema_version": "artifact-manifest.v1",
        "case_id": "case-1",
        "sample_path": "D:/samples/demo.apk",
        "artifacts": [
            {
                "artifact_id": "dynamic-hook-events-sqlite",
                "kind": "dynamic.hook_events_sqlite",
                "path": "D:/cases/case-1/executions/run-1/hook-events.sqlite3",
                "producer": "hook_log_store",
                "created_at": "2026-04-26T00:00:00+00:00",
                "metadata": {"schema": "dynamic-event.v1"},
            }
        ],
    }
    assert ArtifactManifest.from_payload(payload) == manifest


def test_static_result_payload_uses_canonical_schema_shape() -> None:
    finding = Finding(
        finding_id="finding-1",
        category="crypto",
        severity="medium",
        title="Cryptographic activity signals detected",
        summary="Cipher usage should be instrumented.",
        confidence=0.8,
        evidence_ids=("evidence-1",),
        tags=("crypto",),
    )
    evidence = Evidence(
        evidence_id="evidence-1",
        source_type="source",
        path="D:/cases/case-1/static/analysis.json",
        line=42,
        excerpt="javax.crypto.Cipher",
        tags=("crypto", "cipher"),
        metadata={"algorithm": "AES"},
    )
    result = StaticResult(
        package_name="com.demo.app",
        technical_tags=("okhttp3",),
        dangerous_permissions=("android.permission.READ_SMS",),
        callback_endpoints=("https://api.example/upload",),
        callback_clues=("com.demo.net.Config.buildUploadUrl",),
        crypto_signals=("AES",),
        packer_hints=("tencent_legacy_shell",),
        limitations=("jadx_partial_failure",),
        findings=(finding,),
        evidence=(evidence,),
    )

    payload = result.to_payload()

    assert payload["schema_version"] == "static-result.v1"
    assert payload["package_name"] == "com.demo.app"
    assert payload["technical_tags"] == ["okhttp3"]
    assert payload["dangerous_permissions"] == ["android.permission.READ_SMS"]
    assert payload["callback_endpoints"] == ["https://api.example/upload"]
    assert payload["callback_clues"] == ["com.demo.net.Config.buildUploadUrl"]
    assert payload["crypto_signals"] == ["AES"]
    assert payload["packer_hints"] == ["tencent_legacy_shell"]
    assert payload["limitations"] == ["jadx_partial_failure"]
    assert payload["findings"] == [finding.to_payload()]
    assert payload["evidence"] == [evidence.to_payload()]
    assert StaticResult.from_payload(payload) == result


def test_static_payload_models_reject_invalid_payloads() -> None:
    assert ArtifactRef.from_payload(None) is None
    assert ArtifactManifest.from_payload({"case_id": "missing-required-fields"}) is None
    assert Finding.from_payload({"finding_id": "missing-required-fields"}) is None
    assert Evidence.from_payload({"evidence_id": "missing-source-type"}) is None
    assert StaticResult.from_payload({"schema_version": "static-result.v1"}) is None
