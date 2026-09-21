"""Gerenciamento do processo do self bot (iniciar, monitorar e parar)."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from . import APP_NAME

STATE_STOPPED = "stopped"
STATE_STARTING = "starting"
STATE_ONLINE = "online"
STATE_ERROR = "error"

STATE_LABELS = {
    STATE_STOPPED: "Parado",
    STATE_STARTING: "Iniciando",
    STATE_ONLINE: "Online",
    STATE_ERROR: "Erro",
}

LOGIN_TIMEOUT_MS = 35_000
GRACEFUL_STOP_MS = 6_000


@dataclass
class BotInfo:
    """Informacoes recebidas do bot pelo protocolo de eventos."""

    user_id: str = ""
    username: str = ""
    tag: str = ""
    guilds: int = 0
    latency: int | None = None
    uptime: str = ""
    prefix: str = "!"
    started_at: datetime | None = None
    extra: dict = field(default_factory=dict)


class BotProcess(QObject):
    """Encapsula o QProcess que executa `node index.js`."""

    state_changed = Signal(str)  # STATE_* acima
    log = Signal(str, str)  # nivel, mensagem
    info_changed = Signal(object)  # BotInfo
    exited = Signal(int, str)  # codigo, motivo

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None
        self._state = STATE_STOPPED
        self._buffer = ""
        self._stopping = False
        self._exit_detail = ""

        self.info = BotInfo()

        self._login_timer = QTimer(self)
        self._login_timer.setSingleShot(True)
        self._login_timer.setInterval(LOGIN_TIMEOUT_MS)
        self._login_timer.timeout.connect(self._on_login_timeout)

        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.setInterval(GRACEFUL_STOP_MS)
        self._kill_timer.timeout.connect(self._force_kill)

    # ------------------------------------------------------------- estado
    @property
    def state(self) -> str:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def _set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.state_changed.emit(state)

    # ------------------------------------------------------------- inicio
    def start(self, selfbot_dir: Path, node_path: str) -> bool:
        """Inicia o self bot apontando para o Node.js informado."""
        if self.is_running:
            self.log.emit("warn", "O self bot já está em execução.")
            return False

        entry = selfbot_dir / "index.js"
        if not entry.is_file():
            self.log.emit("error", f"Arquivo não encontrado: {entry}")
            self._set_state(STATE_ERROR)
            return False

        if not node_path or not Path(node_path).exists():
            self.log.emit("error", "Node.js não encontrado. Execute 'Preparar Ambiente' novamente.")
            self._set_state(STATE_ERROR)
            return False

        self._buffer = ""
        self._stopping = False
        self._exit_detail = ""
        self.info = BotInfo(started_at=datetime.now())

        process = QProcess(self)
        process.setWorkingDirectory(str(selfbot_dir))
        process.setProcessChannelMode(QProcess.MergedChannels)

        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PATH", f"{Path(node_path).parent}{os.pathsep}{os.environ.get('PATH', '')}")
        environment.insert("CFH_MANAGED_BY", APP_NAME)
        environment.insert("NODE_NO_WARNINGS", "0")
        process.setProcessEnvironment(environment)

        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error_occurred)

        self._process = process
        self.log.emit("info", f"Executando: {node_path} index.js")
        self.log.emit("info", f"Diretório de trabalho: {selfbot_dir}")

        process.start(node_path, ["index.js"])
        if not process.waitForStarted(10_000):
            self.log.emit("error", "Não foi possível iniciar o processo do Node.js.")
            self._set_state(STATE_ERROR)
            self._process = None
            return False

        self._set_state(STATE_STARTING)
        self._login_timer.start()
        self.info_changed.emit(self.info)
        return True

    # --------------------------------------------------------------- stop
    def stop(self, reason: str = "solicitado pelo usuário") -> None:
        """Encerra o processo de forma limpa (com stop via stdin e kill como reserva)."""
        if not self.is_running or self._process is None:
            self._set_state(STATE_STOPPED)
            return

        self._stopping = True
        self._exit_detail = reason
        self.log.emit("info", "Encerrando o self bot...")

        try:
            # Comando cooperativo: o bot encerra a conexão e sai.
            self._process.write(b"stop\n")
            self._process.closeWriteChannel()
        except Exception:  # noqa: BLE001
            pass

        if os.name == "nt":
            self._taskkill(self._process.processId())
        else:
            self._process.terminate()

        self._kill_timer.start()

    def _force_kill(self) -> None:
        if self._process is None or not self.is_running:
            return
        self.log.emit("warn", "O self bot não encerrou a tempo — forçando o término do processo.")
        if os.name == "nt":
            self._taskkill(self._process.processId(), force=True)
        else:
            self._process.kill()

    @staticmethod
    def _taskkill(pid: int, force: bool = False) -> None:
        """Encerra a árvore de processos no Windows (node.cmd -> node.exe)."""
        if not pid:
            return
        command = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            command.append("/F")
        try:
            subprocess.run(
                command,
                capture_output=True,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            pass

    # -------------------------------------------------------------- saida
    def _read_output(self) -> None:
        if self._process is None:
            return
        raw = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._buffer += raw

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._handle_line(line.rstrip("\r"))

    def _handle_line(self, line: str) -> None:
        text = line.strip()
        if not text:
            return

        if text.startswith("{") and '"cfh"' in text:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                self.log.emit("info", text)
                return
            self._handle_event(payload)
            return

        level = "info"
        if "[ERROR]" in text or "ERR!" in text:
            level = "error"
        elif "[WARN " in text or "WARN" in text:
            level = "warn"
        elif "[DEBUG]" in text:
            level = "debug"
        self.log.emit(level, text)

    def _handle_event(self, payload: dict) -> None:
        event = payload.get("event", "")
        if event == "ready":
            self.info.user_id = str(payload.get("id", ""))
            self.info.username = str(payload.get("username", ""))
            self.info.tag = str(payload.get("tag", self.info.username))
            self.info.guilds = int(payload.get("guilds", 0) or 0)
            self.info.latency = int(payload.get("latency", 0) or 0)
            self.info.prefix = str(payload.get("prefix", "!"))
            self._login_timer.stop()
            self._set_state(STATE_ONLINE)
            self.info_changed.emit(self.info)
            return

        if event == "heartbeat":
            if payload.get("latency") is not None:
                self.info.latency = int(payload["latency"])
            if payload.get("guilds") is not None:
                self.info.guilds = int(payload["guilds"])
            if payload.get("uptime"):
                self.info.uptime = str(payload["uptime"])
            self.info_changed.emit(self.info)
            return

        if event == "status":
            self.info.uptime = str(payload.get("uptime", self.info.uptime))
            if payload.get("latency") is not None:
                self.info.latency = int(payload["latency"])
            self.info_changed.emit(self.info)
            return

        if event == "presence":
            self.info.extra.update(payload)
            self.info_changed.emit(self.info)
            return

        if event == "error":
            scope = payload.get("scope", "bot")
            message = payload.get("message", "erro desconhecido")
            self.log.emit("error", f"[{scope}] {message}")
            if payload.get("code") == "TOKEN_INVALID":
                self._exit_detail = "Token inválido — aplique um token novo."
            return

        if event == "command":
            self.log.emit("debug", f"Comando executado: {payload.get('name')}")
            return

        if event == "starting":
            self.log.emit("debug", f"Node {payload.get('node')} • pid {payload.get('pid')}")
            return

        if event == "exit":
            self._exit_detail = str(payload.get("reason", self._exit_detail))
            return

        if event in ("disconnect", "resume", "warn"):
            self.log.emit("warn", f"{event}: {payload.get('message') or payload.get('scope') or ''}".strip())
            return

        self.log.emit("debug", f"Evento: {event}")

    def _on_login_timeout(self) -> None:
        if self._state != STATE_STARTING:
            return
        self.log.emit(
            "error",
            "O Discord não confirmou a conexão em 35 segundos. Verifique o token e a conexão com a internet.",
        )
        self._exit_detail = "Sem resposta do Discord (token ou rede)."
        self._set_state(STATE_ERROR)

    def _on_error_occurred(self, error: QProcess.ProcessError) -> None:
        names = {
            QProcess.FailedToStart: "o processo não pôde ser iniciado",
            QProcess.Crashed: "o processo travou",
            QProcess.Timedout: "tempo esgotado",
            QProcess.WriteError: "erro de escrita",
            QProcess.ReadError: "erro de leitura",
            QProcess.UnknownError: "erro desconhecido",
        }
        self.log.emit("error", f"Falha no processo do self bot: {names.get(error, error)}")
        self._set_state(STATE_ERROR)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._login_timer.stop()
        self._kill_timer.stop()
        # Libera a referencia antes de notificar a interface, para que os botoes
        # sejam atualizados com o estado correto (processo ja encerrado).
        self._process = None

        crashed = exit_status == QProcess.CrashExit
        was_online = self._state == STATE_ONLINE

        if self._stopping:
            self.log.emit("info", "Self bot parado.")
            self._set_state(STATE_STOPPED)
            detail = self._exit_detail or "parado pelo usuário"
        elif was_online:
            self.log.emit("warn", f"O self bot foi encerrado (código {exit_code}).")
            self._set_state(STATE_STOPPED)
            detail = f"encerrado (código {exit_code})"
        else:
            hints = {
                2: "token ausente ou inválido no .env",
                3: "token recusado pelo Discord",
                4: "falha de rede ao conectar no Discord",
            }
            hint = hints.get(exit_code)
            message = "O self bot terminou antes de conectar"
            if hint:
                message += f" — {hint}"
            if crashed:
                message += " (processo interrompido)"
            self.log.emit("error", f"{message}.")
            self._set_state(STATE_ERROR)
            detail = self._exit_detail or hint or f"código {exit_code}"

        self.exited.emit(exit_code, detail)
        self._stopping = False
