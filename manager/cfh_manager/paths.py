"""Resolucao de caminhos do aplicativo (fonte e executavel empacotado)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import APP_ID

# Arquivos que compoem o self bot e precisam existir na pasta de trabalho.
SELFBOT_FILES = (
    "package.json",
    "index.js",
    "src/config.js",
    "src/logger.js",
    "src/client.js",
    "src/commands.js",
    "src/utils.js",
    ".env.example",
    "README.md",
)


def is_frozen() -> bool:
    """True quando o app roda a partir do .exe gerado pelo PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """Pasta de recursos empacotados (sys._MEIPASS) ou a pasta do codigo-fonte."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def app_dir() -> Path:
    """Pasta do executavel (ou do projeto, quando rodando do codigo-fonte)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """Raiz do repositorio (apenas quando executado do codigo-fonte)."""
    return Path(__file__).resolve().parent.parent.parent


def data_dir() -> Path:
    """Pasta de dados do usuario (config, logs, runtime, copia do self bot)."""
    override = os.environ.get("CFH_DATA_DIR")
    if override:
        path = Path(override).expanduser()
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        path = Path(base) / APP_ID
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir() -> Path:
    """Onde o Node.js portatil e instalado quando nao existe no sistema."""
    path = data_dir() / "runtime" / "node"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return data_dir() / "settings.json"


def is_selfbot_dir(path: Path) -> bool:
    """Confere se a pasta informada contem o self bot."""
    return (path / "package.json").is_file() and (path / "index.js").is_file()


def find_selfbot_dir() -> Path | None:
    """Localiza a pasta do self bot, na ordem: env -> ao lado do .exe -> repo -> dados."""
    candidates: list[Path] = []

    override = os.environ.get("CFH_SELFBOT_DIR")
    if override:
        candidates.append(Path(override).expanduser())

    candidates.append(app_dir() / "selfbot")  # modo portatil: .exe + pasta selfbot
    candidates.append(app_dir() / "selfbot-app")
    candidates.append(project_root() / "selfbot")  # rodando do codigo-fonte
    candidates.append(data_dir() / "selfbot")  # copia gerada a partir do pacote

    for candidate in candidates:
        try:
            if is_selfbot_dir(candidate):
                return candidate.resolve()
        except OSError:
            continue
    return None


def materialize_selfbot() -> Path:
    """Copia os arquivos do self bot empacotados para a pasta de dados.

    Usado quando o .exe e distribuido sozinho (sem a pasta ``selfbot`` ao lado).
    """
    source = bundle_dir() / "selfbot"
    target = data_dir() / "selfbot"
    target.mkdir(parents=True, exist_ok=True)

    if not source.is_dir():
        return target

    for relative in SELFBOT_FILES:
        origin = source / relative
        destination = target / relative
        if not origin.is_file():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or origin.stat().st_mtime > destination.stat().st_mtime:
            shutil.copy2(origin, destination)
    return target


def ensure_selfbot_dir() -> Path:
    """Garante que exista uma pasta do self bot pronta para uso."""
    found = find_selfbot_dir()
    if found is not None:
        return found
    return materialize_selfbot()


def bundled_selfbot_available() -> bool:
    return (bundle_dir() / "selfbot").is_dir()
