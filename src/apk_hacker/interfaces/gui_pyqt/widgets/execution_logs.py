from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from apk_hacker.domain.models.hook_event import HookEvent


class ExecutionLogsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Execution & Logs"))
        self.log_list = QListWidget()
        layout.addWidget(self.log_list)
        layout.addStretch(1)

    def set_events(self, events: tuple[HookEvent, ...]) -> None:
        self.log_list.clear()
        for event in events:
            QListWidgetItem(
                f"{event.event_type}: {event.class_name}.{event.method_name} -> {event.return_value or '-'}",
                self.log_list,
            )
