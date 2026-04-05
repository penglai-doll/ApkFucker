from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QComboBox, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from apk_hacker.domain.models.hook_plan import HookPlan


class ScriptPlanWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on_run_requested: Callable[[], None] | None = None
        self.on_execution_mode_changed: Callable[[str], None] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Script Plan"))
        self.plan_list = QListWidget()
        layout.addWidget(self.plan_list)
        self.execution_mode_combo = QComboBox()
        self.execution_mode_combo.addItem("Fake Backend", userData="fake_backend")
        self.execution_mode_combo.addItem("Real Device", userData="real_device")
        layout.addWidget(self.execution_mode_combo)
        self.run_fake_button = QPushButton("Run Analysis")
        layout.addWidget(self.run_fake_button)
        layout.addStretch(1)

        self.run_fake_button.clicked.connect(self._emit_run_requested)
        self.execution_mode_combo.currentIndexChanged.connect(self._emit_execution_mode_changed)

    def set_plan(self, plan: HookPlan) -> None:
        self.plan_list.clear()
        for item in plan.items:
            target = item.target
            label = item.kind
            if target is not None:
                label = f"{target.class_name}.{target.method_name} [{item.kind}]"
            elif item.kind == "custom_script":
                script_name = str(item.render_context.get("script_name", item.kind))
                label = f"{script_name} [{item.kind}]"
            QListWidgetItem(label, self.plan_list)

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
