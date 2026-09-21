"""Widgets reutilizaveis (cards, pilula de status, checklist e console)."""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..theme import COLORS

# Icones e cores por estado de etapa -------------------------------------------------
STEP_STYLE = {
    "pending": ("○", COLORS["text_tertiary"]),
    "running": ("◐", COLORS["warning"]),
    "ok": ("✓", COLORS["success"]),
    "warn": ("!", COLORS["warning"]),
    "error": ("✗", COLORS["danger"]),
}

LOG_STYLE = {
    "debug": ("debug", "#8A8A8A"),
    "info": ("info", COLORS["text_secondary"]),
    "warn": ("aviso", COLORS["warning"]),
    "error": ("erro", COLORS["danger"]),
    "success": ("ok", COLORS["success"]),
}


class Card(QFrame):
    """Cartao escuro com titulo, subtitulo e area de conteudo."""

    def __init__(self, title: str, hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 18)
        outer.setSpacing(10)

        header = QVBoxLayout()
        header.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionTitle")
        header.addWidget(self.title_label)

        if hint:
            self.hint_label = QLabel(hint)
            self.hint_label.setObjectName("SectionHint")
            self.hint_label.setWordWrap(True)
            header.addWidget(self.hint_label)

        outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body)

    def add_widget(self, widget: QWidget) -> None:
        self.body.addWidget(widget)

    def add_layout(self, layout) -> None:
        self.body.addLayout(layout)


class StatusPill(QWidget):
    """Pilula colorida que mostra o estado atual (Parado/Iniciando/Online/Erro)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusPill")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(8)

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        self.text = QLabel("Parado")
        self.text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")

        layout.addWidget(self.dot)
        layout.addWidget(self.text)
        self.set_state("Parado", COLORS["text_tertiary"], COLORS["text_secondary"])

    def set_state(self, label: str, dot_color: str, text_color: str | None = None) -> None:
        self.text.setText(label)
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 12px;")
        self.text.setStyleSheet(f"color: {text_color or dot_color}; font-weight: 600;")
        self.setStyleSheet(
            f"QWidget#StatusPill {{ background-color: rgba(255,255,255,0.06);"
            f" border: 1px solid {COLORS['border']}; border-radius: 14px; }}"
        )


class Metric(QWidget):
    """Pequeno bloco 'rotulo + valor' usado nos cartoes."""

    def __init__(self, label: str, value: str = "—", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self.label = QLabel(label.upper())
        self.label.setObjectName("MetricLabel")

        self.value = QLabel(value)
        self.value.setObjectName("MetricValue")
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str, color: str | None = None, tooltip: str | None = None) -> None:
        self.value.setText(value)
        self.value.setStyleSheet(f"color: {color};" if color else "")
        if tooltip:
            self.setToolTip(tooltip)


class StepsPanel(QTextEdit):
    """Checklist colorida com atualizacao em tempo real e scroll automatico."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Steps")
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(206)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._steps: list[dict] = []

    # ------------------------------------------------------------ API
    def reset(self, steps: list[tuple[str, str]]) -> None:
        """Define a lista de etapas (id, titulo) como 'pending'."""
        self._steps = [{"id": step_id, "title": title, "status": "pending", "detail": ""} for step_id, title in steps]
        self._render()

    def set_step(self, step_id: str, status: str, detail: str = "", title: str | None = None) -> None:
        for step in self._steps:
            if step["id"] == step_id:
                step["status"] = status
                step["detail"] = detail
                if title:
                    step["title"] = title
                break
        else:
            self._steps.append({"id": step_id, "title": title or step_id, "status": status, "detail": detail})
        self._render()

    def add_step(self, step_id: str, title: str, status: str = "pending", detail: str = "") -> None:
        self._steps.append({"id": step_id, "title": title, "status": status, "detail": detail})
        self._render()

    def clear_steps(self) -> None:
        self._steps = []
        self._render()

    # --------------------------------------------------------- render
    def _render(self) -> None:
        rows: list[str] = []
        for step in self._steps:
            icon, color = STEP_STYLE.get(step["status"], STEP_STYLE["pending"])
            title_color = COLORS["text"] if step["status"] != "pending" else COLORS["text_tertiary"]
            weight = "600" if step["status"] in ("running", "ok", "error", "warn") else "400"
            detail = html.escape(step["detail"]) if step["detail"] else ""
            detail_html = f'<span style="color:{COLORS["text_tertiary"]};"> — {detail}</span>' if detail else ""
            rows.append(
                '<div style="margin-bottom:3px;">'
                f'<span style="color:{color};font-weight:700;">{icon}</span>'
                f'&nbsp;&nbsp;<span style="color:{title_color};font-weight:{weight};">{html.escape(step["title"])}</span>'
                f"{detail_html}</div>"
            )
        if not rows:
            rows.append(f'<div style="color:{COLORS["text_tertiary"]};">Nenhuma verificação executada ainda.</div>')

        self.setHtml("".join(rows))
        self.moveCursor(QTextCursor.End)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class LogConsole(QPlainTextEdit):
    """Console de log com cores por nivel e rolagem automatica."""

    MAX_BLOCKS = 4000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Console")
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setMaximumBlockCount(self.MAX_BLOCKS)
        self.setMinimumHeight(170)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet(
            "QPlainTextEdit { font-family: 'Cascadia Mono', Consolas, 'DejaVu Sans Mono', monospace; }"
        )

    def append_line(self, level: str, message: str) -> None:
        label, color = LOG_STYLE.get(level, LOG_STYLE["info"])
        timestamp = datetime.now().strftime("%H:%M:%S")
        safe = html.escape(message).replace(" ", "&nbsp;")
        self.appendHtml(
            f'<span style="color:#6E6E6E;">[{timestamp}]</span> '
            f'<span style="color:{color};">{label:>5}</span> '
            f'<span style="color:{COLORS["text_secondary"]};">{safe}</span>'
        )
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
