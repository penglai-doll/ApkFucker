from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolStatus:
    name: str
    label: str
    available: bool
    path: str | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    tools: tuple[ToolStatus, ...]

    @property
    def available_count(self) -> int:
        return sum(1 for tool in self.tools if tool.available)

    @property
    def missing_count(self) -> int:
        return sum(1 for tool in self.tools if not tool.available)

    @property
    def summary(self) -> str:
        return f"{self.available_count} available, {self.missing_count} missing"
