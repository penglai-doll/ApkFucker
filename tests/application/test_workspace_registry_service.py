from pathlib import Path

from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService


def test_registry_restores_last_opened_workspace(tmp_path: Path) -> None:
    registry = WorkspaceRegistryService(tmp_path / "settings.json")
    workspace_root = tmp_path / "cases" / "case-001"
    workspace_root.mkdir(parents=True)

    registry.set_last_opened_workspace(workspace_root)
    restored = registry.load()

    assert restored.last_opened_workspace == workspace_root
