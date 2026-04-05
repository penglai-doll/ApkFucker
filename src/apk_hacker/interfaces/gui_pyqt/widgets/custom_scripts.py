from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from apk_hacker.application.services.custom_script_service import CustomScriptRecord


class CustomScriptsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Custom Frida Scripts"))
        self.script_list = QListWidget()
        layout.addWidget(self.script_list)
        layout.addStretch(1)

    def set_scripts(self, scripts: tuple[CustomScriptRecord, ...]) -> None:
        self.script_list.clear()
        for script in scripts:
            QListWidgetItem(script.name, self.script_list)
