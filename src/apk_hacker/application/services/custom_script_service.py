from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


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
