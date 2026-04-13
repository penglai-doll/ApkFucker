from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class CustomScriptRecord:
    script_id: str
    name: str
    script_path: Path


class CustomScriptService:
    def __init__(self, scripts_root: Path) -> None:
        self._scripts_root = scripts_root

    def discover_records(self) -> tuple[CustomScriptRecord, ...]:
        self._scripts_root.mkdir(parents=True, exist_ok=True)
        records: list[CustomScriptRecord] = []
        for script_path in sorted(self._scripts_root.glob("*.js")):
            records.append(
                CustomScriptRecord(
                    script_id=f"custom_script:{script_path}",
                    name=script_path.stem,
                    script_path=script_path,
                )
            )
        return tuple(records)

    def discover(self) -> list[CustomScriptRecord]:
        return list(self.discover_records())

    def save_script(self, name: str, content: str) -> CustomScriptRecord:
        normalized_name = self._normalize_name(name)
        normalized_content = content.strip()
        if not normalized_content:
            raise ValueError("Script content cannot be empty.")

        self._scripts_root.mkdir(parents=True, exist_ok=True)
        script_path = self._scripts_root / f"{normalized_name}.js"
        script_path.write_text(content, encoding="utf-8")
        return CustomScriptRecord(
            script_id=f"custom_script:{script_path}",
            name=normalized_name,
            script_path=script_path,
        )

    @staticmethod
    def read_script(record: CustomScriptRecord) -> str:
        return record.script_path.read_text(encoding="utf-8")

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if normalized.endswith(".js"):
            normalized = normalized[:-3]
        if not normalized:
            raise ValueError("Script name is required.")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
            raise ValueError("Script name can only contain letters, numbers, dot, dash, and underscore.")
        return normalized
