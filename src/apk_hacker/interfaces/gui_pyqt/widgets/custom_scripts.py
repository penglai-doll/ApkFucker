from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from apk_hacker.application.services.custom_script_service import CustomScriptRecord


class CustomScriptsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on_add_selected_requested: Callable[[], None] | None = None
        self._scripts: tuple[CustomScriptRecord, ...] = ()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Custom Frida Scripts"))
        self.script_list = QListWidget()
        layout.addWidget(self.script_list)
        self.add_selected_button = QPushButton("Add Selected Script To Plan")
        layout.addWidget(self.add_selected_button)
        layout.addStretch(1)
        self.add_selected_button.clicked.connect(self._emit_add_selected_requested)

    def set_scripts(self, scripts: tuple[CustomScriptRecord, ...]) -> None:
        self._scripts = scripts
        self.script_list.clear()
        for script in scripts:
            QListWidgetItem(script.name, self.script_list)

    def current_script(self) -> CustomScriptRecord | None:
        row = self.script_list.currentRow()
        if row < 0 or row >= len(self._scripts):
            return None
        return self._scripts[row]

    def _emit_add_selected_requested(self) -> None:
        if self.on_add_selected_requested is not None:
            self.on_add_selected_requested()
