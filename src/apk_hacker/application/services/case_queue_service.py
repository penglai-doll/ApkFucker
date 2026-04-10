from __future__ import annotations

import json
from pathlib import Path

from apk_hacker.domain.models.case_queue import CaseQueueItem


def _text_value(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class CaseQueueService:
    def list_cases(self, workspace_root: Path) -> tuple[CaseQueueItem, ...]:
        root = workspace_root.expanduser()
        if not root.exists():
            return ()

        items: list[CaseQueueItem] = []
        for workspace_json in sorted(root.glob("*/workspace.json")):
            try:
                payload = json.loads(workspace_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if not isinstance(payload, dict):
                continue

            case_id = _text_value(payload.get("case_id"))
            title = _text_value(payload.get("title"))
            if case_id is None or title is None:
                continue

            items.append(
                CaseQueueItem(
                    case_id=case_id,
                    title=title,
                    workspace_root=workspace_json.parent,
                )
            )

        return tuple(sorted(items, key=lambda item: (item.case_id, item.title)))
