from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QScrollArea

from apk_hacker.domain.models.config import ArtifactPaths
from apk_hacker.domain.models.static_inputs import StaticInputs
from apk_hacker.interfaces.gui_pyqt.widgets.static_summary import StaticSummaryWidget


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_static_summary_wraps_and_allows_selecting_long_text() -> None:
    app = _app()
    widget = StaticSummaryWidget()

    assert isinstance(widget.scroll_area, QScrollArea)
    assert widget.scroll_area.widgetResizable()
    assert widget.tags_value.wordWrap()
    assert widget.permissions_value.wordWrap()
    assert widget.endpoints_value.wordWrap()
    assert widget.tags_value.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    assert widget.permissions_value.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    assert widget.endpoints_value.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse

    assert app is not None
    widget.close()


def test_static_summary_keeps_long_endpoint_text_visible() -> None:
    app = _app()
    widget = StaticSummaryWidget()
    static_inputs = StaticInputs(
        sample_path=Path("/samples/demo.apk"),
        package_name="com.demo.shell",
        technical_tags=("webview-hybrid", "network-callback", "long-tag-value"),
        dangerous_permissions=(
            "android.permission.READ_SMS",
            "android.permission.RECORD_AUDIO",
            "android.permission.ACCESS_FINE_LOCATION",
        ),
        callback_endpoints=(
            "https://demo-c2.example/api/upload?device_id=1234567890abcdefghijklmnopqrstuvwxyz",
            "https://demo-c2.example/api/config/very/long/path/for/testing/layout",
        ),
        callback_clues=(),
        crypto_signals=(),
        packer_hints=(),
        limitations=(),
        artifact_paths=ArtifactPaths(),
    )

    widget.set_static_inputs(static_inputs)

    assert "long-tag-value" in widget.tags_value.text()
    assert "ACCESS_FINE_LOCATION" in widget.permissions_value.text()
    assert "very/long/path/for/testing/layout" in widget.endpoints_value.text()
    assert app is not None
    widget.close()
