"""Threads de trabalho: validacao do token e preparacao do ambiente."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .paths import (
    bundled_selfbot_available,
    ensure_selfbot_dir,
    is_selfbot_dir,
    runtime_dir,
)
from .settings import apply_token_to_env

NODE_INDEX_URL = "https://nodejs.org/dist/index.json"
NODE_DIST_URL = "https://nodejs.org/dist/{version}/{filename}"
FALLBACK_NODE_VERSIONS = ("v22.14.0", "v20.18.1")
MIN_NODE_VERSION = (16, 6, 0)
RECOMMENDED_NODE_VERSION = (18, 0, 0)
USER_AGENT = "CaptureFruitHoHoHub-ControlHub/1.0 (+https://github.com/lukscode-py/CaptureFruitHoHoHub)"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _node_executable_name() -> str:
    return "node.exe" if os.name == "nt" else "node"


def _npm_executable_name() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def base_environment(extra_path: Path | None = None) -> dict:
    """Ambiente do processo com o Node portatil no PATH, quando existir."""
    env = os.environ.copy()
    env.setdefault("NPM_CONFIG_FUND", "false")
    env.setdefault("NPM_CONFIG_AUDIT", "false")
    if extra_path is not None:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"
    return env


def parse_node_version(output: str) -> tuple[int, ...]:
    """Converte 'v22.14.0' em (22, 14, 0)."""
    cleaned = output.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in cleaned.split("."):
        digits = "".join(char for char in chunk if char.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


class TokenWorker(QThread):
    """Confere o token na API do Discord (GET /users/@me)."""

    finished_check = Signal(str, str, str)  # status ('valid'|'invalid'|'offline'), mensagem, usuario

    def __init__(self, token: str, parent=None) -> None:
        super().__init__(parent)
        self.token = token.strip()

    def run(self) -> None:  # pragma: no cover - depende de rede
        request = urllib.request.Request(
            "https://discord.com/api/v9/users/@me",
            headers={
                "Authorization": self.token,
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            username = payload.get("username") or "conta"
            global_name = payload.get("global_name")
            label = f"{global_name or username}"
            discriminator = payload.get("discriminator")
            if discriminator and discriminator != "0":
                label += f"#{discriminator}"
            self.finished_check.emit("valid", label, payload.get("id") or "")
            return
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                self.finished_check.emit(
                    "invalid",
                    "Token recusado pelo Discord (401/403). Gere um token novo e tente novamente.",
                    "",
                )
            else:
                self.finished_check.emit("offline", f"Discord respondeu HTTP {error.code}.", "")
            return
        except Exception as error:  # noqa: BLE001 - rede, proxy, DNS, TLS...
            self.finished_check.emit(
                "offline",
                f"Não foi possível validar online ({type(error).__name__}). Token salvo localmente.",
                "",
            )


class EnvironmentWorker(QThread):
    """Verifica e instala tudo o que o self bot precisa (Node.js + dependencias)."""

    step = Signal(str, str, str, str)  # id, titulo, status, detalhe
    log = Signal(str, str)  # nivel, mensagem
    progress = Signal(int)  # 0-100 (ou -1 para indeterminado)
    finished_result = Signal(bool, str)  # sucesso, mensagem

    def __init__(self, token: str = "", force: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.token = (token or "").strip()
        self.force = force

        # Resultados expostos para a janela apos o termino.
        self.selfbot_dir: Path | None = None
        self.node_path: str = ""
        self.node_version: str = ""
        self.npm_path: str = ""
        self.installed_lib_version: str = ""

    # ------------------------------------------------------------- helpers
    def _emit_step(self, step_id: str, title: str, status: str, detail: str = "") -> None:
        self.step.emit(step_id, title, status, detail)

    def _run_stream(self, command: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
        """Executa um comando mostrando a saida linha a linha no painel de log."""
        self.log.emit("debug", f"$ {' '.join(str(part) for part in command)}")
        try:
            process = subprocess.Popen(
                [str(part) for part in command],
                cwd=str(cwd) if cwd else None,
                env=env or base_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=CREATE_NO_WINDOW,
            )
        except (OSError, ValueError) as error:
            self.log.emit("error", f"Falha ao executar o comando: {error}")
            return -1

        assert process.stdout is not None
        with process.stdout:
            for line in process.stdout:
                text = line.rstrip()
                if text:
                    self.log.emit("info", text)
        return process.wait()

    def _capture(self, command: list[str], env: dict | None = None) -> tuple[int, str]:
        try:
            completed = subprocess.run(
                [str(part) for part in command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env or base_environment(),
                stdin=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                check=False,
            )
        except (OSError, ValueError) as error:
            return -1, str(error)
        return completed.returncode, (completed.stdout or completed.stderr or "").strip()

    def _npm_command(self, *args: str) -> list[str]:
        """No Windows, npm e um .cmd e precisa ser chamado via cmd.exe."""
        npm = self.npm_path or _npm_executable_name()
        if os.name == "nt":
            comspec = os.environ.get("COMSPEC", "cmd.exe")
            return [comspec, "/d", "/c", npm, *args]
        return [npm, *args]

    # ------------------------------------------------------------ Node.js
    def _managed_node(self) -> Path | None:
        candidate = runtime_dir() / _node_executable_name()
        if candidate.is_file():
            return candidate
        nested = runtime_dir() / "bin" / _node_executable_name()
        return nested if nested.is_file() else None

    def _resolve_node(self) -> str:
        """Descobre o Node.js local (portatil ou instalado no sistema)."""
        managed = self._managed_node()
        if managed is not None:
            self.log.emit("info", f"Node.js portatil encontrado em {managed}")
            return str(managed)

        found = shutil.which("node")
        if found:
            self.log.emit("info", f"Node.js do sistema encontrado em {found}")
            return found
        return ""

    def _latest_lts_version(self) -> str | None:
        request = urllib.request.Request(NODE_INDEX_URL, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                releases = json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception as error:  # noqa: BLE001
            self.log.emit("warn", f"Não foi possível consultar a lista de versões do Node.js ({error}).")
            return None

        for release in releases:
            if release.get("lts"):
                return release.get("version")
        return releases[0].get("version") if releases else None

    def _download_file(self, url: str, destination: Path) -> bool:
        self.log.emit("info", f"Baixando {url}")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                chunk_size = 256 * 1024
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        self.progress.emit(int(downloaded * 100 / total))
                    else:
                        self.progress.emit(-1)
        except Exception as error:  # noqa: BLE001
            self.log.emit("error", f"Falha no download: {error}")
            return False
        return True

    def _extract_archive(self, archive: Path, destination: Path) -> bool:
        try:
            with tempfile.TemporaryDirectory(prefix="cfh-node-") as tmp:
                temp_path = Path(tmp)
                if archive.suffix == ".zip":
                    with zipfile.ZipFile(archive) as bundle:
                        bundle.extractall(temp_path)
                elif archive.suffix in (".xz", ".gz") or archive.name.endswith((".tar.xz", ".tar.gz")):
                    with tarfile.open(archive) as bundle:
                        bundle.extractall(temp_path)
                else:
                    self.log.emit("error", f"Formato de arquivo não suportado: {archive.name}")
                    return False

                roots = [item for item in temp_path.iterdir()]
                source = roots[0] if len(roots) == 1 and roots[0].is_dir() else temp_path

                destination.mkdir(parents=True, exist_ok=True)
                for item in source.iterdir():
                    target = destination / item.name
                    if target.exists():
                        if target.is_dir():
                            shutil.rmtree(target, ignore_errors=True)
                        else:
                            target.unlink(missing_ok=True)
                    shutil.move(str(item), str(target))
        except Exception as error:  # noqa: BLE001
            self.log.emit("error", f"Falha ao extrair o Node.js: {error}")
            return False
        return True

    def _install_node(self) -> str:
        """Baixa o Node.js (LTS) e instala em uma pasta de dados do usuario."""
        version = self._latest_lts_version()
        attempts = [version] if version else []
        attempts.extend(candidate for candidate in FALLBACK_NODE_VERSIONS if candidate not in attempts)

        arch = "arm64" if os.environ.get("PROCESSOR_ARCHITECTURE", "").lower().startswith("arm") else "x64"
        platform_name = "win" if os.name == "nt" else ("darwin" if sys.platform == "darwin" else "linux")
        extension = "zip" if platform_name == "win" else "tar.xz"

        downloads = runtime_dir().parent / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)

        for candidate in attempts:
            filename = f"node-{candidate}-{platform_name}-{arch}.{extension}"
            url = NODE_DIST_URL.format(version=candidate, filename=filename)
            archive = downloads / filename
            self.log.emit("info", f"Instalando Node.js {candidate} ({platform_name}-{arch})...")
            if archive.exists() and archive.stat().st_size > 1024:
                self.log.emit("debug", "Usando o instalador já baixado anteriormente.")
            elif not self._download_file(url, archive):
                continue
            self.progress.emit(-1)
            if not self._extract_archive(archive, runtime_dir()):
                continue
            node = runtime_dir() / _node_executable_name()
            if node.is_file():
                if os.name != "nt":
                    node.chmod(0o755)
                self.log.emit("info", f"Node.js {candidate} instalado em {runtime_dir()}")
                archive.unlink(missing_ok=True)
                return str(node)

        return ""

    def _resolve_npm(self, node_path: str) -> str:
        node_dir = Path(node_path).parent
        for candidate in (node_dir / _npm_executable_name(), node_dir / "npm", node_dir / "bin" / "npm"):
            if candidate.is_file():
                return str(candidate)
        found = shutil.which("npm")
        return found or ""

    # --------------------------------------------------------------- Fluxo
    def run(self) -> None:  # noqa: C901 - fluxo linear de verificacoes
        try:
            self._prepare()
        except Exception as error:  # noqa: BLE001
            self.log.emit("error", f"Erro inesperado durante a preparação: {error}")
            self._emit_step("done", "Preparar ambiente", "error", str(error))
            self.progress.emit(-1)
            self.finished_result.emit(False, str(error))

    def _prepare(self) -> None:
        self.progress.emit(-1)

        # 1) Pasta do self bot -------------------------------------------------
        step_id = "selfbot"
        self._emit_step(step_id, "Localizando arquivos do self bot", "running")
        directory = ensure_selfbot_dir()
        if not is_selfbot_dir(directory):
            detail = "pasta 'selfbot' não encontrada" if not bundled_selfbot_available() else "arquivos incompletos"
            self._emit_step(step_id, "Localizando arquivos do self bot", "error", detail)
            self.log.emit("error", "Não encontrei os arquivos do self bot para preparar.")
            self.finished_result.emit(False, "Arquivos do self bot não encontrados.")
            return
        self.selfbot_dir = directory
        self._emit_step(step_id, "Localizando arquivos do self bot", "ok", str(directory))
        self.log.emit("info", f"Pasta de trabalho: {directory}")

        # 2) package.json ------------------------------------------------------
        step_id = "package"
        self._emit_step(step_id, "Lendo package.json", "running")
        try:
            package = json.loads((directory / "package.json").read_text(encoding="utf-8"))
            dependency = package.get("dependencies", {}).get("discord.js-selfbot-v13", "?")
            self._emit_step(step_id, "Lendo package.json", "ok", f"discord.js-selfbot-v13 {dependency}")
        except Exception as error:  # noqa: BLE001
            self._emit_step(step_id, "Lendo package.json", "error", str(error))
            self.finished_result.emit(False, f"package.json inválido: {error}")
            return

        # 3) Node.js -----------------------------------------------------------
        step_id = "node"
        self._emit_step(step_id, "Verificando Node.js", "running")
        node_path = self._resolve_node()
        if not node_path:
            self.log.emit("warn", "Node.js não encontrado no sistema — instalando a versão portátil LTS.")
            self._emit_step(step_id, "Verificando Node.js", "warn", "não encontrado — baixando a versão LTS")
            node_path = self._install_node()
            if not node_path:
                self._emit_step(step_id, "Verificando Node.js", "error", "falha ao instalar automaticamente")
                self.finished_result.emit(
                    False,
                    "Node.js não encontrado e o download automático falhou. Verifique sua conexão.",
                )
                return
            self._emit_step(step_id, "Verificando Node.js", "ok", f"instalado automaticamente em {node_path}")
        else:
            self._emit_step(step_id, "Verificando Node.js", "ok", node_path)
        self.node_path = node_path

        # 4) Versao do Node ----------------------------------------------------
        step_id = "node_version"
        self._emit_step(step_id, "Verificando versão do Node.js", "running")
        env = base_environment(Path(node_path).parent)
        code, output = self._capture([node_path, "--version"], env=env)
        if code != 0:
            self._emit_step(step_id, "Verificando versão do Node.js", "error", output or "falha ao executar")
            self.finished_result.emit(False, "Não foi possível executar o Node.js.")
            return
        version = output.strip()
        self.node_version = version
        parsed = parse_node_version(version)
        if parsed < MIN_NODE_VERSION:
            detail = f"{version} (mínimo exigido: 16.6.0)"
            self._emit_step(step_id, "Verificando versão do Node.js", "error", detail)
            self.finished_result.emit(False, f"Node.js {version} é antigo demais. Atualize para 18+ (LTS).")
            return
        if parsed < RECOMMENDED_NODE_VERSION:
            self._emit_step(step_id, "Verificando versão do Node.js", "warn", f"{version} (recomendado: 18+)")
        else:
            self._emit_step(step_id, "Verificando versão do Node.js", "ok", version)

        # 5) npm ---------------------------------------------------------------
        step_id = "npm"
        self._emit_step(step_id, "Verificando npm", "running")
        npm_path = self._resolve_npm(node_path)
        if not npm_path:
            self._emit_step(step_id, "Verificando npm", "error", "npm não encontrado")
            self.finished_result.emit(False, "npm não encontrado. Reinstale o Node.js (o npm vem junto).")
            return
        self.npm_path = npm_path
        code, output = self._capture([npm_path, "--version"], env=env)
        detail = f"npm {output.strip()}" if code == 0 else npm_path
        self._emit_step(step_id, "Verificando npm", "ok", detail)

        # 6) Token / .env ------------------------------------------------------
        step_id = "env"
        if self.token:
            self._emit_step(step_id, "Escrevendo token no arquivo .env", "running")
            try:
                env_path = apply_token_to_env(self.token, directory)
                self._emit_step(step_id, "Escrevendo token no arquivo .env", "ok", str(env_path))
            except OSError as error:
                self._emit_step(step_id, "Escrevendo token no arquivo .env", "error", str(error))
                self.finished_result.emit(False, f"Falha ao gravar o .env: {error}")
                return
        else:
            self._emit_step(step_id, "Escrevendo token no arquivo .env", "warn", "token ainda não aplicado")

        # 7) Dependencias ------------------------------------------------------
        step_id = "deps"
        modules = directory / "node_modules"
        if self.force and modules.is_dir():
            self.log.emit("warn", "Removendo node_modules para reinstalação completa...")
            shutil.rmtree(modules, ignore_errors=True)

        self._emit_step(step_id, "Instalando dependências (npm install)", "running")
        args = ["install", "--no-fund", "--no-audit", "--loglevel", "notice"]
        if self.force:
            args.append("--force")
        code = self._run_stream(self._npm_command(*args), cwd=directory, env=env)
        if code != 0:
            self._emit_step(
                step_id,
                "Instalando dependências (npm install)",
                "error",
                f"npm terminou com código {code}",
            )
            self.finished_result.emit(False, "A instalação das dependências falhou. Veja o console de log.")
            return
        self._emit_step(step_id, "Instalando dependências (npm install)", "ok", "concluído")

        # 8) Conferindo a biblioteca principal ---------------------------------
        step_id = "deps_check"
        self._emit_step(step_id, "Conferindo discord.js-selfbot-v13", "running")
        lib_package = directory / "node_modules" / "discord.js-selfbot-v13" / "package.json"
        if not lib_package.is_file():
            self._emit_step(step_id, "Conferindo discord.js-selfbot-v13", "error", "não instalada")
            self.finished_result.emit(False, "A biblioteca discord.js-selfbot-v13 não foi instalada corretamente.")
            return
        try:
            installed = json.loads(lib_package.read_text(encoding="utf-8")).get("version", "?")
        except Exception:  # noqa: BLE001
            installed = "?"
        self.installed_lib_version = installed
        self._emit_step(step_id, "Conferindo discord.js-selfbot-v13", "ok", f"v{installed}")

        # 9) Pastas de log -----------------------------------------------------
        step_id = "folders"
        self._emit_step(step_id, "Preparando pastas de log", "running")
        (directory / "logs").mkdir(parents=True, exist_ok=True)
        self._emit_step(step_id, "Preparando pastas de log", "ok", str(directory / "logs"))

        # 10) Fim --------------------------------------------------------------
        self.progress.emit(100)
        self._emit_step("done", "Ambiente pronto", "ok", f"Node {version} • biblioteca v{installed}")
        self.finished_result.emit(True, "Ambiente preparado com sucesso.")
