from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apk_hacker.domain.models.job import AnalysisJob


class TaskCenterWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        input_box = QGroupBox("Sample")
        input_layout = QFormLayout(input_box)
        self.sample_path_input = QLineEdit()
        self.sample_path_input.setPlaceholderText("/samples/demo.apk")
        input_layout.addRow("Sample Path", self.sample_path_input)
        layout.addWidget(input_box)

        actions = QHBoxLayout()
        self.load_demo_button = QPushButton("Load Demo Workspace")
        actions.addWidget(self.load_demo_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        job_box = QGroupBox("Job")
        job_layout = QFormLayout(job_box)
        self.job_id_value = QLabel("-")
        self.status_value = QLabel("Idle")
        self.current_sample_value = QLabel("-")
        job_layout.addRow("Job ID", self.job_id_value)
        job_layout.addRow("Status", self.status_value)
        job_layout.addRow("Loaded Sample", self.current_sample_value)
        layout.addWidget(job_box)
        layout.addStretch(1)

    def selected_sample_path(self) -> Path:
        sample_text = self.sample_path_input.text().strip() or "/samples/demo.apk"
        return Path(sample_text)

    def set_job(self, job: AnalysisJob | None, sample_path: Path | None) -> None:
        if job is None:
            self.job_id_value.setText("-")
            self.status_value.setText("Idle")
        else:
            self.job_id_value.setText(job.job_id)
            self.status_value.setText(job.status)
        self.current_sample_value.setText(str(sample_path) if sample_path is not None else "-")

    def set_demo_available(self, available: bool) -> None:
        self.load_demo_button.setEnabled(available)
