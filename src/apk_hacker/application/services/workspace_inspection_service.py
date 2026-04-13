from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import replace
import json
from pathlib import Path
from typing import Protocol

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.custom_script_service import CustomScriptRecord, CustomScriptService
from apk_hacker.application.services.job_service import JobService, StaticWorkspaceBundle
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.domain.models.hook_advice import HookRecommendation
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.domain.services.hook_advisor import OfflineHookAdvisor
from apk_hacker.infrastructure.integrations.jadx_launcher import open_in_jadx
from apk_hacker.infrastructure.integrations.jadx_launcher import resolve_jadx_gui_path


class CaseNotFoundError(KeyError):
    pass


class JadxUnavailableError(RuntimeError):
    pass


def _normalize_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_workspace_metadata(workspace_root: Path) -> dict[str, object]:
    workspace_json = workspace_root / "workspace.json"
    payload = json.loads(workspace_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Workspace metadata must be an object: {workspace_json}")
    return payload


def _method_matches(entry: MethodIndexEntry, query: str) -> bool:
    if not query:
        return True

    haystacks = (
        entry.class_name,
        entry.method_name,
        entry.return_type,
        entry.source_path,
        *entry.parameter_types,
        *entry.tags,
        *entry.evidence,
    )
    lowered_query = query.lower()
    return any(lowered_query in value.lower() for value in haystacks)


def _known_workspace_roots(
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
) -> tuple[Path, ...]:
    registry = registry_service.load()
    roots: list[Path] = []
    seen: set[Path] = set()

    for root in (default_workspace_root, *registry.known_workspace_roots):
        normalized_root = root.expanduser()
        if normalized_root in seen:
            continue
        seen.add(normalized_root)
        roots.append(normalized_root)

    return tuple(roots)


class SupportsJadxResolve(Protocol):
    def __call__(self, explicit_path: str | None) -> str | None: ...


class SupportsJadxOpen(Protocol):
    def __call__(self, jadx_gui_path: str, target_path: Path) -> object: ...


@dataclass(frozen=True, slots=True)
class WorkspaceInspectionRecord:
    case_id: str
    title: str
    workspace_root: Path
    sample_path: Path
    bundle: StaticWorkspaceBundle
    custom_scripts: tuple[CustomScriptRecord, ...]

    @property
    def jadx_target_path(self) -> Path:
        artifact_paths = self.bundle.static_inputs.artifact_paths
        return artifact_paths.jadx_sources or artifact_paths.jadx_project or self.sample_path

    @property
    def has_method_index(self) -> bool:
        return self.bundle.static_inputs.artifact_paths.jadx_sources is not None


class WorkspaceInspectionService:
    def __init__(
        self,
        *,
        registry_service: WorkspaceRegistryService,
        default_workspace_root: Path,
        job_service: JobService | None = None,
        case_queue_service: CaseQueueService | None = None,
        custom_script_service: CustomScriptService | None = None,
        hook_advisor: OfflineHookAdvisor | None = None,
        jadx_gui_resolver: SupportsJadxResolve | None = None,
        jadx_opener: SupportsJadxOpen | None = None,
    ) -> None:
        self._registry_service = registry_service
        self._default_workspace_root = default_workspace_root
        self._job_service = job_service or JobService()
        self._case_queue_service = case_queue_service or CaseQueueService()
        self._custom_script_service = custom_script_service or CustomScriptService(
            default_workspace_root.parent / "custom-scripts"
        )
        self._hook_advisor = hook_advisor or OfflineHookAdvisor()
        self._jadx_gui_resolver = jadx_gui_resolver or resolve_jadx_gui_path
        self._jadx_opener = jadx_opener or open_in_jadx
        self._cache: dict[str, WorkspaceInspectionRecord] = {}

    def get_detail(self, case_id: str) -> WorkspaceInspectionRecord:
        record = self._load_case(case_id)
        custom_scripts = self._custom_script_service.discover_records()
        if record.custom_scripts == custom_scripts:
            return record
        refreshed = replace(record, custom_scripts=custom_scripts)
        self._cache[case_id] = refreshed
        return refreshed

    def search_methods(self, case_id: str, *, query: str = "", limit: int = 50) -> tuple[tuple[MethodIndexEntry, ...], int]:
        record = self._load_case(case_id)
        if not record.has_method_index:
            return (), 0

        filtered = [
            method
            for method in record.bundle.method_index.methods
            if _method_matches(method, query)
        ]
        filtered.sort(key=lambda item: (item.class_name, item.method_name, item.source_path, item.line_hint or 0))
        return tuple(filtered[: max(limit, 0)]), len(filtered)

    def get_recommendations(self, case_id: str, *, limit: int = 8) -> tuple[HookRecommendation, ...]:
        record = self._load_case(case_id)
        safe_limit = max(limit, 0)
        return self._hook_advisor.recommend(
            record.bundle.static_inputs,
            record.bundle.method_index,
            limit=safe_limit,
        )

    def open_in_jadx(self, case_id: str, *, explicit_path: str | None = None) -> Path:
        record = self._load_case(case_id)
        jadx_gui_path = self._jadx_gui_resolver(explicit_path)
        if jadx_gui_path is None:
            raise JadxUnavailableError("jadx-gui is not configured or not available")
        target_path = record.jadx_target_path
        self._jadx_opener(jadx_gui_path, target_path)
        return target_path

    def can_open_in_jadx(self, case_id: str, *, explicit_path: str | None = None) -> bool:
        self._load_case(case_id)
        return self._jadx_gui_resolver(explicit_path) is not None

    def _load_case(self, case_id: str) -> WorkspaceInspectionRecord:
        cached = self._cache.get(case_id)
        if cached is not None:
            return cached

        workspace_root, title = self._locate_workspace(case_id)
        metadata = _load_workspace_metadata(workspace_root)
        sample_filename = _normalize_text(metadata.get("sample_filename")) or "original.apk"
        sample_path = workspace_root / "sample" / sample_filename
        bundle = self._job_service.load_static_workspace_bundle(
            sample_path,
            output_dir=workspace_root / "static",
        )
        record = WorkspaceInspectionRecord(
            case_id=case_id,
            title=title,
            workspace_root=workspace_root,
            sample_path=sample_path,
            bundle=bundle,
            custom_scripts=self._custom_script_service.discover_records(),
        )
        self._cache[case_id] = record
        return record

    def _locate_workspace(self, case_id: str) -> tuple[Path, str]:
        for workspace_root in _known_workspace_roots(self._registry_service, self._default_workspace_root):
            items = self._case_queue_service.list_cases(workspace_root)
            for item in items:
                if item.case_id == case_id:
                    return item.workspace_root, item.title
        raise CaseNotFoundError(case_id)
