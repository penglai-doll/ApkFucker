from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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
        db_actions = QHBoxLayout()
        self.copy_db_path_button = QPushButton("Copy Run DB Path")
        self.copy_db_path_button.setEnabled(False)
        db_actions.addWidget(self.copy_db_path_button)
        db_actions.addStretch(1)
        layout.addLayout(db_actions)
        self.bundle_path_label = QLabel("Execution Bundle: -")
        self.bundle_path_label.setWordWrap(True)
        layout.addWidget(self.bundle_path_label)
        bundle_actions = QHBoxLayout()
        self.copy_bundle_path_button = QPushButton("Copy Bundle Path")
        self.copy_bundle_path_button.setEnabled(False)
        bundle_actions.addWidget(self.copy_bundle_path_button)
        bundle_actions.addStretch(1)
        layout.addLayout(bundle_actions)
        layout.addStretch(1)
        self._db_path: Path | None = None
        self._bundle_path: Path | None = None
        self.copy_db_path_button.clicked.connect(self._copy_db_path)
        self.copy_bundle_path_button.clicked.connect(self._copy_bundle_path)

    def set_summary(
        self,
        text: str,
        db_path: Path | None = None,
        bundle_path: Path | None = None,
    ) -> None:
        self.summary_label.setText(text)
        self._db_path = db_path
        self._bundle_path = bundle_path
        self.db_path_label.setText(f"Last Run DB: {db_path}" if db_path is not None else "Last Run DB: -")
        self.bundle_path_label.setText(
            f"Execution Bundle: {bundle_path}" if bundle_path is not None else "Execution Bundle: -"
        )
        self.copy_db_path_button.setEnabled(db_path is not None)
        self.copy_bundle_path_button.setEnabled(bundle_path is not None)

    def _copy_db_path(self) -> None:
        if self._db_path is None:
            return
        QGuiApplication.clipboard().setText(str(self._db_path))

    def _copy_bundle_path(self) -> None:
        if self._bundle_path is None:
            return
        QGuiApplication.clipboard().setText(str(self._bundle_path))
