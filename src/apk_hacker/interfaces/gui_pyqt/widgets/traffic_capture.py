from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from apk_hacker.domain.models.traffic import TrafficCapture


class TrafficCaptureWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on_load_requested: Callable[[], None] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Traffic Capture"))
        self.har_path_input = QLineEdit()
        self.har_path_input.setPlaceholderText("/path/to/capture.har")
        layout.addWidget(self.har_path_input)
        self.load_button = QPushButton("Load HAR Capture")
        layout.addWidget(self.load_button)
        self.summary_label = QLabel("No HAR capture loaded.")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.flow_list = QListWidget()
        layout.addWidget(self.flow_list)
        layout.addStretch(1)

        self.load_button.clicked.connect(self._emit_load_requested)

    def selected_har_path(self) -> Path:
        return Path(self.har_path_input.text().strip())

    def set_capture(self, capture: TrafficCapture | None) -> None:
        self.flow_list.clear()
        if capture is None:
            self.summary_label.setText("No HAR capture loaded.")
            return

        self.summary_label.setText(
            f"{capture.flow_count} flow(s), {capture.suspicious_count} suspicious flow(s) loaded from {capture.source_path.name}."
        )
        for flow in capture.flows:
            indicator_text = ", ".join(flow.matched_indicators) or "-"
            status_code = flow.status_code if flow.status_code is not None else "-"
            label = f"{flow.method} {flow.url} [{status_code}] suspicious={flow.suspicious} indicators={indicator_text}"
            QListWidgetItem(label, self.flow_list)

    def _emit_load_requested(self) -> None:
        if self.on_load_requested is not None:
            self.on_load_requested()
