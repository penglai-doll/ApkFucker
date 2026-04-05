from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apk_hacker.domain.models.indexes import MethodIndexEntry


class MethodIndexWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._visible_methods: tuple[MethodIndexEntry, ...] = ()
        self.on_search_requested: Callable[[str], None] | None = None
        self.on_add_selected_requested: Callable[[], None] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Method Index"))

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search class, method, or type")
        self.search_button = QPushButton("Search")
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        self.method_list = QListWidget()
        layout.addWidget(self.method_list)

        self.add_selected_button = QPushButton("Add Selected To Plan")
        layout.addWidget(self.add_selected_button)
        layout.addStretch(1)

        self.search_button.clicked.connect(self.apply_search)
        self.search_input.returnPressed.connect(self.apply_search)
        self.add_selected_button.clicked.connect(self._emit_add_selected)

    def set_methods(
        self,
        methods: tuple[MethodIndexEntry, ...],
        preferred_method: MethodIndexEntry | None = None,
    ) -> None:
        self._visible_methods = methods
        self.method_list.clear()
        preferred_row: int | None = None
        for method in methods:
            row = self.method_list.count()
            QListWidgetItem(self._format_method(method), self.method_list)
            if preferred_method is not None and self._same_method(method, preferred_method):
                preferred_row = row
        if preferred_row is not None:
            self.method_list.setCurrentRow(preferred_row)
        elif self.method_list.count() > 0:
            self.method_list.setCurrentRow(0)

    def current_method(self) -> MethodIndexEntry | None:
        row = self.method_list.currentRow()
        if row < 0 or row >= len(self._visible_methods):
            return None
        return self._visible_methods[row]

    def apply_search(self) -> None:
        if self.on_search_requested is not None:
            self.on_search_requested(self.search_input.text())

    def _emit_add_selected(self) -> None:
        if self.on_add_selected_requested is not None:
            self.on_add_selected_requested()

    @staticmethod
    def _same_method(left: MethodIndexEntry, right: MethodIndexEntry) -> bool:
        return (
            left.class_name == right.class_name
            and left.method_name == right.method_name
            and left.parameter_types == right.parameter_types
            and left.source_path == right.source_path
        )

    @staticmethod
    def _format_method(method: MethodIndexEntry) -> str:
        params = ", ".join(method.parameter_types)
        line_hint = f":{method.line_hint}" if method.line_hint is not None else ""
        return f"{method.class_name}.{method.method_name}({params}) -> {method.return_type} [{method.source_path}{line_hint}]"
