from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class CustomScriptRecord:
    script_id: str
    name: str
    script_path: Path


@dataclass(frozen=True, slots=True)
class CustomScriptDocument:
    record: CustomScriptRecord
    content: str


class CustomScriptService:
    def __init__(self, scripts_root: Path) -> None:
        self._scripts_root = scripts_root

    @property
    def scripts_root(self) -> Path:
        return self._scripts_root

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
        self._validate_content(content)

        self._scripts_root.mkdir(parents=True, exist_ok=True)
        script_path = self._scripts_root / f"{normalized_name}.js"
        script_path.write_text(content, encoding="utf-8")
        return self._record_for_path(script_path)

    def get_record(self, script_id: str) -> CustomScriptRecord:
        record = next((item for item in self.discover_records() if item.script_id == script_id), None)
        if record is None:
            raise KeyError(script_id)
        return record

    def read_script_document(self, script_id: str) -> CustomScriptDocument:
        record = self.get_record(script_id)
        return CustomScriptDocument(record=record, content=self.read_script(record))

    def update_script(self, script_id: str, name: str, content: str) -> CustomScriptRecord:
        normalized_name = self._normalize_name(name)
        self._validate_content(content)
        record = self.get_record(script_id)
        target_path = self._scripts_root / f"{normalized_name}.js"
        if target_path != record.script_path and target_path.exists():
            raise ValueError("Script name already exists.")
        target_path.write_text(content, encoding="utf-8")
        if target_path != record.script_path and record.script_path.exists():
            record.script_path.unlink()
        return self._record_for_path(target_path)

    def delete_script(self, script_id: str) -> CustomScriptRecord:
        record = self.get_record(script_id)
        record.script_path.unlink()
        return record

    @staticmethod
    def read_script(record: CustomScriptRecord) -> str:
        return record.script_path.read_text(encoding="utf-8")

    @staticmethod
    def _record_for_path(script_path: Path) -> CustomScriptRecord:
        return CustomScriptRecord(
            script_id=f"custom_script:{script_path}",
            name=script_path.stem,
            script_path=script_path,
        )

    @staticmethod
    def _validate_content(content: str) -> None:
        if not content.strip():
            raise ValueError("Script content cannot be empty.")

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
