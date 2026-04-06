from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QComboBox, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from apk_hacker.application.services.execution_presets import EXECUTION_PRESETS, ExecutionPresetStatus
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem


class ScriptPlanWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on_run_requested: Callable[[], None] | None = None
        self.on_execution_mode_changed: Callable[[str], None] | None = None
        self._plan_items: tuple[HookPlanItem, ...] = ()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Script Plan"))
        self.plan_list = QListWidget()
        layout.addWidget(self.plan_list)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Rendered script preview will appear here.")
        layout.addWidget(self.preview)
        self.execution_mode_combo = QComboBox()
        for preset in EXECUTION_PRESETS:
            self.execution_mode_combo.addItem(preset.label, userData=preset.key)
        layout.addWidget(self.execution_mode_combo)
        self.run_fake_button = QPushButton("Run Analysis")
        layout.addWidget(self.run_fake_button)
        layout.addStretch(1)

        self.run_fake_button.clicked.connect(self._emit_run_requested)
        self.execution_mode_combo.currentIndexChanged.connect(self._emit_execution_mode_changed)
        self.plan_list.currentRowChanged.connect(self._sync_preview)

    def set_execution_presets(self, statuses: tuple[ExecutionPresetStatus, ...], current_mode: str) -> None:
        if not statuses:
            return
        self.execution_mode_combo.blockSignals(True)
        model = self.execution_mode_combo.model()
        if not isinstance(model, QStandardItemModel):
            self.execution_mode_combo.blockSignals(False)
            return
        for row, status in enumerate(statuses):
            if row >= model.rowCount():
                continue
            item = model.item(row)
            if item is None:
                continue
            item.setEnabled(status.available)
            item.setToolTip(status.detail)
        self.execution_mode_combo.blockSignals(False)
        self.set_execution_mode(current_mode)

    def set_plan(self, plan: HookPlan) -> None:
        self._plan_items = plan.items
        self.plan_list.clear()
        for item in plan.items:
            target = item.target
            label = item.kind
            if target is not None:
                label = f"{target.class_name}.{target.method_name} [{item.kind}]"
            elif item.kind == "template_hook":
                template_name = str(item.render_context.get("template_name", item.kind))
                label = f"{template_name} [{item.kind}]"
            elif item.kind == "custom_script":
                script_name = str(item.render_context.get("script_name", item.kind))
                label = f"{script_name} [{item.kind}]"
            QListWidgetItem(label, self.plan_list)
        if self.plan_list.count() > 0:
            self.plan_list.setCurrentRow(0)
        else:
            self.preview.setPlainText("")

    def set_execution_mode(self, mode: str) -> None:
        index = self.execution_mode_combo.findData(mode)
        if index >= 0 and index != self.execution_mode_combo.currentIndex():
            self.execution_mode_combo.setCurrentIndex(index)

    def current_execution_mode(self) -> str:
        current_mode = self.execution_mode_combo.currentData()
        return str(current_mode) if current_mode is not None else "fake_backend"

    def _emit_run_requested(self) -> None:
        if self.on_run_requested is not None:
            self.on_run_requested()

    def _emit_execution_mode_changed(self) -> None:
        if self.on_execution_mode_changed is not None:
            self.on_execution_mode_changed(self.current_execution_mode())

    def _sync_preview(self) -> None:
        row = self.plan_list.currentRow()
        if row < 0 or row >= len(self._plan_items):
            self.preview.setPlainText("")
            return
        script = str(self._plan_items[row].render_context.get("rendered_script", ""))
        self.preview.setPlainText(script)
