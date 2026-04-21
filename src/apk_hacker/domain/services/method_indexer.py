from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from apk_hacker.domain.models.indexes import ClassIndexEntry
from apk_hacker.domain.models.indexes import MethodIndex
from apk_hacker.domain.models.indexes import MethodIndexEntry


PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
CLASS_DECL_RE = re.compile(r"\b(?:class|interface|enum)\s+([A-Za-z0-9_]+)\b")
ANNOTATION_RE = re.compile(r"@[A-Za-z0-9_$.]+(?:\([^)]*\))?\s*")
INLINE_COMMENT_RE = re.compile(r"//.*$")
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
MODIFIER_PREFIX_RE = re.compile(
    r"^(?:public|protected|private|static|final|synchronized|native|abstract|default|strictfp)\b\s*"
)

CONTROL_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "throw",
    "new",
    "do",
    "else",
    "try",
    "super",
    "this",
}


def _derive_package_name(source_file: Path, sources_root: Path, text: str) -> str:
    package_match = PACKAGE_RE.search(text)
    if package_match is not None:
        return package_match.group(1)
    relative_parent = source_file.relative_to(sources_root).parent
    if relative_parent == Path("."):
        return ""
    return ".".join(relative_parent.parts)


def _strip_inline_comments(text: str) -> str:
    return INLINE_COMMENT_RE.sub("", BLOCK_COMMENT_RE.sub(" ", text)).strip()


def _count_parentheses(text: str) -> int:
    return text.count("(") - text.count(")")


def _normalize_declaration(lines: list[str]) -> str:
    joined = " ".join(_strip_inline_comments(line) for line in lines)
    normalized = " ".join(joined.replace("{", " ").replace(";", " ").split())
    return normalized.strip()


def _split_parameters(raw_params: str) -> tuple[str, ...]:
    if not raw_params.strip():
        return ()

    parts: list[str] = []
    current: list[str] = []
    angle_depth = 0
    paren_depth = 0
    for char in raw_params:
        if char == "<":
            angle_depth += 1
        elif char == ">" and angle_depth > 0:
            angle_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1
        elif char == "," and angle_depth == 0 and paren_depth == 0:
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

    tokens = [token for token in cleaned.split() if token not in {"final"}]
    if not tokens:
        return None
    if len(tokens) == 1:
        return tokens[0]
    return " ".join(tokens[:-1])


def _looks_like_method_start(line: str) -> bool:
    stripped = _strip_inline_comments(line)
    candidate = ANNOTATION_RE.sub("", stripped).strip()
    if not candidate or "(" not in candidate:
        return False
    if CLASS_DECL_RE.search(candidate):
        return False
    leading = candidate.split("(", 1)[0].strip().split()
    if not leading:
        return False
    first_token = leading[0]
    return first_token not in CONTROL_KEYWORDS


def _consume_angle_block(text: str) -> tuple[str, str]:
    if not text.startswith("<"):
        return "", text

    depth = 0
    for index, char in enumerate(text):
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return text[: index + 1].strip(), text[index + 1 :].strip()
    return "", text


def _find_param_span(text: str) -> tuple[int, int] | None:
    start = text.find("(")
    if start < 0:
        return None

    depth = 0
    angle_depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "<":
            angle_depth += 1
        elif char == ">" and angle_depth > 0:
            angle_depth -= 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return start, index
    return None


def _strip_leading_annotations(text: str) -> str:
    remaining = text.strip()
    while True:
        updated = ANNOTATION_RE.sub("", remaining, count=1).strip()
        if updated == remaining:
            return remaining
        remaining = updated


def _strip_leading_modifiers(text: str) -> str:
    remaining = text.strip()
    while True:
        updated = MODIFIER_PREFIX_RE.sub("", remaining, count=1).strip()
        if updated == remaining:
            return remaining
        remaining = updated


