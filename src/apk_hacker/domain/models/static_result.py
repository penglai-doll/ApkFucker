from __future__ import annotations

from dataclasses import dataclass

from apk_hacker.domain.models.evidence import Evidence
from apk_hacker.domain.models.finding import Finding


@dataclass(frozen=True, slots=True)
class StaticResult:
    package_name: str
    technical_tags: tuple[str, ...]
    dangerous_permissions: tuple[str, ...]
    callback_endpoints: tuple[str, ...]
    callback_clues: tuple[str, ...]
    crypto_signals: tuple[str, ...]
    packer_hints: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[Finding, ...]
    evidence: tuple[Evidence, ...]
