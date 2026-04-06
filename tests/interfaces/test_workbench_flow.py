from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication

from apk_hacker.domain.models.execution import ExecutionRequest
from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.domain.models.hook_plan import HookPlan
from apk_hacker.application.services.job_service import JobService
from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow
from apk_hacker.interfaces.gui_pyqt.viewmodels import WorkbenchController
from apk_hacker.infrastructure.execution.backend import ExecutionBackend
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from apk_hacker.static_engine.analyzer import StaticArtifacts
from apk_hacker.domain.models.environment import EnvironmentSnapshot, ToolStatus


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_main_window_runs_demo_hook_workflow(tmp_path: Path) -> None:
    app = _app()
    window = MainWindow(
        fixture_root=Path("tests/fixtures/static_outputs"),
        jadx_sources_root=Path("tests/fixtures/jadx_sources"),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )

    window.task_center.sample_path_input.setText("/samples/demo.apk")
    window.task_center.load_demo_button.click()

    assert window.static_summary.package_value.text() == "com.demo.shell"
    assert window.method_index.method_list.count() == 5

    window.method_index.search_input.setText("upload")
    window.method_index.apply_search()
    assert window.method_index.method_list.count() == 2

    window.method_index.method_list.setCurrentRow(1)
    window.method_index.add_selected_button.click()
    assert window.script_plan.plan_list.count() == 1
    selected_method = window.method_index.current_method()
    assert selected_method is not None
    assert selected_method.parameter_types == ("String", "String")

    window.script_plan.run_fake_button.click()
    assert window.execution_logs.log_list.count() == 1
    assert "buildUploadUrl" in window.execution_logs.log_list.item(0).text()
    assert "1 event" in window.results_summary.summary_label.text()

    window.script_plan.run_fake_button.click()
    assert window.execution_logs.log_list.count() == 1
    assert "1 event" in window.results_summary.summary_label.text()

    assert app is not None
    window.close()


class _FakeStaticAnalyzer:
    def __init__(self, artifacts: StaticArtifacts) -> None:
        self.artifacts = artifacts
        self.calls: list[tuple[Path, Path | None, str]] = []

    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        self.calls.append((target_path, output_dir, mode))
        return self.artifacts


class _FailingStaticAnalyzer:
    def analyze(self, target_path: Path, output_dir: Path | None = None, mode: str = "auto") -> StaticArtifacts:
        raise RuntimeError("jadx is unavailable")


class _FakeJadxLauncher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def __call__(self, jadx_gui_path: str, target_path: Path) -> None:
        self.calls.append((jadx_gui_path, target_path))


class _FakeRealBackend(ExecutionBackend):
    def __init__(self, events: tuple[HookEvent, ...]) -> None:
        self.events = events
        self.calls: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> tuple[HookEvent, ...]:
        self.calls.append(request)
        return self.events


class _ReadyFridaEnvironmentService:
    def inspect(self) -> EnvironmentSnapshot:
        return EnvironmentSnapshot(
            tools=(
                ToolStatus(name="jadx", label="jadx", available=True, path="/opt/tools/jadx"),
                ToolStatus(name="jadx-gui", label="jadx-gui", available=True, path="/opt/tools/jadx-gui"),
                ToolStatus(name="apktool", label="apktool", available=True, path="/opt/tools/apktool"),
                ToolStatus(name="adb", label="adb", available=True, path="/opt/android/adb"),
                ToolStatus(name="frida", label="frida", available=True, path="/opt/homebrew/bin/frida"),
                ToolStatus(name="python-frida", label="python-frida", available=True, path="module:frida"),
            )
        )


