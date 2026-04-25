from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from apk_hacker.domain.models.config import ArtifactPaths, coerce_artifact_paths
from apk_hacker.domain.models.static_inputs import StaticInputs


def _coerce_path(value: object) -> Path:
    return Path(value).expanduser().resolve()


def _text_value(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unique_texts(values: Sequence[object] | object | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable: Sequence[object] = [values]
    elif isinstance(values, Sequence):
        iterable = values
    else:
        iterable = [values]

    seen: set[str] = set()
    normalized: list[str] = []
    for value in iterable:
        text = _text_value(value)
        if text is None or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _collect_clues(section: object) -> tuple[str, ...]:
    if not isinstance(section, Mapping):
        return _unique_texts(section)

    clues: list[str] = []
    for item in section.get("clues", []) or []:
        if isinstance(item, Mapping):
            source = _text_value(item.get("source"))
            value = _text_value(item.get("value"))
            if source and value:
                clues.append(f"{source}: {value}")
            elif value:
                clues.append(value)
            elif source:
                clues.append(source)
        else:
            text = _text_value(item)
            if text:
                clues.append(text)
    return _unique_texts(clues)


def _collect_callback_clues(callback_config: Mapping[str, Any]) -> tuple[str, ...]:
    clues: list[str] = []
    clues.extend(_collect_clues(callback_config))

    string_scan = callback_config.get("string_scan")
    if isinstance(string_scan, Mapping):
        first_party_candidates = string_scan.get("first_party_candidates")
        if isinstance(first_party_candidates, Mapping):
            clues.extend(_collect_clues(first_party_candidates))

    code_inference = callback_config.get("code_inference")
    if isinstance(code_inference, Mapping):
        clues.extend(_collect_clues(code_inference))

    return _unique_texts(clues)


def _collect_endpoints(callback_config: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[object] = []

    endpoints = callback_config.get("endpoints")
    if isinstance(endpoints, Mapping):
        for key in ("urls", "domains", "ips", "emails"):
            values.extend(_unique_texts(endpoints.get(key)))

    code_inference = callback_config.get("code_inference")
    if isinstance(code_inference, Mapping):
        nested_endpoints = code_inference.get("endpoints")
        if isinstance(nested_endpoints, Mapping):
            for key in ("urls", "domains", "ips", "emails"):
                values.extend(_unique_texts(nested_endpoints.get(key)))

    return _unique_texts(values)


def _collect_technical_tags(analysis_report: Mapping[str, Any]) -> tuple[str, ...]:
    tags: list[object] = []

    technical_tags = analysis_report.get("technical_tags")
    if technical_tags:
        tags.extend(technical_tags if isinstance(technical_tags, Sequence) and not isinstance(technical_tags, (str, bytes)) else [technical_tags])
    else:
        technical_profile = analysis_report.get("technical_profile")
        if isinstance(technical_profile, Mapping):
            primary_type = _text_value(technical_profile.get("primary_type"))
            if primary_type:
                tags.append(primary_type)
            for item in technical_profile.get("types", []) or []:
                if isinstance(item, Mapping):
                    name = _text_value(item.get("name"))
                    if name:
                        tags.append(name)
                else:
                    tags.append(item)

    return _unique_texts(tags)


def _collect_list_field(report: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        value = report.get(key)
        if value is None:
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return _unique_texts(value)
        return _unique_texts([value])
    return ()


def _collect_crypto_signals(report: Mapping[str, Any]) -> tuple[str, ...]:
    explicit = _collect_list_field(report, "crypto_signals")
    if explicit:
        return explicit

    crypto_profile = report.get("crypto_profile")
    if not isinstance(crypto_profile, Mapping):
        return ()

    values: list[object] = []
    for key in ("algorithms", "modes", "decryption_methods"):
        values.extend(_unique_texts(crypto_profile.get(key)))
    return _unique_texts(values)


def _collect_packer_hints(report: Mapping[str, Any]) -> tuple[str, ...]:
    explicit = _collect_list_field(report, "packer_hints") or _collect_list_field(report, "packer")
    if explicit:
        return explicit

    values: list[object] = []
    native_summary = report.get("native_summary")
    if isinstance(native_summary, Mapping):
        values.extend(_unique_texts(native_summary.get("packers")))

    triage = report.get("triage")
    if isinstance(triage, Mapping):
        signals = triage.get("signals")
        if isinstance(signals, Sequence) and not isinstance(signals, (str, bytes)):
            for signal in signals:
                if not isinstance(signal, Mapping) or _text_value(signal.get("category")) != "packer":
                    continue
                values.extend(
                    _unique_texts(
                        [
                            signal.get("evidence"),
                            signal.get("rationale"),
                        ]
                    )
                )

    return _unique_texts(values)


class StaticAdapter:
    def adapt(
        self,
        sample_path: Path,
        analysis_report: Mapping[str, Any],
        callback_config: Mapping[str, Any],
        artifact_paths: Mapping[str, object] | ArtifactPaths | None,
    ) -> StaticInputs:
        base_info = analysis_report.get("base_info")
        if not isinstance(base_info, Mapping):
            base_info = {}

        package_name = _text_value(base_info.get("package_name")) or _text_value(analysis_report.get("package_name"))
        if not package_name:
            raise ValueError("analysis_report did not include a package name")

        dangerous_permissions = _collect_list_field(
            base_info,
            "dangerous_permissions",
        ) or _collect_list_field(
            analysis_report,
            "dangerous_permissions",
        )

        return StaticInputs(
            sample_path=_coerce_path(sample_path),
            package_name=package_name,
            technical_tags=_collect_technical_tags(analysis_report),
            dangerous_permissions=dangerous_permissions,
            callback_endpoints=_collect_endpoints(callback_config),
            callback_clues=_collect_callback_clues(callback_config),
            crypto_signals=_collect_crypto_signals(analysis_report),
            packer_hints=_collect_packer_hints(analysis_report),
            limitations=_collect_list_field(analysis_report, "limitations"),
            artifact_paths=coerce_artifact_paths(artifact_paths),
        )
