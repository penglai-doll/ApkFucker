from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceRegistry:
    default_workspace_root: Path | None = None
    last_opened_workspace: Path | None = None
    known_workspace_roots: tuple[Path, ...] = ()


def _coerce_path(value: object) -> Path | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value
    if not isinstance(value, (str, bytes)):
        return None
    text = value.decode() if isinstance(value, bytes) else value
    if not text.strip():
        return None
    try:
        return Path(text)
    except (TypeError, ValueError):
        return None


def _coerce_paths(value: object) -> tuple[Path, ...]:
    if not isinstance(value, list):
        return ()

    paths: list[Path] = []
    seen: set[Path] = set()
    for entry in value:
        path = _coerce_path(entry)
        if path is None or path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return tuple(paths)


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
        return WorkspaceRegistry(
            default_workspace_root=_coerce_path(payload.get("default_workspace_root")),
            last_opened_workspace=_coerce_path(payload.get("last_opened_workspace")),
            known_workspace_roots=_coerce_paths(payload.get("known_workspace_roots")),
        )

    def save(self, registry: WorkspaceRegistry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(
                {
                    "default_workspace_root": str(registry.default_workspace_root) if registry.default_workspace_root else "",
                    "last_opened_workspace": str(registry.last_opened_workspace) if registry.last_opened_workspace else "",
                    "known_workspace_roots": [str(path) for path in registry.known_workspace_roots],
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
                known_workspace_roots=current.known_workspace_roots,
            )
        )

    def remember_workspace_root(self, workspace_root: Path) -> None:
        current = self.load()
        normalized_root = workspace_root.expanduser()
        roots = list(current.known_workspace_roots)
        if normalized_root not in roots:
            roots.append(normalized_root)

        self.save(
            WorkspaceRegistry(
                default_workspace_root=current.default_workspace_root,
                last_opened_workspace=current.last_opened_workspace,
                known_workspace_roots=tuple(roots),
            )
        )
