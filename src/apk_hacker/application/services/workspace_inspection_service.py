from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import replace
import json
import re
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

VALID_METHOD_SCOPES = ("first_party", "related_candidates", "all")
_RELATED_CANDIDATE_STOPWORDS = {
    "android",
    "app",
    "com",
    "demo",
    "example",
    "file",
    "java",
    "id",
    "org",
    "path",
    "sample",
    "shell",
    "source",
    "sources",
    "tmp",
    "www",
}
_TERM_RE = re.compile(r"[A-Za-z0-9]+")


class CaseNotFoundError(KeyError):
    pass


class JadxUnavailableError(RuntimeError):
    pass


def _normalize_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unique_texts(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _terms_from_text(value: object | None) -> tuple[str, ...]:
    normalized = _normalize_text(value)
    if normalized is None:
        return ()

    terms: list[str] = [normalized.lower()]
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", normalized)
    camel_spaced = camel_spaced.replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ").replace("$", " ")
    for token in _TERM_RE.findall(camel_spaced):
        lowered = token.lower()
        if lowered and lowered not in _RELATED_CANDIDATE_STOPWORDS:
            terms.append(lowered)
    return _unique_texts(tuple(terms))


def _terms_from_values(values: tuple[str, ...]) -> tuple[str, ...]:
    terms: list[str] = []
    for value in values:
        terms.extend(_terms_from_text(value))
    return _unique_texts(tuple(terms))


def _method_blob(entry: MethodIndexEntry) -> str:
    values = (
        entry.class_name,
        entry.method_name,
        entry.return_type,
        entry.source_path,
        entry.declaration,
        entry.source_preview,
        *entry.parameter_types,
        *entry.tags,
        *entry.evidence,
    )
    return " ".join(value.lower() for value in values if value).strip()


def _method_matches_any_term(entry: MethodIndexEntry, terms: tuple[str, ...]) -> bool:
    if not terms:
        return False
    blob = _method_blob(entry)
    return any(term in blob for term in terms if term)


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
        entry.declaration,
        entry.source_preview,
        *entry.parameter_types,
        *entry.tags,
        *entry.evidence,
    )
    lowered_query = query.lower()
    return any(lowered_query in value.lower() for value in haystacks if value)


def _recommendation_matches(entry: HookRecommendation, query: str) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    if entry.method is not None and _method_matches(entry.method, normalized_query):
        return True
    haystacks = (
        entry.title,
        entry.reason,
        entry.template_id,
        entry.template_name,
        entry.plugin_id,
        *entry.matched_terms,
    )
    return any(normalized_query in value.lower() for value in haystacks if value)


def _method_search_score(entry: MethodIndexEntry, query: str) -> int:
    normalized_query = query.strip().lower()
    if not normalized_query:
        evidence_bonus = 25 if entry.evidence else 0
        tag_bonus = min(len(entry.tags), 3) * 5
        constructor_penalty = -10 if entry.is_constructor else 0
        return evidence_bonus + tag_bonus + constructor_penalty

    terms = tuple(term for term in normalized_query.split() if term)
    if not terms:
        return 0

    total = 0
    short_class_name = entry.class_name.rsplit("$", 1)[-1].rsplit(".", 1)[-1].lower()
    declaration = entry.declaration.lower()
    preview = entry.source_preview.lower()
    for term in terms:
        term_score = -1
        if entry.method_name.lower() == term:
            term_score = 120
        elif entry.method_name.lower().startswith(term):
            term_score = 100
        elif term in entry.method_name.lower():
            term_score = 80
        elif short_class_name == term:
            term_score = 70
        elif short_class_name.startswith(term):
            term_score = 60
        elif term in entry.class_name.lower():
            term_score = 50
        elif term in declaration:
            term_score = 40
        elif term in preview:
            term_score = 25
        elif any(term in value.lower() for value in entry.parameter_types):
            term_score = 20
        elif any(term in value.lower() for value in entry.tags):
            term_score = 15
        elif any(term in value.lower() for value in entry.evidence):
            term_score = 10

        if term_score < 0:
            return -1
        total += term_score
    if entry.evidence:
        total += 10
    if entry.tags:
        total += 5
    return total


