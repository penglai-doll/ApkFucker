from pathlib import Path
import json

from apk_hacker.application.services.workspace_service import WorkspaceService


def test_create_workspace_copies_sample_and_writes_metadata(tmp_path: Path) -> None:
    sample = tmp_path / "demo.apk"
    sample.write_bytes(b"apk-bytes")
    root = tmp_path / "cases"

    service = WorkspaceService()
    workspace = service.create_workspace(sample, root, title="测试样本")

    assert workspace.workspace_root.exists()
    assert workspace.workspace_root.parent == root
    assert (workspace.workspace_root / "sample" / "original.apk").read_bytes() == b"apk-bytes"
    metadata = json.loads((workspace.workspace_root / "workspace.json").read_text(encoding="utf-8"))
    assert metadata["title"] == "测试样本"
    assert metadata["case_id"] == workspace.case_id
    assert metadata["sample_filename"] == "original.apk"
    assert workspace.title == "测试样本"
    assert workspace.sample_path == workspace.workspace_root / "sample" / "original.apk"
