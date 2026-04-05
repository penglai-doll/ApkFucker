from pathlib import Path
import json

from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


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
