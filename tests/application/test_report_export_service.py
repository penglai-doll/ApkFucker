from pathlib import Path
import json

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.report_export_service import ExportableReport, ReportExportService
from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend


def test_report_export_service_writes_markdown_report(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs")
    analysis = json.loads((fixture_root / "sample_analysis.json").read_text(encoding="utf-8"))
    callback = json.loads((fixture_root / "sample_callback-config.json").read_text(encoding="utf-8"))

    static_inputs = StaticAdapter().adapt(
        sample_path=Path("/samples/demo.apk"),
        analysis_report=analysis,
        callback_config=callback,
        artifact_paths={"analysis_report": fixture_root / "sample_analysis.json"},
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

    report = ExportableReport(
        job_id="job-1",
        summary_text="Captured 2 event(s) from the fake backend.",
        sample_path=Path("/samples/demo.apk"),
        static_inputs=static_inputs,
        hook_plan=plan,
        hook_events=events,
        traffic_capture=None,
        last_execution_db_path=tmp_path / "job-1-run-1.sqlite3",
        last_execution_bundle_path=tmp_path / "execution-runs" / "job-1-run-1",
    )
    output_path = tmp_path / "reports" / "job-1-report.md"

    exported = ReportExportService().export_markdown(report, output_path)
    content = exported.read_text(encoding="utf-8")

    assert exported == output_path
    assert "# APKHacker Report" in content
    assert "com.demo.shell" in content
    assert "buildUploadUrl" in content
    assert "demo-c2.example/api/upload" in content
    assert "Captured 2 event(s) from the fake backend." in content
