from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from apk_hacker.domain.models.indexes import ClassIndexEntry, MethodIndex, MethodIndexEntry


PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
CLASS_RE = re.compile(r"\bclass\s+([A-Za-z0-9_]+)\b")
METHOD_RE = re.compile(
    r"""
    ^\s*
    (?P<visibility>public|protected|private)\s+
    (?:(?:static|final|synchronized|native|abstract|strictfp)\s+)*
    (?:(?P<return_type>[A-Za-z0-9_$.<>\[\]]+)\s+)?
    (?P<method_name>[A-Za-z0-9_]+)
    \((?P<params>[^)]*)\)
    (?:\s+throws\s+[^{]+)?
    \s*\{
    """,
    re.MULTILINE | re.VERBOSE,
)
ANNOTATION_RE = re.compile(r"@\w+(?:\([^)]*\))?\s*")


def _split_parameters(raw_params: str) -> tuple[str, ...]:
    if not raw_params.strip():
        return ()

    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in raw_params:
        if char == "<":
            depth += 1
        elif char == ">" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)

    return tuple(part for part in parts if part)


def _extract_parameter_type(raw_param: str) -> str | None:
    cleaned = ANNOTATION_RE.sub("", raw_param).strip()
    if not cleaned:
        return None

    tokens = [token for token in cleaned.split() if token != "final"]
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0]

    return " ".join(tokens[:-1])


class JavaMethodIndexer:
    def build(self, sources_root: Path) -> MethodIndex:
        classes: list[ClassIndexEntry] = []
        methods: list[MethodIndexEntry] = []

        for source_file in sorted(sources_root.rglob("*.java")):
            text = source_file.read_text(encoding="utf-8")
            package_match = PACKAGE_RE.search(text)
            class_match = CLASS_RE.search(text)
            if package_match is None or class_match is None:
                continue

            package_name = package_match.group(1)
            class_name = class_match.group(1)
            fqcn = f"{package_name}.{class_name}"
            source_path = source_file.relative_to(sources_root).as_posix()

            file_methods: list[MethodIndexEntry] = []
            overload_counts: Counter[str] = Counter()

            for method_match in METHOD_RE.finditer(text):
                method_name = method_match.group("method_name")
                return_type = method_match.group("return_type") or class_name
                parameter_types = tuple(
                    param_type
                    for param_type in (
                        _extract_parameter_type(part)
                        for part in _split_parameters(method_match.group("params"))
                    )
                    if param_type is not None
                )
                overload_counts[method_name] += 1
                file_methods.append(
                    MethodIndexEntry(
                        class_name=fqcn,
                        method_name=method_name,
                        parameter_types=parameter_types,
                        return_type=return_type,
                        is_constructor=method_name == class_name,
                        overload_count=1,
                        source_path=source_path,
                        line_hint=text[: method_match.start()].count("\n") + 1,
                    )
                )

            file_methods = [
                MethodIndexEntry(
                    class_name=entry.class_name,
                    method_name=entry.method_name,
                    parameter_types=entry.parameter_types,
                    return_type=entry.return_type,
                    is_constructor=entry.is_constructor,
                    overload_count=overload_counts[entry.method_name],
                    source_path=entry.source_path,
                    line_hint=entry.line_hint,
                    tags=entry.tags,
                    evidence=entry.evidence,
                )
                for entry in file_methods
            ]

            classes.append(
                ClassIndexEntry(
                    class_name=fqcn,
                    package_name=package_name,
                    source_path=source_path,
                    method_count=len(file_methods),
                )
            )
            methods.extend(file_methods)

        return MethodIndex(classes=tuple(classes), methods=tuple(methods))
