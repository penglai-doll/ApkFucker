from __future__ import annotations

from collections.abc import Callable
import shutil

from apk_hacker.domain.models.environment import EnvironmentSnapshot, ToolStatus


TOOL_CATALOG: tuple[tuple[str, str], ...] = (
    ("jadx", "jadx"),
    ("jadx-gui", "jadx-gui"),
    ("apktool", "apktool"),
    ("adb", "adb"),
    ("frida", "frida"),
)


class EnvironmentService:
    def __init__(self, resolver: Callable[[str], str | None] | None = None) -> None:
        self._resolver = resolver or shutil.which

    def inspect(self) -> EnvironmentSnapshot:
        tools = tuple(
            ToolStatus(
                name=name,
                label=label,
                available=(resolved := self._resolver(name)) is not None,
                path=resolved,
            )
            for name, label in TOOL_CATALOG
        )
        return EnvironmentSnapshot(tools=tools)
