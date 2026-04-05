from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from apk_hacker.domain.models.hook_plan import HookPlanItem


@dataclass(frozen=True, slots=True)
class CustomScriptRecord:
    script_id: str
    name: str
    script_path: Path


class CustomScriptService:
    def __init__(self, scripts_root: Path) -> None:
        self._scripts_root = scripts_root

    def discover(self) -> list[CustomScriptRecord]:
        self._scripts_root.mkdir(parents=True, exist_ok=True)
        records: list[CustomScriptRecord] = []
        for script_path in sorted(self._scripts_root.glob("*.js")):
            records.append(
                CustomScriptRecord(
                    script_id=str(uuid4()),
                    name=script_path.stem,
                    script_path=script_path,
                )
            )
        return records

    def build_plan_item(self, record: CustomScriptRecord, inject_order: int) -> HookPlanItem:
        return HookPlanItem(
            item_id=str(uuid4()),
            kind="custom_script",
            enabled=True,
            inject_order=inject_order,
            target=None,
            render_context={"script_path": str(record.script_path)},
            plugin_id="custom.local-script",
        )