def _related_candidate_score(entry: MethodIndexEntry, query: str, related_terms: tuple[str, ...]) -> int | None:
    relation_bonus = 0
    if related_terms:
        blob = _method_blob(entry)
        matched_terms = tuple(term for term in related_terms if term and term in blob)
        if matched_terms:
            relation_bonus = min(len(matched_terms), 4) * 12
    if relation_bonus <= 0 and query:
        query_score = _method_search_score(entry, query)
        return query_score if query_score >= 0 else None
    if not query:
        return relation_bonus + max(_method_search_score(entry, ""), 0)

    query_score = _method_search_score(entry, query)
    if query_score < 0:
        return relation_bonus or None
    return query_score + relation_bonus


def _first_party_rank(entry: MethodIndexEntry, package_name: str) -> int:
    normalized_package = package_name.strip().lower()
    if not normalized_package:
        return 1
    return 0 if entry.class_name.lower().startswith(normalized_package) else 1


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
        self._custom_scripts_base_root = (
            custom_script_service.scripts_root if custom_script_service is not None else None
        )
        self._hook_advisor = hook_advisor or OfflineHookAdvisor()
        self._jadx_gui_resolver = jadx_gui_resolver or resolve_jadx_gui_path
        self._jadx_opener = jadx_opener or open_in_jadx
        self._cache: dict[str, WorkspaceInspectionRecord] = {}
        self._expanded_index_cache: dict[tuple[str, str], tuple[MethodIndexEntry, ...]] = {}

    def get_detail(self, case_id: str) -> WorkspaceInspectionRecord:
        record = self._load_case(case_id)
        custom_scripts = self._custom_script_service_for(record.workspace_root).discover_records()
        if record.custom_scripts == custom_scripts:
            return record
        refreshed = replace(record, custom_scripts=custom_scripts)
        self._cache[case_id] = refreshed
        return refreshed

    def refresh_detail(self, case_id: str) -> WorkspaceInspectionRecord:
        self._cache.pop(case_id, None)
        self._expanded_index_cache.pop((case_id, "all"), None)
        return self.get_detail(case_id)

    def search_methods(
        self,
        case_id: str,
        *,
        scope: str = "first_party",
        query: str = "",
        limit: int = 50,
    ) -> tuple[tuple[MethodIndexEntry, ...], int, str]:
        record = self._load_case(case_id)
        if not record.has_method_index:
            return (), 0, "first_party"

        normalized_scope = scope if scope in VALID_METHOD_SCOPES else "first_party"
        if normalized_scope == "all":
            method_pool = self._all_methods_for_record(case_id, record)
        elif normalized_scope == "related_candidates":
            method_pool = self._related_methods_for_record(case_id, record)
        else:
            method_pool = record.bundle.method_index.methods

        package_name = record.bundle.static_inputs.package_name
        related_terms = self._related_candidate_terms(record) if normalized_scope == "related_candidates" else ()
        scored = [
            (
                method,
                _related_candidate_score(method, query, related_terms)
                if normalized_scope == "related_candidates"
                else _method_search_score(method, query),
            )
            for method in method_pool
            if (
                normalized_scope != "related_candidates"
                and _method_matches(method, query)
                or normalized_scope == "related_candidates"
                and self._related_method_is_visible(method, query, package_name, related_terms)
            )
        ]
        scored = [(method, score) for method, score in scored if score >= 0]
        if normalized_scope == "related_candidates":
            scored.sort(
                key=lambda item: (
                    _first_party_rank(item[0], package_name),
                    -item[1],
                    item[0].class_name,
                    item[0].method_name,
                    item[0].source_path,
                    item[0].line_hint or 0,
                )
            )
        else:
            scored.sort(
                key=lambda item: (
                    -item[1],
                    _first_party_rank(item[0], package_name),
                    item[0].class_name,
                    item[0].method_name,
                    item[0].source_path,
                    item[0].line_hint or 0,
                )
            )
        filtered = [method for method, _score in scored]
        return tuple(filtered[: max(limit, 0)]), len(filtered), normalized_scope

    def get_recommendations(
        self,
        case_id: str,
        *,
        limit: int = 8,
        query: str = "",
    ) -> tuple[HookRecommendation, ...]:
        record = self._load_case(case_id)
        safe_limit = max(limit, 0)
        recommendations = self._hook_advisor.recommend(
            record.bundle.static_inputs,
            record.bundle.method_index,
            limit=max(safe_limit * 4, safe_limit, 8),
        )
        filtered = tuple(item for item in recommendations if _recommendation_matches(item, query))
        return filtered[:safe_limit]

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
            custom_scripts=self._custom_script_service_for(workspace_root).discover_records(),
        )
        self._cache[case_id] = record
        return record

    def _custom_script_service_for(self, workspace_root: Path) -> CustomScriptService:
        if self._custom_scripts_base_root is not None:
            return CustomScriptService(self._custom_scripts_base_root / workspace_root.name)
        return CustomScriptService(workspace_root / "scripts")

    def _all_methods_for_record(
        self,
        case_id: str,
        record: WorkspaceInspectionRecord,
    ) -> tuple[MethodIndexEntry, ...]:
        cached = self._expanded_index_cache.get((case_id, "all"))
        if cached is not None:
            return cached

        jadx_sources_dir = record.bundle.static_inputs.artifact_paths.jadx_sources
        if jadx_sources_dir is None:
            return ()

        full_index = self._job_service.build_method_index(jadx_sources_dir)
        self._expanded_index_cache[(case_id, "all")] = full_index.methods
        return full_index.methods

    def _related_candidate_terms(self, record: WorkspaceInspectionRecord) -> tuple[str, ...]:
        static_inputs = record.bundle.static_inputs
        terms = list(
            _terms_from_values(static_inputs.technical_tags)
            + _terms_from_values(static_inputs.dangerous_permissions)
            + _terms_from_values(static_inputs.callback_endpoints)
            + _terms_from_values(static_inputs.callback_clues)
            + _terms_from_values(static_inputs.crypto_signals)
            + _terms_from_values(static_inputs.packer_hints)
        )
        recommendations = self._hook_advisor.recommend(static_inputs, record.bundle.method_index, limit=8)
        for recommendation in recommendations:
            terms.extend(_terms_from_values(recommendation.matched_terms))
        return _unique_texts(tuple(terms))

    def _related_methods_for_record(
        self,
        case_id: str,
        record: WorkspaceInspectionRecord,
    ) -> tuple[MethodIndexEntry, ...]:
        cached = self._expanded_index_cache.get((case_id, "related_candidates"))
        if cached is not None:
            return cached

        related_terms = self._related_candidate_terms(record)
        package_name = record.bundle.static_inputs.package_name
        methods = tuple(
            method
            for method in self._all_methods_for_record(case_id, record)
            if _first_party_rank(method, package_name) == 0 or _method_matches_any_term(method, related_terms)
        )
        self._expanded_index_cache[(case_id, "related_candidates")] = methods
        return methods

    def _related_method_is_visible(
        self,
        method: MethodIndexEntry,
        query: str,
        package_name: str,
        related_terms: tuple[str, ...],
    ) -> bool:
        is_first_party = _first_party_rank(method, package_name) == 0
        if is_first_party:
            return _method_matches(method, query)
        return _method_matches_any_term(method, related_terms)

    def _locate_workspace(self, case_id: str) -> tuple[Path, str]:
        for workspace_root in _known_workspace_roots(self._registry_service, self._default_workspace_root):
            items = self._case_queue_service.list_cases(workspace_root)
            for item in items:
                if item.case_id == case_id:
                    return item.workspace_root, item.title
        raise CaseNotFoundError(case_id)