def _strip_throws_clause(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("throws "):
        return ""
    return stripped


def _parse_method_declaration(
    declaration: str,
    *,
    current_class_name: str,
) -> tuple[str, str, tuple[str, ...], bool] | None:
    cleaned = _strip_leading_annotations(declaration)
    span = _find_param_span(cleaned)
    if span is None:
        return None
    param_start, param_end = span

    before_params = cleaned[:param_start].strip()
    raw_params = cleaned[param_start + 1 : param_end].strip()
    suffix = _strip_throws_clause(cleaned[param_end + 1 :].strip())
    if suffix not in {"", "{", ";"} and not suffix.endswith("{") and not suffix.endswith(";"):
        return None

    method_name_match = re.search(r"([A-Za-z0-9_$]+)$", before_params)
    if method_name_match is None:
        return None

    method_name = method_name_match.group(1)
    if method_name in CONTROL_KEYWORDS:
        return None

    prefix = before_params[: method_name_match.start()].strip()
    prefix = _strip_leading_modifiers(prefix)
    _type_params, prefix = _consume_angle_block(prefix)
    raw_return_type = _strip_leading_modifiers(prefix).strip()
    is_constructor = not raw_return_type or method_name == current_class_name
    return_type = current_class_name if is_constructor else raw_return_type
    parameter_types = tuple(
        parameter_type
        for parameter_type in (
            _extract_parameter_type(part)
            for part in _split_parameters(raw_params)
        )
        if parameter_type is not None
    )
    return method_name, return_type, parameter_types, is_constructor


def _source_preview(lines: list[str], start_line: int, end_line: int) -> str:
    start_index = max(start_line - 1, 0)
    end_index = min(len(lines), end_line + 3)
    return "\n".join(lines[start_index:end_index]).strip()


def _fqcn(package_name: str, class_stack: list[tuple[str, int]]) -> str:
    class_path = "$".join(name for name, _ in class_stack)
    return f"{package_name}.{class_path}" if package_name else class_path


class JavaMethodIndexer:
    def build(
        self,
        sources_root: Path,
        *,
        package_prefixes: tuple[str, ...] = (),
    ) -> MethodIndex:
        classes_by_name: dict[str, ClassIndexEntry] = {}
        methods: list[MethodIndexEntry] = []

        source_files = self._candidate_source_files(sources_root, package_prefixes)

        for source_file in source_files:
            text = source_file.read_text(encoding="utf-8")
            package_name = _derive_package_name(source_file, sources_root, text)
            source_path = source_file.relative_to(sources_root).as_posix()
            lines = text.splitlines()
            brace_depth = 0
            class_stack: list[tuple[str, int]] = []
            pending_class_name: str | None = None
            capture_lines: list[str] = []
            capture_start_line: int | None = None
            capture_paren_depth = 0

            for line_number, raw_line in enumerate(lines, start=1):
                stripped = _strip_inline_comments(raw_line)
                opens = raw_line.count("{")
                closes = raw_line.count("}")

                if capture_lines:
                    capture_lines.append(raw_line)
                    capture_paren_depth += _count_parentheses(raw_line)
                    if capture_paren_depth <= 0 and ("{" in stripped or stripped.endswith(";")):
                        declaration = _normalize_declaration(capture_lines)
                        if class_stack and capture_start_line is not None:
                            current_class_name = class_stack[-1][0]
                            parsed = _parse_method_declaration(
                                declaration,
                                current_class_name=current_class_name,
                            )
                            if parsed is not None:
                                method_name, return_type, parameter_types, is_constructor = parsed
                                fqcn = _fqcn(package_name, class_stack)
                                methods.append(
                                    MethodIndexEntry(
                                        class_name=fqcn,
                                        method_name=method_name,
                                        parameter_types=parameter_types,
                                        return_type=return_type,
                                        is_constructor=is_constructor,
                                        overload_count=1,
                                        source_path=source_path,
                                        line_hint=capture_start_line,
                                        declaration=declaration,
                                        source_preview=_source_preview(lines, capture_start_line, line_number),
                                    )
                                )
                                classes_by_name.setdefault(
                                    fqcn,
                                    ClassIndexEntry(
                                        class_name=fqcn,
                                        package_name=package_name,
                                        source_path=source_path,
                                        method_count=0,
                                    ),
                                )
                        capture_lines = []
                        capture_start_line = None
                        capture_paren_depth = 0

                elif class_stack and _looks_like_method_start(raw_line):
                    capture_lines = [raw_line]
                    capture_start_line = line_number
                    capture_paren_depth = _count_parentheses(raw_line)
                    if capture_paren_depth <= 0 and ("{" in stripped or stripped.endswith(";")):
                        declaration = _normalize_declaration(capture_lines)
                        current_class_name = class_stack[-1][0]
                        parsed = _parse_method_declaration(
                            declaration,
                            current_class_name=current_class_name,
                        )
                        if parsed is not None:
                            method_name, return_type, parameter_types, is_constructor = parsed
                            fqcn = _fqcn(package_name, class_stack)
                            methods.append(
                                MethodIndexEntry(
                                    class_name=fqcn,
                                    method_name=method_name,
                                    parameter_types=parameter_types,
                                    return_type=return_type,
                                    is_constructor=is_constructor,
                                    overload_count=1,
                                    source_path=source_path,
                                    line_hint=capture_start_line,
                                    declaration=declaration,
                                    source_preview=_source_preview(lines, capture_start_line, line_number),
                                )
                            )
                            classes_by_name.setdefault(
                                fqcn,
                                ClassIndexEntry(
                                    class_name=fqcn,
                                    package_name=package_name,
                                    source_path=source_path,
                                    method_count=0,
                                ),
                            )
                        capture_lines = []
                        capture_start_line = None
                        capture_paren_depth = 0

                if pending_class_name is None:
                    class_match = CLASS_DECL_RE.search(stripped)
                    if class_match is not None:
                        pending_class_name = class_match.group(1)

                brace_depth += opens - closes

                if pending_class_name is not None and opens > 0:
                    class_stack.append((pending_class_name, brace_depth))
                    fqcn = _fqcn(package_name, class_stack)
                    classes_by_name.setdefault(
                        fqcn,
                        ClassIndexEntry(
                            class_name=fqcn,
                            package_name=package_name,
                            source_path=source_path,
                            method_count=0,
                        ),
                    )
                    pending_class_name = None

                while class_stack and brace_depth < class_stack[-1][1]:
                    class_stack.pop()

            overload_counts: Counter[tuple[str, str]] = Counter(
                (entry.class_name, entry.method_name) for entry in methods if entry.source_path == source_path
            )

            for index, entry in enumerate(methods):
                if entry.source_path != source_path:
                    continue
                methods[index] = MethodIndexEntry(
                    class_name=entry.class_name,
                    method_name=entry.method_name,
                    parameter_types=entry.parameter_types,
                    return_type=entry.return_type,
                    is_constructor=entry.is_constructor,
                    overload_count=overload_counts[(entry.class_name, entry.method_name)],
                    source_path=entry.source_path,
                    line_hint=entry.line_hint,
                    declaration=entry.declaration,
                    source_preview=entry.source_preview,
                    tags=entry.tags,
                    evidence=entry.evidence,
                )

        method_counts: Counter[str] = Counter(entry.class_name for entry in methods)
        classes = tuple(
            ClassIndexEntry(
                class_name=entry.class_name,
                package_name=entry.package_name,
                source_path=entry.source_path,
                method_count=method_counts.get(entry.class_name, 0),
                tags=entry.tags,
            )
            for entry in sorted(classes_by_name.values(), key=lambda item: item.class_name)
        )
        methods.sort(key=lambda item: (item.class_name, item.method_name, item.line_hint or 0, item.source_path))
        return MethodIndex(classes=classes, methods=tuple(methods))

    def _candidate_source_files(
        self,
        sources_root: Path,
        package_prefixes: tuple[str, ...],
    ) -> tuple[Path, ...]:
        all_source_files = tuple(sorted(sources_root.rglob("*.java")))
        normalized_prefixes = tuple(
            prefix.strip(". ").replace(".", "/")
            for prefix in package_prefixes
            if prefix and prefix.strip(". ")
        )
        if not normalized_prefixes:
            return all_source_files

        preferred_source_files = tuple(
            source_file
            for source_file in all_source_files
            if any(
                source_file.relative_to(sources_root).as_posix().startswith(f"{prefix}/")
                or source_file.relative_to(sources_root).as_posix() == f"{prefix}.java"
                for prefix in normalized_prefixes
            )
        )
        return preferred_source_files or all_source_files
