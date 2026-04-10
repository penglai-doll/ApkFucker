from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceRegistry:
    default_workspace_root: Path | None = None
    last_opened_workspace: Path | None = None


class WorkspaceRegistryService:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> WorkspaceRegistry:
        if not self._path.exists():
            return WorkspaceRegistry()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return WorkspaceRegistry()
        if not isinstance(payload, dict):
            return WorkspaceRegistry()
        default_workspace_root = payload.get("default_workspace_root")
        last_opened_workspace = payload.get("last_opened_workspace")
        return WorkspaceRegistry(
            default_workspace_root=Path(default_workspace_root) if default_workspace_root else None,
            last_opened_workspace=Path(last_opened_workspace) if last_opened_workspace else None,
        )

    def save(self, registry: WorkspaceRegistry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(
                {
                    "default_workspace_root": str(registry.default_workspace_root) if registry.default_workspace_root else "",
                    "last_opened_workspace": str(registry.last_opened_workspace) if registry.last_opened_workspace else "",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_path.replace(self._path)

    def set_last_opened_workspace(self, workspace_root: Path) -> None:
        current = self.load()
        self.save(
            WorkspaceRegistry(
                default_workspace_root=current.default_workspace_root,
                last_opened_workspace=workspace_root,
            )
        )
