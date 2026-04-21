import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from apk_hacker.static_engine.analyzer import StaticAnalyzer, StaticArtifacts, build_output_layout


def test_static_analyzer_exposes_legacy_entrypoint(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    assert analyzer.legacy_module_name == "investigate_android_app"
    assert analyzer.resolve_output_root(tmp_path / "sample.apk", None) == tmp_path


def test_build_output_layout_matches_legacy_semantics(tmp_path: Path) -> None:
    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"

    default_layout = build_output_layout(target, None)
    custom_layout = build_output_layout(target, output_root)

    assert default_layout["root"] == tmp_path.resolve()
    assert default_layout["report_dir"] == (tmp_path / "报告" / "sample").resolve()
    assert default_layout["cache_dir"] == (tmp_path / "cache" / "sample").resolve()
    assert custom_layout["root"] == output_root.resolve()
    assert custom_layout["report_dir"] == (output_root / "报告" / "sample").resolve()
    assert custom_layout["cache_dir"] == (output_root / "cache" / "sample").resolve()


def test_build_output_layout_expands_tilde_roots(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")
    output_root = Path("~/artifacts")

    layout = build_output_layout(target, output_root)

    assert layout["root"] == (home_dir / "artifacts").resolve()
    assert layout["report_dir"] == (home_dir / "artifacts" / "报告" / "sample").resolve()
    assert layout["cache_dir"] == (home_dir / "artifacts" / "cache" / "sample").resolve()


def test_static_analyzer_returns_static_artifacts_from_legacy_stdout(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"

    payload = {
        "output_root": str(output_root.resolve()),
        "report_dir": str((output_root / "报告" / "sample").resolve()),
        "cache_dir": str((output_root / "cache" / "sample").resolve()),
        "artifacts": {
            "analysis_json": str((output_root / "cache" / "sample" / "analysis.json").resolve()),
            "callback_config_json": str((output_root / "cache" / "sample" / "callback-config.json").resolve()),
            "noise_log_json": str((output_root / "cache" / "sample" / "noise-log.json").resolve()),
        },
    }
    completed = Mock(returncode=0, stdout=json.dumps(payload), stderr="")

    with patch("apk_hacker.static_engine.analyzer.shutil.which", return_value=None), patch(
        "apk_hacker.static_engine.analyzer.subprocess.run",
        return_value=completed,
    ) as run_mock:
        artifacts = analyzer.analyze(target, output_dir=output_root)

    assert isinstance(artifacts, StaticArtifacts)
    assert artifacts.output_root == output_root.resolve()
    assert artifacts.report_dir == (output_root / "报告" / "sample").resolve()
    assert artifacts.cache_dir == (output_root / "cache" / "sample").resolve()
    assert artifacts.analysis_json == (output_root / "cache" / "sample" / "analysis.json").resolve()
    assert artifacts.callback_config_json == (output_root / "cache" / "sample" / "callback-config.json").resolve()
    assert artifacts.noise_log_json == (output_root / "cache" / "sample" / "noise-log.json").resolve()
    assert artifacts.jadx_sources_dir is None

    run_mock.assert_called_once()
    command = run_mock.call_args.args[0]
    assert command[0] == sys.executable
    assert Path(command[1]).name == "investigate_android_app.py"
    assert command[2] == str(target.resolve())
    assert command[3:] == ["--mode", "auto", "--output-dir", str(output_root)]


def test_static_analyzer_treats_missing_or_blank_jadx_sources_as_absent(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    output_root = tmp_path / "artifacts"
    layout = {
        "root": output_root.resolve(),
        "report_dir": (output_root / "报告" / "sample").resolve(),
        "cache_dir": (output_root / "cache" / "sample").resolve(),
    }

    missing_payload = {
        "output_root": str(layout["root"]),
        "report_dir": str(layout["report_dir"]),
        "cache_dir": str(layout["cache_dir"]),
        "artifacts": {
            "analysis_json": str((layout["cache_dir"] / "analysis.json").resolve()),
            "callback_config_json": str((layout["cache_dir"] / "callback-config.json").resolve()),
            "noise_log_json": str((layout["cache_dir"] / "noise-log.json").resolve()),
        },
    }
    blank_payload = {
        "output_root": str(layout["root"]),
        "report_dir": str(layout["report_dir"]),
        "cache_dir": str(layout["cache_dir"]),
        "artifacts": {
            "analysis_json": str((layout["cache_dir"] / "analysis.json").resolve()),
            "callback_config_json": str((layout["cache_dir"] / "callback-config.json").resolve()),
            "noise_log_json": str((layout["cache_dir"] / "noise-log.json").resolve()),
            "jadx_sources_dir": "",
        },
    }

    missing_completed = Mock(returncode=0, stdout=json.dumps(missing_payload), stderr="")
    blank_completed = Mock(returncode=0, stdout=json.dumps(blank_payload), stderr="")

    with patch("apk_hacker.static_engine.analyzer.subprocess.run", return_value=missing_completed):
        missing_artifacts = analyzer.analyze(tmp_path / "sample.apk")
    with patch("apk_hacker.static_engine.analyzer.subprocess.run", return_value=blank_completed):
        blank_artifacts = analyzer.analyze(tmp_path / "sample.apk")

    assert missing_artifacts.jadx_sources_dir is None
    assert blank_artifacts.jadx_sources_dir is None


def test_static_analyzer_exports_jadx_sources_when_legacy_stdout_does_not_include_them(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    jadx_root = output_root / "jadx"
    payload = {
        "output_root": str(output_root.resolve()),
        "report_dir": str((output_root / "报告" / "sample").resolve()),
        "cache_dir": str((output_root / "cache" / "sample").resolve()),
        "artifacts": {
            "analysis_json": str((output_root / "cache" / "sample" / "analysis.json").resolve()),
            "callback_config_json": str((output_root / "cache" / "sample" / "callback-config.json").resolve()),
            "noise_log_json": str((output_root / "cache" / "sample" / "noise-log.json").resolve()),
        },
    }

    legacy_completed = Mock(returncode=0, stdout=json.dumps(payload), stderr="")

    def run_side_effect(command: list[object], capture_output: bool, text: bool, check: bool):  # type: ignore[override]
        if Path(command[1]).name == "investigate_android_app.py":
            return legacy_completed
        (jadx_root / "sources").mkdir(parents=True, exist_ok=True)
        (jadx_root / "resources").mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with patch("apk_hacker.static_engine.analyzer.shutil.which", return_value="/usr/local/bin/jadx"), patch(
        "apk_hacker.static_engine.analyzer.subprocess.run",
        side_effect=run_side_effect,
    ) as run_mock:
        artifacts = analyzer.analyze(target, output_dir=output_root)

    assert artifacts.jadx_sources_dir == (jadx_root / "sources").resolve()
    assert artifacts.jadx_project_dir == jadx_root.resolve()
    assert run_mock.call_count == 2


def test_static_analyzer_raises_for_nonzero_exit(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")

    completed = Mock(returncode=3, stdout="", stderr="boom")

    with patch("apk_hacker.static_engine.analyzer.subprocess.run", return_value=completed):
        try:
            analyzer.analyze(target)
        except RuntimeError as exc:
            assert "exit code 3" in str(exc)
            assert "boom" in str(exc)
        else:
            raise AssertionError("Expected RuntimeError for non-zero exit")


def test_static_analyzer_raises_for_malformed_json_stdout(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    target = tmp_path / "sample.apk"
    target.write_bytes(b"apk")

    completed = Mock(returncode=0, stdout="not-json", stderr="")

    with patch("apk_hacker.static_engine.analyzer.subprocess.run", return_value=completed):
        try:
            analyzer.analyze(target)
        except ValueError as exc:
            assert "valid JSON stdout" in str(exc)
        else:
            raise AssertionError("Expected ValueError for malformed JSON stdout")
