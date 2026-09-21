"""CaptureFruitHoHoHub Control Hub — ponto de entrada do aplicativo.

Uso:
    python app.py            (executar a partir do codigo-fonte)
    CaptureFruitHoHoHub-ControlHub.exe   (versao compilada com PyInstaller)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Permite executar "python app.py" de dentro da pasta manager/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from cfh_manager import APP_ID, APP_NAME, APP_VERSION  # noqa: E402
from cfh_manager.theme import apply_theme  # noqa: E402
from cfh_manager.ui.main_window import MainWindow  # noqa: E402


def _set_windows_app_id() -> None:
    """Agrupa a janela corretamente na barra de tarefas do Windows."""
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass


def main() -> int:
    _set_windows_app_id()

    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName("CaptureFruitHoHoHub")
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    apply_theme(app)

    try:
        window = MainWindow()
    except Exception as error:  # noqa: BLE001
        QMessageBox.critical(
            None,
            "Falha ao iniciar",
            f"Não foi possível abrir o CaptureFruitHoHoHub Control Hub:\n\n{error}",
        )
        return 1

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
