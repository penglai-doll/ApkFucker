from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from apk_hacker.domain.models.static_inputs import StaticInputs


class StaticSummaryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        summary_box = QGroupBox("Static Summary")
        form = QFormLayout(summary_box)
        self.package_value = self._build_value_label()
        self.tags_value = self._build_value_label()
        self.permissions_value = self._build_value_label()
        self.endpoints_value = self._build_value_label()
        form.addRow("Package", self.package_value)
        form.addRow("Technical Tags", self.tags_value)
        form.addRow("Dangerous Permissions", self.permissions_value)
        form.addRow("Callback Endpoints", self.endpoints_value)
        self.scroll_area.setWidget(summary_box)
        layout.addWidget(self.scroll_area)
        layout.addStretch(1)

    def set_static_inputs(self, static_inputs: StaticInputs | None) -> None:
        if static_inputs is None:
            self.package_value.setText("-")
            self.tags_value.setText("-")
            self.permissions_value.setText("-")
            self.endpoints_value.setText("-")
            return

        self.package_value.setText(static_inputs.package_name)
        self.tags_value.setText(", ".join(static_inputs.technical_tags) or "-")
        self.permissions_value.setText(", ".join(static_inputs.dangerous_permissions) or "-")
        self.endpoints_value.setText(", ".join(static_inputs.callback_endpoints) or "-")

    @staticmethod
    def _build_value_label() -> QLabel:
        label = QLabel("-")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        return label
