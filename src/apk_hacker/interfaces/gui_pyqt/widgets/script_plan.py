from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from apk_hacker.domain.models.hook_plan import HookPlan


class ScriptPlanWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on_run_requested: Callable[[], None] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Script Plan"))
        self.plan_list = QListWidget()
        layout.addWidget(self.plan_list)
        self.run_fake_button = QPushButton("Run Fake Analysis")
        layout.addWidget(self.run_fake_button)
        layout.addStretch(1)

        self.run_fake_button.clicked.connect(self._emit_run_requested)

    def set_plan(self, plan: HookPlan) -> None:
        self.plan_list.clear()
        for item in plan.items:
            target = item.target
            label = item.kind
            if target is not None:
                label = f"{target.class_name}.{target.method_name} [{item.kind}]"
            QListWidgetItem(label, self.plan_list)

    def _emit_run_requested(self) -> None:
        if self.on_run_requested is not None:
            self.on_run_requested()
