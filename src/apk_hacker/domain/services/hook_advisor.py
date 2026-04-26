from __future__ import annotations

from dataclasses import dataclass
import re

from apk_hacker.domain.models.hook_advice import HookRecommendation
from apk_hacker.domain.models.indexes import MethodIndex, MethodIndexEntry
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.services.offline_rule_engine import OfflineRuleEngine


TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
STOPWORDS = {
    "android",
    "apk",
    "app",
    "com",
    "demo",
    "example",
    "file",
    "java",
    "org",
    "path",
    "sample",
    "shell",
    "source",
    "sources",
    "tmp",
    "www",
}

PERMISSION_HINTS: dict[str, tuple[str, ...]] = {
    "read_sms": ("sms", "otp", "message", "body"),
    "receive_sms": ("sms", "otp", "message", "body"),
    "record_audio": ("audio", "record", "mic", "voice"),
    "camera": ("camera", "image", "photo", "capture"),
    "access_fine_location": ("location", "gps", "lat", "lng", "coordinate"),
    "access_coarse_location": ("location", "gps", "lat", "lng", "coordinate"),
    "read_contacts": ("contact", "addressbook", "phone"),
}

TAG_HINTS: dict[str, tuple[str, ...]] = {
    "webview": ("webview", "jsbridge", "javascript", "loadurl", "bridge"),
    "hybrid": ("webview", "bridge", "javascript"),
    "network": ("api", "url", "request", "upload", "telemetry", "callback", "http", "https", "net"),
    "callback": ("api", "url", "request", "upload", "telemetry", "callback", "http", "https", "net"),
}

CRYPTO_HINTS = ("encrypt", "decrypt", "cipher", "crypto", "digest", "hash", "hmac", "aes", "rsa", "mac", "key")
CALLBACK_HINTS = ("api", "url", "request", "upload", "telemetry", "callback", "http", "https", "net", "backup")


def _normalize_text(text: str) -> str:
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return camel_spaced.replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ").replace("$", " ")


def _tokenize(text: str) -> tuple[str, ...]:
    normalized = _normalize_text(text)
    tokens = tuple(
        token.lower()
        for token in TOKEN_RE.findall(normalized)
        if token and token.lower() not in STOPWORDS
    )
    return tokens


def _unique_terms(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _method_blob(entry: MethodIndexEntry) -> tuple[str, ...]:
    values: list[str] = []
    for item in (
        entry.class_name,
        entry.method_name,
        entry.return_type,
        entry.source_path,
        *entry.parameter_types,
        *entry.tags,
        *entry.evidence,
    ):
        values.extend(_tokenize(item))
    return _unique_terms(tuple(values))


@dataclass(frozen=True, slots=True)
class _SignalGroup:
    label: str
    terms: tuple[str, ...]
    weight: int
    source_signal: str


class OfflineHookAdvisor:
    def __init__(self, rule_engine: OfflineRuleEngine | None = None) -> None:
        self._rule_engine = rule_engine or OfflineRuleEngine()

    def recommend(self, static_inputs: StaticInputs, method_index: MethodIndex, limit: int = 8) -> tuple[HookRecommendation, ...]:
        signal_groups = self._build_signal_groups(static_inputs)
        recommendations = list(self._rule_engine.recommend(static_inputs))

        for method in method_index.methods:
            recommendation = self._score_method(method, signal_groups)
            if recommendation is None:
                continue
            recommendations.append(recommendation)

        recommendations.sort(
            key=lambda item: (
                -item.score,
                item.method.method_name if item.method is not None else item.title,
                item.method.class_name if item.method is not None else "",
                len(item.matched_terms),
            )
        )
        return tuple(recommendations[:limit])

    def _build_signal_groups(self, static_inputs: StaticInputs) -> tuple[_SignalGroup, ...]:
        groups: list[_SignalGroup] = []

        callback_terms = self._terms_from_values(static_inputs.callback_endpoints + static_inputs.callback_clues) + CALLBACK_HINTS
        callback_terms = _unique_terms(callback_terms)
        if callback_terms:
            groups.append(_SignalGroup("Callback / network clues", callback_terms, 4, "callback_endpoints"))

        crypto_terms = self._terms_from_values(static_inputs.crypto_signals) + CRYPTO_HINTS
        crypto_terms = _unique_terms(crypto_terms)
        if crypto_terms:
            groups.append(_SignalGroup("Crypto signals", crypto_terms, 5, "crypto_signals"))

        permission_terms: list[str] = []
        for permission in static_inputs.dangerous_permissions:
            permission_name = permission.rsplit(".", 1)[-1].lower()
            permission_terms.extend(_tokenize(permission_name))
            for key, hints in PERMISSION_HINTS.items():
                if key in permission_name:
                    permission_terms.extend(hints)
        permission_terms = list(_unique_terms(tuple(permission_terms)))
        if permission_terms:
            groups.append(_SignalGroup("Sensitive permission signals", tuple(permission_terms), 4, "dangerous_permissions"))

        tag_terms: list[str] = []
        for tag in static_inputs.technical_tags:
            lower_tag = tag.lower()
            tag_terms.extend(_tokenize(lower_tag))
            for key, hints in TAG_HINTS.items():
                if key in lower_tag:
                    tag_terms.extend(hints)
        tag_terms = list(_unique_terms(tuple(tag_terms)))
        if tag_terms:
            groups.append(_SignalGroup("Technical profile hints", tuple(tag_terms), 2, "technical_tags"))

        return tuple(groups)

    @staticmethod
    def _terms_from_values(values: tuple[str, ...]) -> tuple[str, ...]:
        terms: list[str] = []
        for value in values:
            terms.extend(_tokenize(value))
        return _unique_terms(tuple(terms))

    def _score_method(self, method: MethodIndexEntry, signal_groups: tuple[_SignalGroup, ...]) -> HookRecommendation | None:
        blob_terms = set(_method_blob(method))
        if not blob_terms:
            return None

        score = 0
        matched_terms: list[str] = []
        source_signals: list[str] = []
        reason_parts: list[str] = []

        for group in signal_groups:
            matches = tuple(term for term in group.terms if term in blob_terms)
            if not matches:
                continue
            score += group.weight + min(len(matches), 3) - 1
            matched_terms.extend(matches[:3])
            source_signals.append(group.source_signal)
            reason_parts.append(f"{group.label}: {', '.join(matches[:3])}")

        if score <= 0:
            return None

        signature = ",".join(method.parameter_types)
        return HookRecommendation(
            recommendation_id=f"recommendation:{method.class_name}:{method.method_name}:{signature}:{method.source_path}",
            kind="method_hook",
            title=f"{method.class_name}.{method.method_name}",
            reason="; ".join(reason_parts),
            score=score,
            matched_terms=_unique_terms(tuple(matched_terms)),
            source_signals=_unique_terms(tuple(source_signals)),
            method=method,
        )
