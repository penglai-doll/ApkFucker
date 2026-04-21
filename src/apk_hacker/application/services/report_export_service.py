from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.domain.models.traffic import TrafficCapture


def _joined(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _read_optional_text(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


@dataclass(frozen=True, slots=True)
class ExportableReport:
    job_id: str | None
    summary_text: str
    sample_path: Path | None
    static_inputs: StaticInputs | None
    hook_plan: HookPlan
    hook_events: tuple[HookEvent, ...]
    traffic_capture: TrafficCapture | None
    last_execution_db_path: Path | None = None
    last_execution_bundle_path: Path | None = None
    last_execution_status: str | None = None
    last_execution_mode: str | None = None
    last_executed_backend_key: str | None = None
    last_execution_error_code: str | None = None
    last_execution_error_message: str | None = None


class ReportExportService:
    def build_workspace_summary(
        self,
        *,
        workspace_title: str,
        sample_path: Path,
        method_count: int,
        script_count: int,
        case_count: int,
    ) -> str:
        sample_name = sample_path.name or str(sample_path)
        title = workspace_title.strip() or sample_name
        return (
            f"已初始化工作区 {title}，样本 {sample_name}，"
            f"静态方法 {method_count} 个，自定义脚本 {script_count} 个，"
            f"案件队列 {case_count} 项。"
        )

    def build_markdown(self, report: ExportableReport) -> str:
        static_inputs = report.static_inputs
        lines = [
            "# APKHacker Report",
            "",
            f"- Generated At: {datetime.now(timezone.utc).isoformat()}",
            f"- Job ID: {report.job_id or '-'}",
            f"- Sample: {report.sample_path or '-'}",
            f"- Package: {static_inputs.package_name if static_inputs is not None else '-'}",
            "",
            "## Summary",
            "",
            report.summary_text or "-",
            "",
        ]

        if static_inputs is not None:
            static_markdown = _read_optional_text(static_inputs.artifact_paths.static_markdown_report)
            lines.extend(
                [
                    "## Static Summary",
                    "",
                    f"- Technical Tags: {_joined(static_inputs.technical_tags)}",
                    f"- Dangerous Permissions: {_joined(static_inputs.dangerous_permissions)}",
                    f"- Callback Endpoints: {_joined(static_inputs.callback_endpoints)}",
                    f"- Callback Clues: {_joined(static_inputs.callback_clues)}",
                    f"- Crypto Signals: {_joined(static_inputs.crypto_signals)}",
                    f"- Packer Hints: {_joined(static_inputs.packer_hints)}",
                    f"- Limitations: {_joined(static_inputs.limitations)}",
                    "",
                ]
            )
            if static_markdown is not None:
                lines.extend(
                    [
                        "## Static Report Body",
                        "",
                        static_markdown,
                        "",
                    ]
                )

        lines.extend(["## Hook Plan", ""])
        if not report.hook_plan.items:
            lines.extend(["- No hook plan items selected.", ""])
        else:
            for item in report.hook_plan.items:
                if item.target is not None:
                    signature = ", ".join(item.target.parameter_types)
                    lines.append(
                        f"- [{item.kind}] {item.target.class_name}.{item.target.method_name}({signature})"
                    )
                    continue
                template_name = str(item.render_context.get("template_name", "")).strip()
                script_name = str(item.render_context.get("script_name", "")).strip()
                label = template_name or script_name or item.kind
                lines.append(f"- [{item.kind}] {label}")
            lines.append("")

        lines.extend(
            [
                "## Dynamic Execution",
                "",
                f"- Last Status: {report.last_execution_status or '-'}",
                f"- Requested Mode: {report.last_execution_mode or '-'}",
                f"- Executed Backend: {report.last_executed_backend_key or '-'}",
                f"- Event Count: {len(report.hook_events)}",
                f"- Last Run DB: {report.last_execution_db_path or '-'}",
                f"- Execution Bundle: {report.last_execution_bundle_path or '-'}",
                f"- Failure Code: {report.last_execution_error_code or '-'}",
                f"- Failure Message: {report.last_execution_error_message or '-'}",
                "",
            ]
        )
        if report.hook_events:
            for event in report.hook_events:
                target = f"{event.class_name}.{event.method_name}"
                arguments = ", ".join(event.arguments) if event.arguments else "-"
                lines.extend(
                    [
                        f"### {event.event_type}: {target}",
                        "",
                        f"- Source: {event.source}",
                        f"- Arguments: {arguments}",
                        f"- Return: {event.return_value or '-'}",
                        f"- Stacktrace: {event.stacktrace or '-'}",
                        "",
                    ]
                )

        lines.extend(["## Traffic Capture", ""])
        if report.traffic_capture is None:
            lines.extend(["- No HAR capture loaded.", ""])
        else:
            traffic_summary = report.traffic_capture.summary
            lines.extend(
                [
                    f"- Source: {report.traffic_capture.source_path}",
                    f"- Provenance: {report.traffic_capture.provenance.label}",
                    f"- Flow Count: {report.traffic_capture.flow_count}",
                    f"- Suspicious Count: {report.traffic_capture.suspicious_count}",
                    f"- HTTPS Flow Count: {traffic_summary.https_flow_count}",
                    f"- Matched Indicator Count: {traffic_summary.matched_indicator_count}",
                    "",
                ]
            )
            if traffic_summary.top_hosts:
                lines.extend(["### Top Hosts", ""])
                for host in traffic_summary.top_hosts:
                    lines.append(
                        f"- {host.host}: {host.flow_count} flows, {host.suspicious_count} suspicious, {host.https_flow_count} HTTPS"
                    )
                lines.append("")
            if traffic_summary.suspicious_hosts:
                lines.extend(["### Suspicious Hosts", ""])
                for host in traffic_summary.suspicious_hosts:
                    lines.append(
                        f"- {host.host}: {host.flow_count} flows, {host.suspicious_count} suspicious, {host.https_flow_count} HTTPS"
                    )
                lines.append("")

        if static_inputs is not None:
            lines.extend(["## Artifacts", ""])
            artifact_paths = static_inputs.artifact_paths
            lines.extend(
                [
                    f"- Analysis Report: {artifact_paths.analysis_report or '-'}",
                    f"- Callback Config: {artifact_paths.callback_config or '-'}",
                    f"- Noise Log: {artifact_paths.noise_log or '-'}",
                    f"- JADX Sources: {artifact_paths.jadx_sources or '-'}",
                    f"- JADX Project: {artifact_paths.jadx_project or '-'}",
                    f"- Static Markdown Report: {artifact_paths.static_markdown_report or '-'}",
                    f"- Static DOCX Report: {artifact_paths.static_docx_report or '-'}",
                    "",
                ]
            )

        return "\n".join(lines).rstrip() + "\n"

    def export_markdown(self, report: ExportableReport, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.build_markdown(report), encoding="utf-8")
        return output_path
