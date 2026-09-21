"""Tema dark no estilo Fluent Design (WinUI) para o aplicativo."""

from __future__ import annotations

import os
import sys

from pathlib import Path

from PySide6.QtGui import QColor, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------- Paleta
COLORS = {
    "window": "#1F1F1F",
    "window_alt": "#191919",
    "surface": "#2B2B2B",
    "surface_hover": "#333333",
    "surface_pressed": "#262626",
    "control": "#2D2D2D",
    "control_hover": "#373737",
    "control_border": "#3F3F3F",
    "border": "#3A3A3A",
    "border_subtle": "#2F2F2F",
    "text": "#FFFFFF",
    "text_secondary": "#C7C7C7",
    "text_tertiary": "#9A9A9A",
    "text_disabled": "#6A6A6A",
    "accent": "#4CC2FF",
    "accent_hover": "#6ACFFF",
    "accent_pressed": "#3AA9E0",
    "accent_text": "#06131B",
    "success": "#6CCB5F",
    "warning": "#FFB900",
    "danger": "#FF6B6B",
    "danger_bg": "#442726",
    "danger_border": "#6E2B2B",
    "danger_hover": "#55302F",
    "info": "#8AB4F8",
}

FONT_STACK = '"Segoe UI Variable Text", "Segoe UI", "Inter", "DejaVu Sans", sans-serif'
MONO_STACK = '"Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", monospace'

# Icone de "marcado" usado no QSS (o caminho precisa ser absoluto).
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_CHECK_ICON_FILE = _ASSETS_DIR / "check.png"
CHECK_ICON = f'url("{_CHECK_ICON_FILE.as_posix()}")' if _CHECK_ICON_FILE.is_file() else "none"

