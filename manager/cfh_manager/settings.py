"""Persistencia de configuracoes, validacao de token e escrita do arquivo .env."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .paths import data_dir, ensure_selfbot_dir, settings_file

# Token de usuario do Discord: tres partes separadas por ponto.
TOKEN_REGEX = re.compile(r"^[\w-]{20,40}\.[\w-]{5,10}\.[\w-]{25,60}$")


def validate_token_format(token: str) -> tuple[bool, str]:
    """Valida apenas o formato do token (sem consultar o Discord)."""
    value = (token or "").strip()
    if not value:
        return False, "Informe o token da sua conta para continuar."
    if re.match(r"^Bot\s", value, flags=re.IGNORECASE):
        return False, 'Remova o prefixo "Bot " — ele é usado apenas em bots oficiais.'
    if len(value) < 50:
        return False, "Token muito curto — verifique se copiou o valor completo."
    if not TOKEN_REGEX.match(value):
        return False, "Formato inesperado. O token tem 3 partes separadas por ponto (a.b.c)."
    return True, "Formato do token válido."


def mask_token(token: str) -> str:
    value = (token or "").strip()
    if len(value) <= 14:
        return "***" if value else ""
    return f"{value[:8]}…{value[-6:]}"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class Settings:
    """Configuracoes persistentes do gerenciador."""

    token: str = ""
    token_applied: bool = False
    token_username: str = ""
    token_checked_at: str = ""
    environment_ready: bool = False
    node_path: str = ""
    node_version: str = ""
    npm_path: str = ""
    last_environment_check: str = ""
    managed_node_version: str = ""
    force_reinstall: bool = False
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ IO
    @classmethod
    def load(cls) -> "Settings":
        path = settings_file()
        if not path.is_file():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()

        known = {key: value for key, value in raw.items() if key in cls.__dataclass_fields__}
        settings = cls(**known)
        # Revalida o formato: um token corrompido nao deve habilitar o bot.
        if settings.token:
            ok, _ = validate_token_format(settings.token)
            if not ok:
                settings.token = ""
                settings.token_applied = False
        return settings

    def save(self) -> None:
        path = settings_file()
        payload = json.dumps(asdict(self), indent=2, ensure_ascii=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
        harden_file_permissions(path)

    # --------------------------------------------------------- Conveniencia
    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())

    @property
    def ready_to_run(self) -> bool:
        """Regra da interface: Iniciar Bot so libera com token + ambiente prontos."""
        return self.has_token and self.token_applied and self.environment_ready


def harden_file_permissions(path: Path) -> None:
    """Restringe o acesso ao arquivo (o token fica gravado nele)."""
    try:
        if os.name == "nt":
            user = os.environ.get("USERNAME")
            if not user:
                return
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                capture_output=True,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            path.chmod(0o600)
    except OSError:
        pass


def upsert_env_value(env_path: Path, key: str, value: str) -> None:
    """Cria/atualiza uma chave no arquivo .env preservando as demais linhas."""
    lines: list[str] = []
    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines()

    new_line = f"{key}={value}"
    replaced = False
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            name = stripped.split("=", 1)[0].strip()
            if name == key:
                output.append(new_line)
                replaced = True
                continue
        output.append(line)

    if not replaced:
        if output and output[-1].strip():
            output.append("")
        output.append(new_line)

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    harden_file_permissions(env_path)


def apply_token_to_env(token: str, selfbot_dir: Path | None = None) -> Path:
    """Grava o token no .env do self bot (usado ao iniciar o bot e ao aplicar o token)."""
    directory = selfbot_dir or ensure_selfbot_dir()
    env_path = directory / ".env"

    if not env_path.exists():
        template = directory / ".env.example"
        if template.is_file():
            env_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            env_path.write_text("", encoding="utf-8")

    upsert_env_value(env_path, "DISCORD_TOKEN", token.strip())
    return env_path


def env_token(env_path: Path) -> str:
    """Le o token gravado no .env (para conferir se esta sincronizado)."""
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("DISCORD_TOKEN="):
            return stripped.split("=", 1)[1].strip()
    return ""


def data_directory() -> Path:
    return data_dir()
