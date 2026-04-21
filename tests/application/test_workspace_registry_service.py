from pathlib import Path

from apk_hacker.application.services.workspace_registry_service import default_workspace_data_root
from apk_hacker.application.services.workspace_registry_service import default_workspace_registry_path
from apk_hacker.application.services.workspace_registry_service import legacy_workspace_data_root
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


def test_registry_tracks_known_workspace_roots_without_duplicates(tmp_path: Path) -> None:
    registry = WorkspaceRegistryService(tmp_path / "settings.json")
    root_one = tmp_path / "cases-a"
    root_two = tmp_path / "cases-b"

    registry.remember_workspace_root(root_one)
    registry.remember_workspace_root(root_two)
    registry.remember_workspace_root(root_one)

    restored = registry.load()

    assert restored.known_workspace_roots == (root_one, root_two)


def test_default_workspace_paths_use_workbench_name_for_new_installations(tmp_path: Path) -> None:
    assert default_workspace_data_root(tmp_path) == tmp_path / "cache" / "workbench"
    assert default_workspace_registry_path(tmp_path) == tmp_path / "cache" / "workbench" / "workspace-registry.json"


def test_default_workspace_registry_path_falls_back_to_legacy_gui_location(tmp_path: Path) -> None:
    legacy_registry_path = legacy_workspace_data_root(tmp_path) / "workspace-registry.json"
    legacy_registry_path.parent.mkdir(parents=True)
    legacy_registry_path.write_text("{}", encoding="utf-8")

    assert default_workspace_registry_path(tmp_path) == legacy_registry_path
