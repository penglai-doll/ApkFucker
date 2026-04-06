from __future__ import annotations

from collections.abc import Callable
import importlib.util
import shutil

from apk_hacker.domain.models.environment import EnvironmentSnapshot, ToolStatus


BINARY_TOOL_CATALOG: tuple[tuple[str, str], ...] = (
    ("jadx", "jadx"),
    ("jadx-gui", "jadx-gui"),
    ("apktool", "apktool"),
    ("adb", "adb"),
    ("frida", "frida"),
)

PYTHON_MODULE_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("frida", "python-frida", "module:frida"),
)


class EnvironmentService:
    def __init__(
        self,
        resolver: Callable[[str], str | None] | None = None,
        module_resolver: Callable[[str], object | None] | None = None,
    ) -> None:
        self._resolver = resolver or shutil.which
        self._module_resolver = module_resolver or importlib.util.find_spec

    def inspect(self) -> EnvironmentSnapshot:
        binary_tools = tuple(
            ToolStatus(
                name=name,
                label=label,
                available=(resolved := self._resolver(name)) is not None,
                path=resolved,
            )
            for name, label in BINARY_TOOL_CATALOG
        )
        python_modules = tuple(
            ToolStatus(
                name=label,
                label=label,
                available=(resolved := self._module_resolver(module_name)) is not None,
                path=display_path if resolved is not None else None,
            )
            for module_name, label, display_path in PYTHON_MODULE_CATALOG
        )
        return EnvironmentSnapshot(tools=(*binary_tools, *python_modules))
