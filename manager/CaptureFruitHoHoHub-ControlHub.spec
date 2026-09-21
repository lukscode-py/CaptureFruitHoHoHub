# -*- mode: python ; coding: utf-8 -*-
"""Arquivo de build do PyInstaller para o CaptureFruitHoHoHub Control Hub.

Uso:
    pyinstaller CaptureFruitHoHoHub-ControlHub.spec --noconfirm

Variaveis de ambiente:
    CFH_ONEFILE=1   gera um unico .exe (mais lento para abrir, ~60 MB)
                    sem a variavel, gera a pasta dist/ com o .exe + dependencias
"""

import os
import sys
from pathlib import Path

SPEC_DIR = Path(os.path.abspath(SPECPATH))
PROJECT_ROOT = SPEC_DIR.parent
SELFBOT_DIR = PROJECT_ROOT / "selfbot"
ASSETS_DIR = SPEC_DIR / "assets"

ONEFILE = os.environ.get("CFH_ONEFILE", "") == "1"
APP_NAME = "CaptureFruitHoHoHub-ControlHub"

# O codigo do self bot vai embutido: se o .exe for usado sozinho, o app copia
# esses arquivos para a pasta de dados do usuario antes de preparar o ambiente.
selfbot_files = [
    ("package.json", "selfbot"),
    ("index.js", "selfbot"),
    (".env.example", "selfbot"),
    ("README.md", "selfbot"),
    ("src/config.js", "selfbot/src"),
    ("src/logger.js", "selfbot/src"),
    ("src/client.js", "selfbot/src"),
    ("src/commands.js", "selfbot/src"),
    ("src/utils.js", "selfbot/src"),
]

datas = [(str(ASSETS_DIR), "assets")]
for relative, target in selfbot_files:
    source = SELFBOT_DIR / relative
    if source.is_file():
        datas.append((str(source), target))

# Modulos do Qt que o app nao usa (reduz bastante o tamanho final).
excludes = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras", "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic", "PySide6.Qt3DRender", "PySide6.QtBluetooth", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtLocation",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtNfc", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtPositioning",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSensors",
    "PySide6.QtSerialPort", "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtTest", "PySide6.QtTextToSpeech", "PySide6.QtWebChannel", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets",
    "shiboken6.Shiboken",
    "tkinter", "unittest", "pydoc", "doctest", "email", "http", "xmlrpc",
]

a = Analysis(
    ["app.py"],
    pathex=[str(SPEC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtSvg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    *([] if ONEFILE else [a.binaries, a.datas]),
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # aplicacao com interface grafica
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_DIR / "icon.ico") if (ASSETS_DIR / "icon.ico").is_file() else None,
    version=None,
)

if not ONEFILE:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
