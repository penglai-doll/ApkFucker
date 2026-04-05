from __future__ import annotations

from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry


class HookSearch:
    def search(self, index: MethodIndex, query: str, limit: int | None = None) -> tuple[MethodIndexEntry, ...]:
        query_terms = tuple(term for term in query.strip().lower().split() if term)
        if not query_terms:
            results = index.methods
        else:
            results = tuple(
                entry
                for entry in index.methods
                if self._matches(entry, query_terms)
            )

        if limit is None:
            return results
        return results[:limit]

    def _matches(self, entry: MethodIndexEntry, query_terms: tuple[str, ...]) -> bool:
        blob = self._search_blob(entry)
        return all(term in blob for term in query_terms)

    def _search_blob(self, entry: MethodIndexEntry) -> str:
        parts = [
            entry.class_name,
            entry.method_name,
            entry.return_type,
            *entry.parameter_types,
            *entry.tags,
            *entry.evidence,
        ]
        return " ".join(parts).lower()
