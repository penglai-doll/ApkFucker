from __future__ import annotations

from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry


class HookSearch:
    def search(self, index: MethodIndex, query: str, limit: int | None = None) -> tuple[MethodIndexEntry, ...]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            results = index.methods
        else:
            results = tuple(
                entry
                for entry in index.methods
                if normalized_query in self._search_blob(entry)
            )

        if limit is None:
            return results
        return results[:limit]

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
