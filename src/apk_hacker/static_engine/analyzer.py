from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


LEGACY_DIR = Path(__file__).resolve().parent / "legacy"
LEGACY_SCRIPT = LEGACY_DIR / "scripts" / "investigate_android_app.py"


@dataclass(frozen=True, slots=True)
class StaticArtifacts:
    output_root: Path
    report_dir: Path
    cache_dir: Path
    analysis_json: Path
    callback_config_json: Path
    noise_log_json: Path
    jadx_sources_dir: Path | None
    jadx_project_dir: Path | None


def build_output_layout(target_path: Path, output_dir: Path | None) -> dict[str, Path]:
    resolved_target = target_path.resolve()
    base_name = resolved_target.stem if resolved_target.is_file() else resolved_target.name
    root = output_dir.expanduser().resolve() if output_dir is not None else resolved_target.parent
    return {
        "root": root,
        "report_dir": root / "报告" / base_name,
        "cache_dir": root / "cache" / base_name,
    }


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"none", "null"}:
            return None
        return Path(stripped)
    return Path(value)


def _parse_artifacts(payload: dict, layout: dict[str, Path]) -> StaticArtifacts:
    artifacts = payload.get("artifacts", {})
    output_root = Path(payload["output_root"])
    report_dir = Path(payload["report_dir"])
    cache_dir = Path(payload["cache_dir"])

    return StaticArtifacts(
        output_root=output_root,
        report_dir=report_dir,
        cache_dir=cache_dir,
        analysis_json=Path(artifacts["analysis_json"]),
        callback_config_json=Path(artifacts["callback_config_json"]),
        noise_log_json=Path(artifacts["noise_log_json"]),
        jadx_sources_dir=_optional_path(artifacts.get("jadx_sources_dir")),
        jadx_project_dir=_optional_path(artifacts.get("jadx_project_dir")),
    )


class StaticAnalyzer:
    legacy_module_name = "investigate_android_app"

    def resolve_output_root(self, target_path: Path, output_dir: Path | None) -> Path:
        return build_output_layout(target_path, output_dir)["root"]

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        layout = build_output_layout(target_path, output_dir)
        command = [sys.executable, str(LEGACY_SCRIPT), str(target_path.resolve()), "--mode", mode]
        if output_dir is not None:
            command.extend(["--output-dir", str(output_dir)])

        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(
                f"Legacy static engine failed with exit code {completed.returncode}: {stderr}"
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("Legacy static engine did not emit valid JSON stdout.") from exc

        return _parse_artifacts(payload, layout)

    def __call__(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        return self.analyze(target_path, output_dir=output_dir, mode=mode)