def test_main_window_runs_real_static_analysis_workflow(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    assert window.static_summary.package_value.text() == "com.demo.shell"
    assert window.task_center.current_sample_value.text() == str(sample_path)
    assert window.method_index.method_list.count() == 5
    assert fake_analyzer.calls == [(sample_path, tmp_path / "static-analysis", "auto")]
    assert app is not None
    window.close()


def test_main_window_shows_hook_assistant_recommendations_and_adds_selected_item(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    assert window.hook_assistant.recommendation_list.count() >= 1
    assert "buildUploadUrl" in window.hook_assistant.recommendation_list.item(0).text()

    window.hook_assistant.recommendation_list.setCurrentRow(0)
    window.hook_assistant.add_selected_button.click()

    assert window.script_plan.plan_list.count() == 1
    assert "buildUploadUrl" in window.script_plan.plan_list.item(0).text()
    assert "buildUploadUrl" in window.script_plan.preview.toPlainText()
    assert app is not None
    window.close()


def test_main_window_can_add_template_recommendation_and_run_fake_analysis(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    template_row = next(
        row
        for row in range(window.hook_assistant.recommendation_list.count())
        if "OkHttp3 SSL Unpinning" in window.hook_assistant.recommendation_list.item(row).text()
    )
    window.hook_assistant.recommendation_list.setCurrentRow(template_row)
    window.hook_assistant.add_selected_button.click()

    assert window.script_plan.plan_list.count() == 1
    assert "OkHttp3 SSL Unpinning" in window.script_plan.plan_list.item(0).text()
    assert "ssl.okhttp3_unpin" in window.script_plan.preview.toPlainText()

    window.script_plan.run_fake_button.click()

    assert window.execution_logs.log_list.count() == 1
    assert "OkHttp3 SSL Unpinning" in window.execution_logs.log_list.item(0).text()
    assert app is not None
    window.close()


def test_main_window_loads_har_capture_and_updates_summary(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.traffic_capture.har_path_input.setText(str(Path("tests/fixtures/traffic/sample.har").resolve()))
    window.traffic_capture.load_button.click()

    assert window.traffic_capture.flow_list.count() == 2
    assert "demo-c2.example/api/upload" in window.traffic_capture.flow_list.item(0).text()
    assert "suspicious" in window.traffic_capture.flow_list.item(0).text().lower()
    assert "1 suspicious flow" in window.results_summary.summary_label.text().lower()
    assert app is not None
    window.close()


def test_main_window_surfaces_real_static_analysis_failures(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "broken.apk"
    sample_path.write_bytes(b"apk")
    fake_launcher = _FakeJadxLauncher()
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=_FailingStaticAnalyzer()),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(
        controller=controller,
        jadx_gui_path="/opt/jadx/bin/jadx-gui",
        jadx_launcher=fake_launcher,
    )

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    assert "failed" in window.results_summary.summary_label.text().lower()
    assert "jadx is unavailable" in window.results_summary.summary_label.text().lower()
    assert window.task_center.current_sample_value.text() == str(sample_path)
    assert window.method_index.method_list.count() == 0
    assert not window.open_jadx_action.isEnabled()
    window.open_jadx_action.trigger()
    assert fake_launcher.calls == []
    assert app is not None
    window.close()


def test_main_window_opens_loaded_sample_in_jadx(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    fake_launcher = _FakeJadxLauncher()
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(
        controller=controller,
        jadx_gui_path="/opt/jadx/bin/jadx-gui",
        jadx_launcher=fake_launcher,
    )

    assert not window.open_jadx_action.isEnabled()
    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    assert window.open_jadx_action.isEnabled()
    window.open_jadx_action.trigger()

    assert fake_launcher.calls == [("/opt/jadx/bin/jadx-gui", sample_path)]
    assert app is not None
    window.close()


def test_main_window_keeps_open_jadx_disabled_for_blank_path_after_load(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller, jadx_gui_path="")

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    assert not window.open_jadx_action.isEnabled()
    assert app is not None
    window.close()


def test_main_window_adds_custom_script_to_plan_and_runs_fake_analysis(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    (scripts_root / "trace_login.js").write_text("send('trace');\n", encoding="utf-8")
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=scripts_root,
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()

    assert window.custom_scripts.script_list.count() == 1
    window.custom_scripts.script_list.setCurrentRow(0)
    window.custom_scripts.add_selected_button.click()

    assert window.script_plan.plan_list.count() == 1
    assert "trace_login" in window.script_plan.plan_list.item(0).text()

    window.script_plan.run_fake_button.click()

    assert window.execution_logs.log_list.count() == 1
    assert "trace_login" in window.execution_logs.log_list.item(0).text()
    assert "1 event" in window.results_summary.summary_label.text()
    assert app is not None
    window.close()


def test_main_window_saves_custom_script_from_editor_and_adds_it_to_plan(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    scripts_root = tmp_path / "scripts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=scripts_root,
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.custom_scripts.name_input.setText("trace_login")
    window.custom_scripts.editor.setPlainText("send('trace');\n")
    window.custom_scripts.save_button.click()

    assert window.custom_scripts.script_list.count() == 1
    assert window.custom_scripts.script_list.item(0).text() == "trace_login"
    assert "Saved custom script" in window.results_summary.summary_label.text()

    window.custom_scripts.script_list.setCurrentRow(0)
    window.custom_scripts.add_selected_button.click()

    assert "trace_login" in window.script_plan.plan_list.item(0).text()
    assert app is not None
    window.close()


def test_main_window_preserves_custom_script_order_before_method_hooks(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    (scripts_root / "trace_login.js").write_text("send('trace');\n", encoding="utf-8")
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=scripts_root,
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.custom_scripts.script_list.setCurrentRow(0)
    window.custom_scripts.add_selected_button.click()
    window.method_index.search_input.setText("buildUploadUrl")
    window.method_index.apply_search()
    window.method_index.method_list.setCurrentRow(0)
    window.method_index.add_selected_button.click()

    assert "trace_login" in window.script_plan.plan_list.item(0).text()
    assert "buildUploadUrl" in window.script_plan.plan_list.item(1).text()

    window.script_plan.run_fake_button.click()

    assert "trace_login" in window.execution_logs.log_list.item(0).text()
    assert "buildUploadUrl" in window.execution_logs.log_list.item(1).text()
    assert app is not None
    window.close()


def test_main_window_disables_unavailable_real_execution_mode(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.method_index.method_list.setCurrentRow(0)
    window.method_index.add_selected_button.click()
    real_device_index = window.script_plan.execution_mode_combo.findData("real_device")

    assert real_device_index >= 0
    assert not window.script_plan.execution_mode_combo.model().item(real_device_index).isEnabled()
    assert window.script_plan.execution_mode_combo.currentData() == "fake_backend"
    assert app is not None
    window.close()


def test_main_window_runs_injected_real_backend_when_mode_is_real_device(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    real_events = (
        HookEvent(
            timestamp="2026-04-05T00:00:00+00:00",
            job_id="job-1",
            event_type="method_call",
            source="real",
            class_name="com.demo.net.Config",
            method_name="buildUploadUrl",
            arguments=("String",),
            return_value="real-return",
            stacktrace="com.demo.net.Config.buildUploadUrl:1",
            raw_payload={"plugin_id": "builtin.method-hook"},
        ),
    )
    real_backend = _FakeRealBackend(real_events)
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        execution_backends={"real_device": real_backend},
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.method_index.search_input.setText("buildUploadUrl")
    window.method_index.apply_search()
    window.method_index.method_list.setCurrentRow(0)
    window.method_index.add_selected_button.click()
    window.script_plan.execution_mode_combo.setCurrentText("Real Device")
    window.script_plan.run_fake_button.click()

    assert len(real_backend.calls) == 1
    assert window.execution_logs.log_list.count() == 1
    assert "real-return" in window.execution_logs.log_list.item(0).text()
    assert "1 event" in window.results_summary.summary_label.text()
    assert app is not None
    window.close()


def test_main_window_routes_to_named_real_backend_preset(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    preset_events = (
        HookEvent(
            timestamp="2026-04-06T00:00:00+00:00",
            job_id="job-1",
            event_type="frida_session",
            source="real",
            class_name="frida",
            method_name="attached",
            arguments=("com.demo.shell", "1"),
            return_value="attached",
            stacktrace="",
            raw_payload={"source_script": "02_builduploadurl.js"},
        ),
    )
    preset_backend = _FakeRealBackend(preset_events)
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        environment_service=_ReadyFridaEnvironmentService(),
        execution_backends={"real_frida_session": preset_backend},
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.method_index.search_input.setText("buildUploadUrl")
    window.method_index.apply_search()
    window.method_index.method_list.setCurrentRow(0)
    window.method_index.add_selected_button.click()
    window.script_plan.execution_mode_combo.setCurrentText("Frida Session")
    window.script_plan.run_fake_button.click()

    assert len(preset_backend.calls) == 1
    assert window.execution_logs.log_list.count() == 1
    assert "[02_builduploadurl.js]" in window.execution_logs.log_list.item(0).text()
    assert "attached" in window.execution_logs.log_list.item(0).text()
    assert "1 event" in window.results_summary.summary_label.text()
    assert app is not None
    window.close()


def test_main_window_reports_auto_routed_real_device_backend(tmp_path: Path) -> None:
    app = _app()
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    preset_events = (
        HookEvent(
            timestamp="2026-04-06T00:00:00+00:00",
            job_id="job-1",
            event_type="frida_session",
            source="real",
            class_name="frida",
            method_name="attached",
            arguments=("com.demo.shell", "1"),
            return_value="attached",
            stacktrace="",
            raw_payload={"source_script": "02_builduploadurl.js"},
        ),
    )
    preset_backend = _FakeRealBackend(preset_events)
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        environment_service=_ReadyFridaEnvironmentService(),
        execution_backends={"real_frida_session": preset_backend},
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.run_analysis_button.click()
    window.method_index.search_input.setText("buildUploadUrl")
    window.method_index.apply_search()
    window.method_index.method_list.setCurrentRow(0)
    window.method_index.add_selected_button.click()
    window.script_plan.execution_mode_combo.setCurrentText("Real Device")
    window.script_plan.run_fake_button.click()

    assert len(preset_backend.calls) == 1
    assert "Real Device -> Frida Session" in window.results_summary.summary_label.text()
    assert app is not None
    window.close()


def test_main_window_forwards_runtime_device_settings_to_real_backend(tmp_path: Path) -> None:
    app = _app()
    helper = tmp_path / "emit_runtime_backend.py"
    helper.write_text(
        """
import json
import os

print(json.dumps({
    "event_type": "runtime_env",
    "class_name": "cli.real",
    "method_name": "configured",
    "arguments": [
        os.environ.get("APKHACKER_DEVICE_SERIAL", ""),
        os.environ.get("APKHACKER_FRIDA_SERVER_BINARY", ""),
        os.environ.get("APKHACKER_FRIDA_SERVER_REMOTE_PATH", ""),
        os.environ.get("APKHACKER_FRIDA_SESSION_SECONDS", ""),
    ],
    "return_value": "ok",
    "stacktrace": ""
}))
""".strip()
        + "\n",
        encoding="utf-8",
    )
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")
    frida_server_binary = tmp_path / "frida-server"
    frida_server_binary.write_text("fake-binary", encoding="utf-8")
    output_root = tmp_path / "artifacts"
    fixture_root = Path("tests/fixtures/static_outputs").resolve()
    jadx_sources = Path("tests/fixtures/jadx_sources").resolve()
    fake_analyzer = _FakeStaticAnalyzer(
        StaticArtifacts(
            output_root=output_root,
            report_dir=output_root / "报告" / "sample",
            cache_dir=output_root / "cache" / "sample",
            analysis_json=fixture_root / "sample_analysis.json",
            callback_config_json=fixture_root / "sample_callback-config.json",
            noise_log_json=output_root / "cache" / "sample" / "noise-log.json",
            jadx_sources_dir=jadx_sources,
            jadx_project_dir=None,
        )
    )
    controller = WorkbenchController(
        job_service=JobService(static_analyzer=fake_analyzer),
        scripts_root=tmp_path / "scripts",
        db_root=tmp_path,
        execution_backends={
            "real_device": RealExecutionBackend(
                command=f"{sys.executable} {helper}",
                artifact_root=tmp_path / "execution-runs",
            ),
        },
    )
    window = MainWindow(controller=controller)

    window.task_center.sample_path_input.setText(str(sample_path))
    window.task_center.device_serial_input.setText("serial-123")
    window.task_center.frida_server_binary_input.setText(str(frida_server_binary))
    window.task_center.frida_server_remote_path_input.setText("/data/local/tmp/custom-frida-server")
    window.task_center.frida_session_seconds_input.setText("3.5")
    window.task_center.run_analysis_button.click()
    window.method_index.search_input.setText("buildUploadUrl")
    window.method_index.apply_search()
    window.method_index.method_list.setCurrentRow(0)
    window.method_index.add_selected_button.click()
    window.script_plan.execution_mode_combo.setCurrentText("Real Device")
    window.script_plan.run_fake_button.click()

    assert window.execution_logs.log_list.count() == 1
    assert window._state.hook_events[0].arguments == (
        "serial-123",
        str(frida_server_binary),
        "/data/local/tmp/custom-frida-server",
        "3.5",
    )
    assert window.results_summary.db_path_label.text().endswith("-run-1.sqlite3")
    assert "execution-runs" in window.results_summary.bundle_path_label.text()
    assert app is not None
    window.close()