STYLESHEET = f"""
* {{
    font-family: {FONT_STACK};
    font-size: 13px;
    outline: none;
}}

QWidget#Root {{
    background-color: {COLORS['window']};
}}

QWidget#HeaderBar {{
    background-color: {COLORS['window_alt']};
    border-bottom: 1px solid {COLORS['border_subtle']};
}}

QLabel#AppTitle {{
    font-size: 20px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QLabel#AppSubtitle {{
    font-size: 12px;
    color: {COLORS['text_tertiary']};
}}

QLabel#SectionTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {COLORS['text']};
}}

QLabel#SectionHint, QLabel#Muted {{
    color: {COLORS['text_tertiary']};
    font-size: 12px;
}}

QLabel#FieldLabel {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
    font-weight: 600;
}}

QLabel#Feedback {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

QLabel#MetricValue {{
    color: {COLORS['text']};
    font-weight: 600;
}}

QLabel#MetricLabel {{
    color: {COLORS['text_tertiary']};
    font-size: 11px;
    text-transform: uppercase;
}}

QLabel#Badge {{
    background-color: {COLORS['control']};
    border: 1px solid {COLORS['control_border']};
    border-radius: 10px;
    padding: 2px 10px;
    color: {COLORS['text_secondary']};
    font-size: 11px;
}}

QFrame#Card {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QFrame#Divider {{
    background-color: {COLORS['border_subtle']};
    max-height: 1px;
    border: none;
}}

/* ---------------------------------------------------------- Buttons */
QPushButton {{
    background-color: {COLORS['control']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['control_border']};
    border-radius: 6px;
    padding: 8px 18px;
    min-height: 20px;
}}

QPushButton:hover:!disabled {{
    background-color: {COLORS['control_hover']};
    border-color: #4A4A4A;
}}

QPushButton:pressed:!disabled {{
    background-color: {COLORS['surface_pressed']};
}}

QPushButton:disabled {{
    background-color: #262626;
    color: {COLORS['text_disabled']};
    border-color: #2E2E2E;
}}

QPushButton#AccentButton {{
    background-color: {COLORS['accent']};
    color: {COLORS['accent_text']};
    border: 1px solid {COLORS['accent']};
    font-weight: 600;
}}

QPushButton#AccentButton:hover:!disabled {{
    background-color: {COLORS['accent_hover']};
    border-color: {COLORS['accent_hover']};
}}

QPushButton#AccentButton:pressed:!disabled {{
    background-color: {COLORS['accent_pressed']};
}}

QPushButton#AccentButton:disabled {{
    background-color: #2E3B42;
    color: #5E7078;
    border-color: #2E3B42;
}}

QPushButton#DangerButton {{
    background-color: {COLORS['danger_bg']};
    border: 1px solid {COLORS['danger_border']};
    color: #FFC9C9;
}}

QPushButton#DangerButton:hover:!disabled {{
    background-color: {COLORS['danger_hover']};
}}

QPushButton#DangerButton:disabled {{
    background-color: #2A2323;
    border-color: #3A2E2E;
    color: #7A6666;
}}

QPushButton#GhostButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {COLORS['text_secondary']};
    padding: 6px 10px;
}}

QPushButton#GhostButton:hover:!disabled {{
    background-color: {COLORS['control']};
    border-color: {COLORS['control_border']};
}}

QPushButton#LinkButton {{
    background-color: transparent;
    border: none;
    color: {COLORS['accent']};
    padding: 2px 4px;
    text-align: left;
}}

QPushButton#LinkButton:hover {{
    color: {COLORS['accent_hover']};
    text-decoration: underline;
}}

/* -------------------------------------------------------- Line edits */
QLineEdit {{
    background-color: {COLORS['control']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['control_border']};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['accent_text']};
}}

QLineEdit:hover {{
    background-color: #313131;
}}

QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
    background-color: #2A2A2A;
}}

QLineEdit:disabled {{
    color: {COLORS['text_disabled']};
    background-color: #262626;
}}

/* --------------------------------------------------------- Checkbox */
QCheckBox {{
    color: {COLORS['text_secondary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid {COLORS['control_border']};
    background-color: {COLORS['control']};
}}

QCheckBox::indicator:hover {{
    background-color: {COLORS['control_hover']};
    border-color: #575757;
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
    image: {CHECK_ICON};
}}

QCheckBox::indicator:checked:hover {{
    background-color: {COLORS['accent_hover']};
    border-color: {COLORS['accent_hover']};
}}

/* ----------------------------------------------------- Progress bar */
QProgressBar {{
    background-color: {COLORS['control']};
    border: 1px solid {COLORS['control_border']};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 4px;
}}

/* ---------------------------------------------------------- Console */
QPlainTextEdit#Console, QTextEdit#Steps {{
    background-color: {COLORS['window_alt']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['accent_text']};
}}

/* ------------------------------------------------------- Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #4A4A4A;
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: #5C5C5C;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #4A4A4A;
    border-radius: 5px;
    min-width: 24px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0px;
}}

/* ----------------------------------------------------------- Outros */
QToolTip {{
    background-color: #2B2B2B;
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    padding: 6px 8px;
    border-radius: 4px;
}}

QStatusBar {{
    background-color: {COLORS['window_alt']};
    color: {COLORS['text_tertiary']};
    border-top: 1px solid {COLORS['border_subtle']};
}}
"""


def apply_theme(app: QApplication) -> None:
    """Aplica paleta, fonte e folha de estilo do tema dark."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["window"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["window_alt"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ToolTipText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["control"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.BrightText, QColor(COLORS["danger"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor(COLORS["accent_text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(COLORS["text_tertiary"]))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(COLORS["text_disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(COLORS["text_disabled"]))
    app.setPalette(palette)

    app.setStyleSheet(STYLESHEET)

    if sys.platform == "win32":
        _enable_dark_title_bar()
    elif "Segoe UI" not in QFontDatabase.families():
        # Fora do Windows mantemos a fonte padrao do sistema (usado em testes).
        pass


def _enable_dark_title_bar() -> None:
    """Ativa a barra de titulo escura nativa no Windows 10/11."""
    if os.name != "nt":
        return
    try:
        import ctypes

        from PySide6.QtWidgets import QWidget

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute  # type: ignore[attr-defined]

        def hook(widget: QWidget) -> None:
            hwnd = int(widget.winId())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined]
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
            )

        QApplication.instance()._cfh_dark_title_hook = hook  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - apenas Windows
        pass


def apply_dark_title_bar(widget) -> None:
    """Reaplica a barra escura em uma janela especifica (Windows)."""
    hook = getattr(QApplication.instance(), "_cfh_dark_title_hook", None)
    if callable(hook):
        try:
            hook(widget)
        except Exception:
            pass
