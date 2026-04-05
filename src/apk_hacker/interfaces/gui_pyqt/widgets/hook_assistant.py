from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from apk_hacker.domain.models.hook_advice import HookRecommendation
from apk_hacker.domain.models.static_inputs import StaticInputs


class HookAssistantWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._recommendations: tuple[HookRecommendation, ...] = ()
        self.on_add_selected_requested: Callable[[], None] | None = None
        self.on_add_top_requested: Callable[[], None] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hook Assistant"))

        self.context_label = QLabel("Offline recommendations will appear after static analysis.")
        self.context_label.setWordWrap(True)
        self.context_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.context_label)

        self.recommendation_list = QListWidget()
        layout.addWidget(self.recommendation_list)

        self.add_selected_button = QPushButton("Add Selected Recommendation")
        self.add_top_button = QPushButton("Add Top Recommendations")
        layout.addWidget(self.add_selected_button)
        layout.addWidget(self.add_top_button)
        layout.addStretch(1)

        self.add_selected_button.clicked.connect(self._emit_add_selected)
        self.add_top_button.clicked.connect(self._emit_add_top)

    def set_context(self, static_inputs: StaticInputs | None) -> None:
        if static_inputs is None:
            self.context_label.setText("Offline recommendations will appear after static analysis.")
            return

        parts = [
            f"Package: {static_inputs.package_name}",
            f"Technical tags: {len(static_inputs.technical_tags)}",
            f"Permissions: {len(static_inputs.dangerous_permissions)}",
            f"Callback clues: {len(static_inputs.callback_endpoints) + len(static_inputs.callback_clues)}",
            f"Crypto signals: {len(static_inputs.crypto_signals)}",
        ]
        self.context_label.setText(" | ".join(parts))

    def set_recommendations(
        self,
        recommendations: tuple[HookRecommendation, ...],
        preferred_recommendation_id: str | None = None,
    ) -> None:
        self._recommendations = recommendations
        self.recommendation_list.clear()
        preferred_row: int | None = None

        for recommendation in recommendations:
            row = self.recommendation_list.count()
            QListWidgetItem(self._format_recommendation(recommendation), self.recommendation_list)
            if preferred_recommendation_id is not None and recommendation.recommendation_id == preferred_recommendation_id:
                preferred_row = row

        if preferred_row is not None:
            self.recommendation_list.setCurrentRow(preferred_row)
        elif self.recommendation_list.count() > 0:
            self.recommendation_list.setCurrentRow(0)

    def current_recommendation(self) -> HookRecommendation | None:
        row = self.recommendation_list.currentRow()
        if row < 0 or row >= len(self._recommendations):
            return None
        return self._recommendations[row]

    def top_recommendations(self, limit: int = 3) -> tuple[HookRecommendation, ...]:
        return self._recommendations[:limit]

    def _emit_add_selected(self) -> None:
        if self.on_add_selected_requested is not None:
            self.on_add_selected_requested()

    def _emit_add_top(self) -> None:
        if self.on_add_top_requested is not None:
            self.on_add_top_requested()

    @staticmethod
    def _format_recommendation(recommendation: HookRecommendation) -> str:
        method = recommendation.method
        if method is None:
            return f"{recommendation.title} [{recommendation.score}] {recommendation.reason}"
        params = ", ".join(method.parameter_types)
        return (
            f"{method.class_name}.{method.method_name}({params}) "
            f"[score={recommendation.score}] {recommendation.reason}"
        )
