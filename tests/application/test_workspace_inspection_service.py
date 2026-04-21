from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.job_service import StaticWorkspaceBundle
from apk_hacker.application.services.workspace_inspection_service import _first_party_rank
from apk_hacker.application.services.workspace_inspection_service import _method_matches
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.domain.models.indexes import MethodIndex
from apk_hacker.domain.models.static_inputs import StaticInputs


@dataclass
class _FakeJobService:
    bundle: StaticWorkspaceBundle
    all_method_index: MethodIndex

    def __post_init__(self) -> None:
        self.load_calls: list[tuple[Path, Path | None, str]] = []
        self.build_calls: list[tuple[Path, tuple[str, ...]]] = []

    def load_static_workspace_bundle(
        self,
        sample_path: Path,
        output_dir: Path | None = None,
        mode: str = "auto",
    ) -> StaticWorkspaceBundle:
        self.load_calls.append((sample_path, output_dir, mode))
        return self.bundle

    def build_method_index(self, jadx_sources_dir: Path, package_prefixes: tuple[str, ...] = ()) -> MethodIndex:
        self.build_calls.append((jadx_sources_dir, package_prefixes))
        if package_prefixes:
            return self.bundle.method_index
        return self.all_method_index


def _sample_method() -> MethodIndexEntry:
    return MethodIndexEntry(
        class_name="com.example.alpha.net.ApiClient",
        method_name="sendPayload",
        parameter_types=("java.lang.String", "java.util.Map<java.lang.String, java.lang.String>"),
        return_type="void",
        is_constructor=False,
        overload_count=1,
        source_path="com/example/alpha/net/ApiClient.java",
        line_hint=142,
        tags=("回连", "加密前"),
        evidence=("命中 callback clue",),
        declaration="public void sendPayload(java.lang.String endpoint, java.util.Map<java.lang.String, java.lang.String> headers)",
        source_preview="public void sendPayload(...) {\n    encryptPayload(body);\n    post(endpoint, headers);\n}",
    )


def _related_candidate_static_inputs() -> StaticInputs:
    return StaticInputs(
        sample_path=Path("/samples/demo.apk"),
        package_name="com.demo.shell",
        technical_tags=("network-callback", "webview-hybrid"),
        dangerous_permissions=("android.permission.READ_SMS",),
        callback_endpoints=("https://demo-c2.example/api/upload",),
        callback_clues=("request body includes device_id and sms_body",),
        crypto_signals=("AES/CBC/PKCS5Padding",),
        packer_hints=("com.tencent.legu",),
        limitations=(),
        artifact_paths=ArtifactPaths(jadx_sources=Path("/virtual/jadx-sources")),
    )


def _related_candidate_method_index() -> tuple[MethodIndex, MethodIndex]:
    first_party_methods = (
        MethodIndexEntry(
            class_name="com.demo.shell.UploadManager",
            method_name="buildUploadUrl",
            parameter_types=("java.lang.String",),
            return_type="java.lang.String",
            is_constructor=False,
            overload_count=1,
            source_path="com/demo/shell/UploadManager.java",
            line_hint=18,
            declaration='public String buildUploadUrl(String host)',
            source_preview='return "https://demo-c2.example/api/upload";',
            tags=("network", "upload"),
            evidence=("https",),
        ),
        MethodIndexEntry(
            class_name="com.demo.shell.HomeActivity",
            method_name="onCreate",
            parameter_types=("android.os.Bundle",),
            return_type="void",
            is_constructor=False,
            overload_count=1,
            source_path="com/demo/shell/HomeActivity.java",
            line_hint=21,
            declaration="protected void onCreate(android.os.Bundle savedInstanceState)",
            source_preview="super.onCreate(savedInstanceState);",
        ),
    )
    all_methods = first_party_methods + (
        MethodIndexEntry(
            class_name="okhttp3.OkHttpClient",
            method_name="newCall",
            parameter_types=("okhttp3.Request",),
            return_type="okhttp3.Call",
            is_constructor=False,
            overload_count=1,
            source_path="okhttp3/OkHttpClient.java",
            line_hint=37,
            declaration="public Call newCall(Request request)",
            source_preview="Request.Builder builder = new Request.Builder().url(endpoint); // network callback",
            evidence=("request", "callback"),
        ),
        MethodIndexEntry(
            class_name="com.thirdparty.crypto.CipherHelper",
            method_name="encryptPayload",
            parameter_types=("byte[]",),
            return_type="byte[]",
            is_constructor=False,
            overload_count=1,
            source_path="com/thirdparty/crypto/CipherHelper.java",
            line_hint=11,
            declaration="public byte[] encryptPayload(byte[] data)",
            source_preview='Cipher.getInstance("AES/CBC/PKCS5Padding"); // cipher',
            tags=("cipher", "crypto"),
            evidence=("AES/CBC/PKCS5Padding",),
        ),
        MethodIndexEntry(
            class_name="org.other.DebugHelper",
            method_name="dump",
            parameter_types=("java.lang.String",),
            return_type="void",
            is_constructor=False,
            overload_count=1,
            source_path="org/other/DebugHelper.java",
            line_hint=8,
            declaration="public void dump(String value)",
            source_preview="System.out.println(value);",
        ),
    )
    return MethodIndex(classes=(), methods=first_party_methods), MethodIndex(classes=(), methods=all_methods)


