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

from apk_hacker.application.services.execution_presets import ExecutionPresetStatus
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.models.environment import EnvironmentSnapshot


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
        self.run_analysis_button = QPushButton("Run Static Analysis")
        actions.addWidget(self.run_analysis_button)
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

        environment_box = QGroupBox("Environment")
        environment_layout = QFormLayout(environment_box)
        self.environment_summary_value = QLabel("Not checked yet")
        self.environment_details_value = QLabel("-")
        self.environment_details_value.setWordWrap(True)
        self.execution_presets_value = QLabel("-")
        self.execution_presets_value.setWordWrap(True)
        self.refresh_environment_button = QPushButton("Refresh Environment")
        environment_layout.addRow("Summary", self.environment_summary_value)
        environment_layout.addRow("Tools", self.environment_details_value)
        environment_layout.addRow("Execution Presets", self.execution_presets_value)
        environment_layout.addRow("", self.refresh_environment_button)
        layout.addWidget(environment_box)
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

    def set_analysis_available(self, available: bool) -> None:
        self.run_analysis_button.setEnabled(available)

    def set_environment(self, snapshot: EnvironmentSnapshot | None) -> None:
        if snapshot is None:
            self.environment_summary_value.setText("Not checked yet")
            self.environment_details_value.setText("-")
            return

        self.environment_summary_value.setText(snapshot.summary)
        detail_lines = []
        for tool in snapshot.tools:
            value = tool.path if tool.available and tool.path is not None else "missing"
            detail_lines.append(f"{tool.label}: {value}")
        self.environment_details_value.setText("\n".join(detail_lines))

    def set_execution_presets(self, statuses: tuple[ExecutionPresetStatus, ...]) -> None:
        if not statuses:
            self.execution_presets_value.setText("-")
            return
        self.execution_presets_value.setText(
            "\n".join(f"{status.label}: {status.detail}" for status in statuses)
        )
