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

    def __post_init__(self) -> None:
        object.__setattr__(self, "technical_tags", tuple(str(value) for value in self.technical_tags))
        object.__setattr__(self, "dangerous_permissions", tuple(str(value) for value in self.dangerous_permissions))
        object.__setattr__(self, "callback_endpoints", tuple(str(value) for value in self.callback_endpoints))
        object.__setattr__(self, "callback_clues", tuple(str(value) for value in self.callback_clues))
        object.__setattr__(self, "crypto_signals", tuple(str(value) for value in self.crypto_signals))
        object.__setattr__(self, "packer_hints", tuple(str(value) for value in self.packer_hints))
        object.__setattr__(self, "limitations", tuple(str(value) for value in self.limitations))
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "evidence", tuple(self.evidence))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "static-result.v1",
            "package_name": self.package_name,
            "technical_tags": list(self.technical_tags),
            "dangerous_permissions": list(self.dangerous_permissions),
            "callback_endpoints": list(self.callback_endpoints),
            "callback_clues": list(self.callback_clues),
            "crypto_signals": list(self.crypto_signals),
            "packer_hints": list(self.packer_hints),
            "limitations": list(self.limitations),
            "findings": [finding.to_payload() for finding in self.findings],
            "evidence": [evidence.to_payload() for evidence in self.evidence],
        }

    @classmethod
    def from_payload(cls, payload: object) -> "StaticResult | None":
        if not isinstance(payload, dict):
            return None
        package_name = payload.get("package_name")
        if not isinstance(package_name, str):
            return None
        findings_payload = payload.get("findings", [])
        evidence_payload = payload.get("evidence", [])
        if not isinstance(findings_payload, list):
            findings_payload = []
        if not isinstance(evidence_payload, list):
            evidence_payload = []
        return cls(
            package_name=package_name,
            technical_tags=_tuple_of_text(payload.get("technical_tags", [])),
            dangerous_permissions=_tuple_of_text(payload.get("dangerous_permissions", [])),
            callback_endpoints=_tuple_of_text(payload.get("callback_endpoints", [])),
            callback_clues=_tuple_of_text(payload.get("callback_clues", [])),
            crypto_signals=_tuple_of_text(payload.get("crypto_signals", [])),
            packer_hints=_tuple_of_text(payload.get("packer_hints", [])),
            limitations=_tuple_of_text(payload.get("limitations", [])),
            findings=tuple(
                finding
                for finding in (Finding.from_payload(item) for item in findings_payload)
                if finding is not None
            ),
            evidence=tuple(
                item
                for item in (Evidence.from_payload(entry) for entry in evidence_payload)
                if item is not None
            ),
        )


def _tuple_of_text(payload: object) -> tuple[str, ...]:
    if not isinstance(payload, (list, tuple)):
        return ()
    return tuple(str(value) for value in payload)
