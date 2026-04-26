from __future__ import annotations

from dataclasses import dataclass

from apk_hacker.domain.models.indexes import MethodIndexEntry


@dataclass(frozen=True, slots=True)
class HookRecommendation:
    recommendation_id: str
    kind: str
    title: str
    reason: str
    score: int
    matched_terms: tuple[str, ...]
    method: MethodIndexEntry | None = None
    template_id: str | None = None
    template_name: str | None = None
    plugin_id: str | None = None
    source_signals: tuple[str, ...] = ()
    template_event_types: tuple[str, ...] = ()
    template_category: str | None = None
    requires_root: bool = False
    supports_offline: bool = True
