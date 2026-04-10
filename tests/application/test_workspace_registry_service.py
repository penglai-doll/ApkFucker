from pathlib import Path

from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistry
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService


def test_registry_restores_last_opened_workspace(tmp_path: Path) -> None:
    registry = WorkspaceRegistryService(tmp_path / "settings.json")
    workspace_root = tmp_path / "cases" / "case-001"
    workspace_root.mkdir(parents=True)

    registry.set_last_opened_workspace(workspace_root)
    restored = registry.load()

    assert restored.last_opened_workspace == workspace_root


def test_registry_preserves_default_workspace_root(tmp_path: Path) -> None:
    registry_path = tmp_path / "settings.json"
    registry = WorkspaceRegistryService(registry_path)
    default_root = tmp_path / "defaults"
    workspace_root = tmp_path / "cases" / "case-001"
    workspace_root.mkdir(parents=True)

    registry.save(
        WorkspaceRegistry(
            default_workspace_root=default_root,
            last_opened_workspace=None,
        )
    )

    registry.set_last_opened_workspace(workspace_root)
    restored = registry.load()

    assert restored.default_workspace_root == default_root
    assert restored.last_opened_workspace == workspace_root


def test_registry_degrades_safely_on_invalid_field_types(tmp_path: Path) -> None:
    registry_path = tmp_path / "settings.json"
    registry_path.write_text(
        """
        {
          "default_workspace_root": {"path": "/tmp/defaults"},
          "last_opened_workspace": ["case-001"]
        }
        """.strip(),
        encoding="utf-8",
    )

    registry = WorkspaceRegistryService(registry_path)

    restored = registry.load()

    assert restored.default_workspace_root is None
    assert restored.last_opened_workspace is None
