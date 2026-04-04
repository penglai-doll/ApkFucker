from pathlib import Path
from unittest.mock import Mock, patch
import json

from apk_hacker.static_engine.analyzer import StaticAnalyzer
from apk_hacker.static_engine.tooling.jadx_exporter import build_jadx_command


def test_build_jadx_command_uses_split_source_and_resource_dirs(tmp_path: Path) -> None:
    jadx_binary = tmp_path / "bin" / "jadx"
    apk_path = tmp_path / "sample.apk"
    out_dir = tmp_path / "export"

    command = build_jadx_command(jadx_binary, apk_path, out_dir)

    assert command == [
        jadx_binary,
        "--output-dir-src",
        out_dir / "sources",
        "--output-dir-res",
        out_dir / "resources",
        apk_path,
    ]


def test_static_analyzer_carries_optional_jadx_project_dir(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    jadx_project_dir = output_root / "jadx"

    payload = {
        "output_root": str(output_root.resolve()),
        "report_dir": str((output_root / "报告" / "sample").resolve()),
        "cache_dir": str((output_root / "cache" / "sample").resolve()),
        "artifacts": {
            "analysis_json": str((output_root / "cache" / "sample" / "analysis.json").resolve()),
            "callback_config_json": str((output_root / "cache" / "sample" / "callback-config.json").resolve()),
            "noise_log_json": str((output_root / "cache" / "sample" / "noise-log.json").resolve()),
            "jadx_sources_dir": str((jadx_project_dir / "sources").resolve()),
            "jadx_project_dir": str(jadx_project_dir.resolve()),
        },
    }
    completed = Mock(returncode=0, stdout=json.dumps(payload), stderr="")

    with patch("apk_hacker.static_engine.analyzer.subprocess.run", return_value=completed):
        artifacts = analyzer.analyze(target, output_dir=output_root)

    assert artifacts.jadx_sources_dir == (jadx_project_dir / "sources").resolve()
    assert artifacts.jadx_project_dir == jadx_project_dir.resolve()
