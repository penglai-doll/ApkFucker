from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassIndexEntry:
    class_name: str
    package_name: str
    source_path: str
    method_count: int
    tags: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "class_name": self.class_name,
            "package_name": self.package_name,
            "source_path": self.source_path,
            "method_count": self.method_count,
            "tags": list(self.tags),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "ClassIndexEntry | None":
        if not isinstance(payload, dict):
            return None
        class_name = payload.get("class_name")
        package_name = payload.get("package_name")
        source_path = payload.get("source_path")
        method_count = payload.get("method_count")
        if not isinstance(class_name, str) or not isinstance(package_name, str):
            return None
        if not isinstance(source_path, str) or not isinstance(method_count, int):
            return None
        tags = payload.get("tags", [])
        return cls(
            class_name=class_name,
            package_name=package_name,
            source_path=source_path,
            method_count=method_count,
            tags=tuple(str(value) for value in tags) if isinstance(tags, list) else (),
        )


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
    declaration: str = ""
    source_preview: str = ""
    tags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "class_name": self.class_name,
            "method_name": self.method_name,
            "parameter_types": list(self.parameter_types),
            "return_type": self.return_type,
            "is_constructor": self.is_constructor,
            "overload_count": self.overload_count,
            "source_path": self.source_path,
            "line_hint": self.line_hint,
            "declaration": self.declaration,
            "source_preview": self.source_preview,
            "tags": list(self.tags),
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_payload(cls, payload: object) -> "MethodIndexEntry | None":
        if not isinstance(payload, dict):
            return None
        class_name = payload.get("class_name")
        method_name = payload.get("method_name")
        return_type = payload.get("return_type")
        source_path = payload.get("source_path")
        if not isinstance(class_name, str) or not isinstance(method_name, str):
            return None
        if not isinstance(return_type, str) or not isinstance(source_path, str):
            return None
        parameter_types = payload.get("parameter_types", [])
        tags = payload.get("tags", [])
        evidence = payload.get("evidence", [])
        line_hint = payload.get("line_hint")
        declaration = payload.get("declaration", "")
        source_preview = payload.get("source_preview", "")
        return cls(
            class_name=class_name,
            method_name=method_name,
            parameter_types=tuple(str(value) for value in parameter_types) if isinstance(parameter_types, list) else (),
            return_type=return_type,
            is_constructor=bool(payload.get("is_constructor", False)),
            overload_count=int(payload.get("overload_count", 1)),
            source_path=source_path,
            line_hint=line_hint if isinstance(line_hint, int) else None,
            declaration=declaration if isinstance(declaration, str) else "",
            source_preview=source_preview if isinstance(source_preview, str) else "",
            tags=tuple(str(value) for value in tags) if isinstance(tags, list) else (),
            evidence=tuple(str(value) for value in evidence) if isinstance(evidence, list) else (),
        )


@dataclass(frozen=True, slots=True)
class MethodIndex:
    classes: tuple[ClassIndexEntry, ...]
    methods: tuple[MethodIndexEntry, ...]
