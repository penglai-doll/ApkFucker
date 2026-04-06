from __future__ import annotations

import json

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from apk_hacker.domain.models.hook_event import HookEvent


class ExecutionLogsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Execution & Logs"))
        self.log_list = QListWidget()
        layout.addWidget(self.log_list)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select an event to inspect its arguments, return value, stacktrace, and payload.")
        layout.addWidget(self.details)
        self.copy_details_button = QPushButton("Copy Event Details")
        self.copy_details_button.setEnabled(False)
        layout.addWidget(self.copy_details_button)
        layout.addStretch(1)
        self._events: tuple[HookEvent, ...] = ()
        self.log_list.currentRowChanged.connect(self._sync_details)
        self.copy_details_button.clicked.connect(self._copy_details)

    def set_events(self, events: tuple[HookEvent, ...]) -> None:
        self._events = events
        self.log_list.clear()
        for event in events:
            source_script = str(event.raw_payload.get("source_script", "")).strip()
            prefix = f"[{source_script}] " if source_script else ""
            QListWidgetItem(
                f"{prefix}{event.event_type}: {event.class_name}.{event.method_name} -> {event.return_value or '-'}",
                self.log_list,
            )
        if self.log_list.count() > 0:
            self.log_list.setCurrentRow(0)
        else:
            self.details.setPlainText("")
            self.copy_details_button.setEnabled(False)

    def _sync_details(self) -> None:
        row = self.log_list.currentRow()
        if row < 0 or row >= len(self._events):
            self.details.setPlainText("")
            self.copy_details_button.setEnabled(False)
            return
        event = self._events[row]
        payload = json.dumps(event.raw_payload, ensure_ascii=False, indent=2)
        self.details.setPlainText(
            "\n".join(
                (
                    f"Timestamp: {event.timestamp}",
                    f"Source: {event.source}",
                    f"Type: {event.event_type}",
                    f"Target: {event.class_name}.{event.method_name}",
                    f"Arguments: {', '.join(event.arguments) if event.arguments else '-'}",
                    f"Return: {event.return_value or '-'}",
                    "Stacktrace:",
                    event.stacktrace or "-",
                    "",
                    "Raw Payload:",
                    payload,
                )
            )
        )
        self.copy_details_button.setEnabled(True)

    def _copy_details(self) -> None:
        details = self.details.toPlainText().strip()
        if not details:
            return
        QGuiApplication.clipboard().setText(details)