def _make_workspace_inspection_service(tmp_path: Path) -> tuple[WorkspaceInspectionService, str, _FakeJobService]:
    workspace_root = tmp_path / "workspaces"
    case_id = "case-related"
    case_root = workspace_root / case_id
    sample_dir = case_root / "sample"
    sample_dir.mkdir(parents=True)
    (sample_dir / "original.apk").write_bytes(b"apk")
    (case_root / "workspace.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "title": "相关候选案件",
                "workspace_version": 1,
                "created_at": "2026-04-19T00:00:00Z",
                "updated_at": "2026-04-19T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    first_party_index, all_method_index = _related_candidate_method_index()
    bundle = StaticWorkspaceBundle(
        job=AnalysisJob.queued(str(sample_dir / "original.apk")),
        static_inputs=_related_candidate_static_inputs(),
        method_index=first_party_index,
    )
    fake_job_service = _FakeJobService(bundle=bundle, all_method_index=all_method_index)
    service = WorkspaceInspectionService(
        registry_service=WorkspaceRegistryService(tmp_path / "registry.json"),
        default_workspace_root=workspace_root,
        job_service=fake_job_service,
        case_queue_service=CaseQueueService(),
        custom_script_service=CustomScriptService(tmp_path / "scripts"),
    )
    return service, case_id, fake_job_service


def test_method_matches_declaration_and_source_preview_terms() -> None:
    entry = _sample_method()

    assert _method_matches(entry, "sendPayload")
    assert _method_matches(entry, "headers")
    assert _method_matches(entry, "encryptPayload")
    assert _method_matches(entry, "callback clue")
    assert not _method_matches(entry, "nonexistentToken")


def test_first_party_rank_prefers_methods_under_sample_package() -> None:
    first_party = _sample_method()
    third_party = MethodIndexEntry(
        class_name="android.support.v4.app.RemoteActionCompatParcelizer",
        method_name="read",
        parameter_types=("NV1",),
        return_type="RemoteActionCompat",
        is_constructor=False,
        overload_count=1,
        source_path="android/support/v4/app/RemoteActionCompatParcelizer.java",
        line_hint=10,
        declaration="public static RemoteActionCompat read(NV1 nv1)",
        source_preview="public static RemoteActionCompat read(NV1 nv1) { return androidx.core.app.RemoteActionCompatParcelizer.read(nv1); }",
    )

    assert _first_party_rank(first_party, "com.example.alpha") == 0
    assert _first_party_rank(third_party, "com.example.alpha") == 1


def test_related_candidates_keep_first_party_ahead_and_include_clue_matches(tmp_path: Path) -> None:
    service, case_id, fake_job_service = _make_workspace_inspection_service(tmp_path)

    first_party_items, first_party_total, first_party_scope = service.search_methods(
        case_id,
        scope="first_party",
        query="",
        limit=20,
    )
    related_items, related_total, related_scope = service.search_methods(
        case_id,
        scope="related_candidates",
        query="",
        limit=20,
    )
    all_items, all_total, all_scope = service.search_methods(
        case_id,
        scope="all",
        query="",
        limit=20,
    )

    assert first_party_scope == "first_party"
    assert related_scope == "related_candidates"
    assert all_scope == "all"
    assert first_party_total == 2
    assert related_total == 4
    assert all_total == 5
    assert [item.class_name for item in first_party_items] == [
        "com.demo.shell.UploadManager",
        "com.demo.shell.HomeActivity",
    ]
    assert [item.class_name for item in related_items[:2]] == [
        "com.demo.shell.UploadManager",
        "com.demo.shell.HomeActivity",
    ]
    assert {item.class_name for item in related_items[2:]} == {
        "okhttp3.OkHttpClient",
        "com.thirdparty.crypto.CipherHelper",
    }
    assert "org.other.DebugHelper" not in {item.class_name for item in related_items}
    assert len(fake_job_service.load_calls) == 1
    assert fake_job_service.build_calls == [(Path("/virtual/jadx-sources"), ())]
