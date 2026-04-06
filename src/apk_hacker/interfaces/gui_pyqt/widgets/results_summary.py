from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResultsSummaryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Results Summary"))
        self.summary_label = QLabel("No analysis run yet.")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.db_path_label = QLabel("Last Run DB: -")
        self.db_path_label.setWordWrap(True)
        layout.addWidget(self.db_path_label)
        self.bundle_path_label = QLabel("Execution Bundle: -")
        self.bundle_path_label.setWordWrap(True)
        layout.addWidget(self.bundle_path_label)
        layout.addStretch(1)

    def set_summary(
        self,
        text: str,
        db_path: Path | None = None,
        bundle_path: Path | None = None,
    ) -> None:
        self.summary_label.setText(text)
        self.db_path_label.setText(f"Last Run DB: {db_path}" if db_path is not None else "Last Run DB: -")
        self.bundle_path_label.setText(
            f"Execution Bundle: {bundle_path}" if bundle_path is not None else "Execution Bundle: -"
        )
