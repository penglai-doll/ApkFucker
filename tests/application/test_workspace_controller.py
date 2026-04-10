from pathlib import Path
import json

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.report_export_service import ReportExportService
from apk_hacker.application.services.workspace_controller import WorkspaceController
from apk_hacker.application.services.workspace_service import WorkspaceService
from apk_hacker.domain.models.case_queue import CaseQueueItem
from apk_hacker.static_engine.analyzer import StaticArtifacts


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts
        self.calls: list[tuple[Path, Path | None, str]] = []

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        self.calls.append((target_path, output_dir, mode))
        return self.artifacts


def test_workspace_controller_initializes_workspace_and_refreshes_related_state(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    (scripts_root / "trace_login.js").write_text("send('trace');\n", encoding="utf-8")

    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=tmp_path / "cache",
            report_dir=tmp_path / "cache" / "报告" / "sample",
            cache_dir=tmp_path / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=tmp_path / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )

    controller = WorkspaceController(
        db_root=tmp_path / "cache",
        scripts_root=scripts_root,
        job_service=JobService(static_analyzer=fake_analyzer),
        workspace_service=WorkspaceService(),
        case_queue_service=CaseQueueService(),
        custom_script_service=CustomScriptService(scripts_root),
        report_export_service=ReportExportService(),
    )

    state = controller.initialize_workspace(
        sample_path=sample_path,
        workspace_root=tmp_path / "workspaces",
        title="测试样本",
    )

    assert state.workspace.title == "测试样本"
    assert state.workspace.sample_path.name == "original.apk"
    assert state.workspace.workspace_root.exists()
    assert state.job.status == "queued"
    assert state.static_inputs.package_name == "com.demo.shell"
    assert len(state.method_index.methods) == 5
    assert state.case_queue == (
        CaseQueueItem(
            case_id=state.workspace.case_id,
            title="测试样本",
            workspace_root=state.workspace.workspace_root,
        ),
    )
    assert [script.name for script in state.custom_scripts] == ["trace_login"]
    assert "测试样本" in state.summary_text
    assert "5" in state.summary_text
    assert fake_analyzer.calls == [
        (
            state.workspace.sample_path,
            state.workspace.workspace_root / "static",
            "auto",
        )
    ]


def test_case_queue_service_lists_valid_workspaces_only(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    valid_workspace = root / "case-001"
    valid_workspace.mkdir(parents=True)
    (valid_workspace / "workspace.json").write_text(
        json.dumps(
            {
                "case_id": "case-001",
                "title": "Alpha",
                "workspace_version": 1,
                "created_at": "2026-04-10T00:00:00Z",
                "updated_at": "2026-04-10T00:00:00Z",
                "sample_filename": "original.apk",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    invalid_workspace = root / "case-002"
    invalid_workspace.mkdir(parents=True)
    (invalid_workspace / "workspace.json").write_text(
        json.dumps({"case_id": 123, "title": None}, ensure_ascii=False),
        encoding="utf-8",
    )

    items = CaseQueueService().list_cases(root)

    assert items == (
        CaseQueueItem(
            case_id="case-001",
            title="Alpha",
            workspace_root=valid_workspace,
        ),
    )
