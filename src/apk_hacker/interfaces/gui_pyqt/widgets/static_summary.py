from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StaticSummaryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Static Summary"))
