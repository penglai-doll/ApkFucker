from dataclasses import dataclass
from pathlib import Path
import json

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore
from apk_hacker.static_engine.analyzer import StaticArtifacts


@dataclass
class _FakeStaticAnalyzer:
    artifacts: StaticArtifacts

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        return self.artifacts


def test_mvp_flow_static_to_fake_dynamic(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs")
    analysis = json.loads((fixture_root / "sample_analysis.json").read_text(encoding="utf-8"))
    callback = json.loads((fixture_root / "sample_callback-config.json").read_text(encoding="utf-8"))

    static_inputs = StaticAdapter().adapt(
        sample_path=Path("/samples/demo.apk"),
        analysis_report=analysis,
        callback_config=callback,
        artifact_paths={"analysis_report": "cache/demo/analysis.json"},
    )
    index = JavaMethodIndexer().build(Path("tests/fixtures/jadx_sources"))
    selected = [method for method in index.methods if method.method_name == "buildUploadUrl"]
    plan = HookPlanService().plan_for_methods(selected)
    events = FakeExecutionBackend().execute(
        ExecutionRequest(
            job_id="job-1",
            plan=plan,
            package_name=static_inputs.package_name,
            sample_path=Path("/samples/demo.apk"),
        )
    )

    store = HookLogStore(tmp_path / "hooks.sqlite3")
    for event in events:
        store.insert(event)

    rows = store.list_for_job("job-1")
    assert static_inputs.package_name == "com.demo.shell"
    assert len(rows) == 2
    assert {row.method_name for row in rows} == {"buildUploadUrl"}


def test_mvp_flow_writes_normalized_static_payloads(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"

    service = JobService(
        static_analyzer=_FakeStaticAnalyzer(
            StaticArtifacts(
                output_root=output_root,
                report_dir=output_root / "报告" / "sample",
                cache_dir=output_root / "cache" / "sample",
                analysis_json=fixture_root / "sample_analysis.json",
                callback_config_json=fixture_root / "sample_callback-config.json",
                noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
                jadx_sources_dir=jadx_sources,
                jadx_project_dir=None,
            )
        )
    )

    bundle = service.load_static_workspace_bundle(sample_path, output_dir=output_root)
    paths = bundle.static_inputs.artifact_paths
    manifest_payload = json.loads(paths.artifact_manifest.read_text(encoding="utf-8"))
    static_result_payload = json.loads(paths.static_result.read_text(encoding="utf-8"))
    findings_rows = [json.loads(line) for line in paths.findings_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    evidence_rows = [json.loads(line) for line in paths.evidence_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert bundle.static_result is not None
    assert bundle.artifact_manifest is not None
    assert manifest_payload["schema_version"] == "artifact-manifest.v1"
    artifact_kinds = {artifact["kind"] for artifact in manifest_payload["artifacts"]}
    assert artifact_kinds >= {
        "normalized.artifact_manifest",
        "normalized.static_result",
        "normalized.findings",
        "normalized.evidence",
        "normalized.method_index",
        "normalized.class_index",
    }
    assert "legacy.noise_log_json" not in artifact_kinds
    assert "legacy.report_docx" not in artifact_kinds
    assert static_result_payload["schema_version"] == "static-result.v1"
    assert static_result_payload["package_name"] == "com.demo.shell"
    assert "com.tencent.legu" in static_result_payload["packer_hints"]
    assert findings_rows
    assert evidence_rows
