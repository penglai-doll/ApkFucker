from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassIndexEntry:
    class_name: str
    package_name: str
    source_path: str
    method_count: int
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MethodIndexEntry:
    class_name: str
    method_name: str
    parameter_types: tuple[str, ...]
    return_type: str
    is_constructor: bool
    overload_count: int
    source_path: str
    line_hint: int | None
    tags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MethodIndex:
    classes: tuple[ClassIndexEntry, ...]
    methods: tuple[MethodIndexEntry, ...]
