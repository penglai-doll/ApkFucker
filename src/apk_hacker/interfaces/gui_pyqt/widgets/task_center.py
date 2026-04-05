from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TaskCenterWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Task Center"))
