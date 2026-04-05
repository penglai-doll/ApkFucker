from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apk_hacker.application.services.custom_script_service import CustomScriptRecord


class CustomScriptsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.on_add_selected_requested: Callable[[], None] | None = None
        self.on_save_requested: Callable[[], None] | None = None
        self.on_selection_changed: Callable[[], None] | None = None
        self._scripts: tuple[CustomScriptRecord, ...] = ()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Custom Frida Scripts"))
        self.script_list = QListWidget()
        layout.addWidget(self.script_list)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("trace_login")
        layout.addWidget(self.name_input)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Java.perform(function() {\n    // Frida script here\n});")
        layout.addWidget(self.editor)
        actions = QHBoxLayout()
        self.add_selected_button = QPushButton("Add Selected Script To Plan")
        actions.addWidget(self.add_selected_button)
        self.save_button = QPushButton("Save Script")
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.add_selected_button.clicked.connect(self._emit_add_selected_requested)
        self.save_button.clicked.connect(self._emit_save_requested)
        self.script_list.currentRowChanged.connect(self._emit_selection_changed)

    def set_scripts(
        self,
        scripts: tuple[CustomScriptRecord, ...],
        preferred_script_path: str | None = None,
    ) -> None:
        self._scripts = scripts
        self.script_list.blockSignals(True)
        try:
            self.script_list.clear()
            preferred_row: int | None = None
            for script in scripts:
                row = self.script_list.count()
                QListWidgetItem(script.name, self.script_list)
                if preferred_script_path is not None and str(script.script_path) == preferred_script_path:
                    preferred_row = row
            if preferred_row is not None:
                self.script_list.setCurrentRow(preferred_row)
            elif self.script_list.count() > 0:
                self.script_list.setCurrentRow(0)
        finally:
            self.script_list.blockSignals(False)

    def current_script(self) -> CustomScriptRecord | None:
        row = self.script_list.currentRow()
        if row < 0 or row >= len(self._scripts):
            return None
        return self._scripts[row]

    def set_draft(
        self,
        name: str,
        content: str,
    ) -> None:
        if self.name_input.text() != name:
            self.name_input.setText(name)
        if self.editor.toPlainText() != content:
            self.editor.setPlainText(content)

    def draft_name(self) -> str:
        return self.name_input.text()

    def draft_content(self) -> str:
        return self.editor.toPlainText()

    def _emit_add_selected_requested(self) -> None:
        if self.on_add_selected_requested is not None:
            self.on_add_selected_requested()

    def _emit_save_requested(self) -> None:
        if self.on_save_requested is not None:
            self.on_save_requested()

    def _emit_selection_changed(self) -> None:
        if self.on_selection_changed is not None:
            self.on_selection_changed()
