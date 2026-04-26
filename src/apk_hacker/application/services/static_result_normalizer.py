from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping

from apk_hacker.domain.models.artifact import ArtifactManifest, ArtifactRef
from apk_hacker.domain.models.evidence import Evidence
from apk_hacker.domain.models.finding import Finding
from apk_hacker.domain.models.indexes import MethodIndex
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.static_result import StaticResult
from apk_hacker.static_engine.analyzer import StaticArtifacts


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_id(kind: str) -> str:
    return kind.replace("/", "-").replace(".", "-").replace("_", "-")


def _json_default(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False, default=_json_default) for row in rows)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")
    return path


@dataclass(frozen=True, slots=True)
class NormalizedStaticArtifacts:
    manifest: ArtifactManifest
    static_result: StaticResult
    manifest_path: Path
    static_result_path: Path
    findings_path: Path
    evidence_path: Path
    method_index_path: Path
    class_index_path: Path


class StaticResultNormalizer:
    def normalize(
        self,
        *,
        sample_path: Path,
        artifacts: StaticArtifacts,
        analysis_report: Mapping[str, object],
        callback_config: Mapping[str, object],
        static_inputs: StaticInputs,
        method_index: MethodIndex,
    ) -> NormalizedStaticArtifacts:
        normalized_root = artifacts.output_root / "normalized"
        created_at = _now_iso()
        evidence, findings = self._build_findings_and_evidence(
            static_inputs=static_inputs,
            analysis_report=analysis_report,
            callback_config=callback_config,
        )
        static_result = StaticResult(
            package_name=static_inputs.package_name,
            technical_tags=static_inputs.technical_tags,
            dangerous_permissions=static_inputs.dangerous_permissions,
            callback_endpoints=static_inputs.callback_endpoints,
            callback_clues=static_inputs.callback_clues,
            crypto_signals=static_inputs.crypto_signals,
            packer_hints=static_inputs.packer_hints,
            limitations=static_inputs.limitations,
            findings=tuple(findings),
            evidence=tuple(evidence),
        )

        manifest_path = normalized_root / "artifact-manifest.json"
        static_result_path = normalized_root / "static-result.v1.json"
        findings_path = normalized_root / "findings.jsonl"
        evidence_path = normalized_root / "evidence.jsonl"
        method_index_path = normalized_root / "method-index.jsonl"
        class_index_path = normalized_root / "class-index.jsonl"

        method_rows = [item.to_payload() for item in method_index.methods]
        class_rows = [item.to_payload() for item in method_index.classes]

        manifest = ArtifactManifest(
            schema_version="artifact-manifest.v1",
            case_id=self._infer_case_id(sample_path, artifacts.output_root),
            sample_path=str(sample_path.resolve()),
            artifacts=tuple(
                self._build_manifest_entries(
                    created_at=created_at,
                    artifacts=artifacts,
                    manifest_path=manifest_path,
                    static_result_path=static_result_path,
                    findings_path=findings_path,
                    evidence_path=evidence_path,
                    method_index_path=method_index_path,
                    class_index_path=class_index_path,
                    method_count=len(method_rows),
                    class_count=len(class_rows),
                    finding_count=len(findings),
                    evidence_count=len(evidence),
                )
            ),
        )

        _write_json(static_result_path, static_result.to_payload())
        _write_jsonl(findings_path, [item.to_payload() for item in findings])
        _write_jsonl(evidence_path, [item.to_payload() for item in evidence])
        _write_jsonl(method_index_path, method_rows)
        _write_jsonl(class_index_path, class_rows)
        _write_json(manifest_path, manifest.to_payload())

        return NormalizedStaticArtifacts(
            manifest=manifest,
            static_result=static_result,
            manifest_path=manifest_path.resolve(),
            static_result_path=static_result_path.resolve(),
            findings_path=findings_path.resolve(),
            evidence_path=evidence_path.resolve(),
            method_index_path=method_index_path.resolve(),
            class_index_path=class_index_path.resolve(),
        )

    @staticmethod
    def _infer_case_id(sample_path: Path, output_root: Path) -> str:
        if output_root.name == "static" and output_root.parent.name:
            return output_root.parent.name
        return sample_path.stem

    def _build_findings_and_evidence(
        self,
        *,
        static_inputs: StaticInputs,
        analysis_report: Mapping[str, object],
        callback_config: Mapping[str, object],
    ) -> tuple[list[Evidence], list[Finding]]:
        evidences: list[Evidence] = []
        findings: list[Finding] = []

        def add_evidence(*, source_type: str, excerpt: str, tags: tuple[str, ...], path: str | None) -> Evidence:
            evidence = Evidence(
                evidence_id=f"evidence-{len(evidences) + 1}",
                source_type=source_type,
                path=path,
                line=None,
                excerpt=excerpt,
                tags=tags,
                metadata={},
            )
            evidences.append(evidence)
            return evidence

        def add_finding(
            *,
            category: str,
            severity: str,
            title: str,
            summary: str,
            evidence_ids: tuple[str, ...],
            tags: tuple[str, ...],
            confidence: float = 0.75,
        ) -> None:
            findings.append(
                Finding(
                    finding_id=f"finding-{len(findings) + 1}",
                    category=category,
                    severity=severity,
                    title=title,
                    summary=summary,
                    confidence=confidence,
                    evidence_ids=evidence_ids,
                    tags=tags,
                )
            )

        analysis_path = (
            str(static_inputs.artifact_paths.analysis_report)
            if static_inputs.artifact_paths.analysis_report is not None
            else None
        )
        callback_path = (
            str(static_inputs.artifact_paths.callback_config)
            if static_inputs.artifact_paths.callback_config is not None
            else None
        )

        for permission in static_inputs.dangerous_permissions:
            evidence = add_evidence(
                source_type="manifest",
                excerpt=permission,
                tags=("permission", "dangerous"),
                path=analysis_path,
            )
            add_finding(
                category="permission",
                severity="medium",
                title=f"Dangerous permission: {permission}",
                summary="Legacy static analysis marked this Android permission as high-risk.",
                evidence_ids=(evidence.evidence_id,),
                tags=("permission",),
                confidence=0.9,
            )

        network_evidence_ids: list[str] = []
        for endpoint in static_inputs.callback_endpoints:
            evidence = add_evidence(
                source_type="resource",
                excerpt=endpoint,
                tags=("network", "callback"),
                path=callback_path,
            )
            network_evidence_ids.append(evidence.evidence_id)
        for clue in static_inputs.callback_clues:
            evidence = add_evidence(
                source_type="source",
                excerpt=clue,
                tags=("network", "callback_clue"),
                path=callback_path,
            )
            network_evidence_ids.append(evidence.evidence_id)
        if network_evidence_ids:
            add_finding(
                category="network",
                severity="medium",
                title="Callback infrastructure clues detected",
                summary="Static callback analysis produced endpoints or source-level clues worth correlating during runtime capture.",
                evidence_ids=tuple(network_evidence_ids),
                tags=("network", "callback"),
                confidence=0.85,
            )

        crypto_evidence_ids: list[str] = []
        for signal in static_inputs.crypto_signals:
            evidence = add_evidence(
                source_type="source",
                excerpt=signal,
                tags=("crypto",),
                path=analysis_path,
            )
            crypto_evidence_ids.append(evidence.evidence_id)
        if crypto_evidence_ids:
            add_finding(
                category="crypto",
                severity="medium",
                title="Cryptographic activity signals detected",
                summary="Static analysis identified crypto-related APIs or algorithm markers that should be instrumented dynamically.",
                evidence_ids=tuple(crypto_evidence_ids),
                tags=("crypto",),
                confidence=0.8,
            )

        packer_evidence_ids: list[str] = []
        for packer in static_inputs.packer_hints:
            evidence = add_evidence(
                source_type="runtime",
                excerpt=packer,
                tags=("packer",),
                path=analysis_path,
            )
            packer_evidence_ids.append(evidence.evidence_id)
        if packer_evidence_ids:
            add_finding(
                category="packer",
                severity="high",
                title="Packer or shell hints detected",
                summary="The sample appears to use a packer or anti-analysis shell and may require runtime unpacking or bypasses.",
                evidence_ids=tuple(packer_evidence_ids),
                tags=("packer", "anti-analysis"),
                confidence=0.9,
            )

        framework_tags = tuple(static_inputs.technical_tags)
        if framework_tags:
            evidence = add_evidence(
                source_type="resource",
                excerpt=", ".join(framework_tags),
                tags=("framework",),
                path=analysis_path,
            )
            add_finding(
                category="framework",
                severity="info",
                title="Technical profile detected",
                summary="Normalized static result preserved the legacy technical profile for downstream hook/template selection.",
                evidence_ids=(evidence.evidence_id,),
                tags=framework_tags,
                confidence=0.7,
            )

        if analysis_report.get("limitations") or callback_config.get("limitations"):
            limitations_text = ", ".join(static_inputs.limitations)
            if limitations_text:
                add_evidence(
                    source_type="runtime",
                    excerpt=limitations_text,
                    tags=("limitation",),
                    path=analysis_path,
                )

        return evidences, findings

    def _build_manifest_entries(
        self,
        *,
        created_at: str,
        artifacts: StaticArtifacts,
        manifest_path: Path,
        static_result_path: Path,
        findings_path: Path,
        evidence_path: Path,
        method_index_path: Path,
        class_index_path: Path,
        method_count: int,
        class_count: int,
        finding_count: int,
        evidence_count: int,
    ) -> list[ArtifactRef]:
        manifest_entries: list[ArtifactRef] = []

        def add(
            kind: str,
            path: Path | None,
            producer: str,
            metadata: dict[str, object] | None = None,
            *,
            require_exists: bool = True,
        ) -> None:
            if path is None or (require_exists and not path.exists()):
                return
            manifest_entries.append(
                ArtifactRef(
                    artifact_id=_artifact_id(kind),
                    kind=kind,
                    path=str(path.resolve()),
                    producer=producer,
                    created_at=created_at,
                    metadata=metadata or {},
                )
            )

        add("legacy.analysis_json", artifacts.analysis_json, "legacy_static_engine")
        add("legacy.callback_config_json", artifacts.callback_config_json, "legacy_static_engine")
        add("legacy.noise_log_json", artifacts.noise_log_json, "legacy_static_engine")
        add("legacy.jadx_sources", artifacts.jadx_sources_dir, "legacy_static_engine")
        add("legacy.jadx_project", artifacts.jadx_project_dir, "legacy_static_engine")
        add("legacy.report_markdown", artifacts.report_dir / "report.md", "legacy_static_engine")
        add("legacy.report_docx", artifacts.report_dir / "report.docx", "legacy_static_engine")
        add("normalized.artifact_manifest", manifest_path, "static_result_normalizer", require_exists=False)
        add(
            "normalized.static_result",
            static_result_path,
            "static_result_normalizer",
            {"schema": "static-result.v1"},
            require_exists=False,
        )
        add("normalized.findings", findings_path, "static_result_normalizer", {"count": finding_count}, require_exists=False)
        add("normalized.evidence", evidence_path, "static_result_normalizer", {"count": evidence_count}, require_exists=False)
        add("normalized.method_index", method_index_path, "static_result_normalizer", {"count": method_count}, require_exists=False)
        add("normalized.class_index", class_index_path, "static_result_normalizer", {"count": class_count}, require_exists=False)
        return manifest_entries
