from PyQt6.QtWidgets import QApplication

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.interfaces.gui_pyqt.widgets.execution_logs import ExecutionLogsWidget


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_execution_logs_widget_shows_source_script_when_available() -> None:
    app = _app()
    widget = ExecutionLogsWidget()
    widget.set_events(
        (
            HookEvent(
                timestamp="2026-04-06T00:00:00Z",
                job_id="job-1",
                event_type="method_call",
                source="real",
                class_name="com.demo.net.Config",
                method_name="buildUploadUrl",
                arguments=("plaintext",),
                return_value="ciphertext",
                stacktrace="com.demo.net.Config.buildUploadUrl:1",
                raw_payload={"source_script": "02_builduploadurl.js"},
            ),
        )
    )

    assert widget.log_list.count() == 1
    assert "[02_builduploadurl.js]" in widget.log_list.item(0).text()
    assert app is not None
    widget.close()
