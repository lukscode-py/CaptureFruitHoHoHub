"""Janela principal do CaptureFruitHoHoHub Control Hub."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION, REPOSITORY_URL
from ..bot_process import (
    STATE_ERROR,
    STATE_ONLINE,
    STATE_STARTING,
    STATE_STOPPED,
    BotProcess,
)
from ..paths import app_dir, data_dir, ensure_selfbot_dir, logs_dir, runtime_dir
from ..settings import Settings, apply_token_to_env, mask_token, validate_token_format
from ..theme import COLORS, apply_dark_title_bar
from ..workers import EnvironmentWorker, TokenWorker
from .widgets import Card, LogConsole, Metric, StatusPill, StepsPanel

STEPS: list[tuple[str, str]] = [
    ("selfbot", "Localizando arquivos do self bot"),
    ("package", "Lendo package.json"),
    ("node", "Verificando Node.js"),
    ("node_version", "Verificando versão do Node.js"),
    ("npm", "Verificando npm"),
    ("env", "Escrevendo token no arquivo .env"),
    ("deps", "Instalando dependências (npm install)"),
    ("deps_check", "Conferindo discord.js-selfbot-v13"),
    ("folders", "Preparando pastas de log"),
    ("done", "Ambiente pronto"),
]

PILL_STATES = {
    STATE_STOPPED: ("Parado", COLORS["text_tertiary"]),
    STATE_STARTING: ("Iniciando", COLORS["warning"]),
    STATE_ONLINE: ("Online", COLORS["success"]),
    STATE_ERROR: ("Erro", COLORS["danger"]),
}


class MainWindow(QMainWindow):
    """Interface unica com token, preparo de ambiente, status e execucao."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Self Bot Manager")
        self.resize(1060, 980)
        self.setMinimumSize(900, 700)

        self.settings = Settings.load()
        self.selfbot_dir: Path = ensure_selfbot_dir()
        self.env_worker: EnvironmentWorker | None = None
        self.token_worker: TokenWorker | None = None
        self.bot = BotProcess(self)

        self.log_file = logs_dir() / f"manager-{datetime.now():%Y-%m-%d}.log"

        self._build_ui()
        self._wire_bot()
        self._restore_state()
        self._log("info", f"{APP_NAME} v{APP_VERSION} iniciado.")
        self._log("info", f"Pasta do self bot: {self.selfbot_dir}")
        self._log("info", f"Pasta de dados: {data_dir()}")

    # ================================================================ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        content = QWidget()
        content.setObjectName("Root")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 14, 18, 12)
        content_layout.setSpacing(10)

        content_layout.addWidget(self._build_token_card())
        content_layout.addWidget(self._build_environment_card())
        content_layout.addWidget(self._build_steps_card())
        self.execution_card = self._build_execution_card()
        content_layout.addWidget(self.execution_card, stretch=1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidget(content)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; }")
        layout.addWidget(self.scroll_area, stretch=1)
        layout.addWidget(self._build_footer())

        icon_path = app_dir() / "assets" / "icon.ico"
        if not icon_path.is_file():
            icon_path = app_dir() / "assets" / "icon.png"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(74)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(14)

        logo_path = app_dir() / "assets" / "icon.png"
        if logo_path.is_file():
            from PySide6.QtGui import QPixmap

            logo = QLabel()
            logo.setPixmap(
                QPixmap(str(logo_path)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            layout.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("CaptureFruitHoHoHub")
        title.setObjectName("AppTitle")
        subtitle = QLabel(f"Control Hub v{APP_VERSION} · gerenciador de self bot (discord.js-selfbot-v13)")
        subtitle.setObjectName("AppSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        layout.addLayout(titles)
        layout.addStretch(1)

        self.pill = StatusPill()
        layout.addWidget(self.pill)
        return header

    # --------------------------------------------------------- cartao 1
    def _build_token_card(self) -> Card:
        card = Card(
            "1 · Token do self bot",
            "Cole o token da sua conta. Ele fica salvo apenas neste computador, no arquivo .env do self bot.",
        )

        row = QHBoxLayout()
        row.setSpacing(10)

        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("Cole aqui o token da sua conta (ex.: MTA1…Gx9k.Qk2p…7f)")
        self.token_input.setClearButtonEnabled(True)
        self.token_input.returnPressed.connect(self._apply_token)
        row.addWidget(self.token_input, stretch=1)

        self.reveal_button = QPushButton("Mostrar")
        self.reveal_button.setObjectName("GhostButton")
        self.reveal_button.setCheckable(True)
        self.reveal_button.setCursor(Qt.PointingHandCursor)
        self.reveal_button.toggled.connect(self._toggle_token_visibility)
        row.addWidget(self.reveal_button)

        self.apply_button = QPushButton("Aplicar Token")
        self.apply_button.setObjectName("AccentButton")
        self.apply_button.setCursor(Qt.PointingHandCursor)
        self.apply_button.setMinimumWidth(150)
        self.apply_button.clicked.connect(self._apply_token)
        row.addWidget(self.apply_button)

        card.add_layout(row)

        self.token_feedback = QLabel("Nenhum token aplicado até o momento.")
        self.token_feedback.setObjectName("Feedback")
        self.token_feedback.setWordWrap(True)
        card.add_widget(self.token_feedback)
        return card

    # --------------------------------------------------------- cartao 2
    def _build_environment_card(self) -> Card:
        card = Card(
            "2 · Preparar ambiente",
            "Verifica e instala automaticamente o Node.js (se necessário) e as dependências do self bot.",
        )

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(28)
        metrics.setVerticalSpacing(10)

        self.metric_node = Metric("Node.js", "verificando…")
        self.metric_npm = Metric("npm", "—")
        self.metric_library = Metric("discord.js-selfbot-v13", "—")
        self.metric_folder = Metric("Pasta do self bot", "—")

        metrics.addWidget(self.metric_node, 0, 0)
        metrics.addWidget(self.metric_npm, 0, 1)
        metrics.addWidget(self.metric_library, 0, 2)
        metrics.addWidget(self.metric_folder, 0, 3)
        metrics.setColumnStretch(3, 1)
        card.add_layout(metrics)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.HLine)
        card.add_widget(divider)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.prepare_button = QPushButton("Preparar Ambiente")
        self.prepare_button.setObjectName("AccentButton")
        self.prepare_button.setCursor(Qt.PointingHandCursor)
        self.prepare_button.setMinimumWidth(190)
        self.prepare_button.clicked.connect(self._prepare_environment)
        row.addWidget(self.prepare_button)

        self.force_checkbox = QCheckBox("Forçar reinstalação das dependências")
        self.force_checkbox.setChecked(self.settings.force_reinstall)
        row.addWidget(self.force_checkbox)
        row.addStretch(1)

        card.add_layout(row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        card.add_widget(self.progress)
        return card

    # --------------------------------------------------------- cartao 3
    def _build_steps_card(self) -> Card:
        card = Card("3 · Status da instalação", "Cada etapa é atualizada em tempo real durante o preparo do ambiente.")
        self.steps_panel = StepsPanel()
        self.steps_panel.reset(STEPS)
        for step_id, _ in STEPS:
            self.steps_panel.set_step(step_id, "pending")
        card.add_widget(self.steps_panel)
        return card

    # --------------------------------------------------------- cartao 4
    def _build_execution_card(self) -> Card:
        card = Card("4 · Execução", "O bot só pode ser iniciado com o token aplicado e o ambiente preparado.")

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(28)
        metrics.setVerticalSpacing(10)
        self.metric_user = Metric("Conta conectada", "—")
        self.metric_guilds = Metric("Servidores", "—")
        self.metric_latency = Metric("Latência", "—")
        self.metric_uptime = Metric("Tempo online", "—")
        metrics.addWidget(self.metric_user, 0, 0)
        metrics.addWidget(self.metric_guilds, 0, 1)
        metrics.addWidget(self.metric_latency, 0, 2)
        metrics.addWidget(self.metric_uptime, 0, 3)
        metrics.setColumnStretch(3, 1)
        card.add_layout(metrics)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.start_button = QPushButton("Iniciar Bot")
        self.start_button.setObjectName("AccentButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumWidth(150)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start_bot)
        row.addWidget(self.start_button)

        self.stop_button = QPushButton("Parar Bot")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setMinimumWidth(130)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop_bot)
        row.addWidget(self.stop_button)

        self.bot_status_label = QLabel("Parado")
        self.bot_status_label.setObjectName("Feedback")
        row.addWidget(self.bot_status_label)
        row.addStretch(1)

        self.clear_log_button = QPushButton("Limpar console")
        self.clear_log_button.setObjectName("GhostButton")
        self.clear_log_button.setCursor(Qt.PointingHandCursor)
        self.clear_log_button.clicked.connect(lambda: self.console.clear())
        row.addWidget(self.clear_log_button)

        self.open_logs_button = QPushButton("Abrir logs")
        self.open_logs_button.setObjectName("GhostButton")
        self.open_logs_button.setCursor(Qt.PointingHandCursor)
        self.open_logs_button.clicked.connect(lambda: self._open_path(logs_dir()))
        row.addWidget(self.open_logs_button)

        card.add_layout(row)

        self.console = LogConsole()
        self.console.setMinimumHeight(190)
        card.add_widget(self.console)
        return card

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("HeaderBar")
        footer.setFixedHeight(42)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 6, 20, 6)
        layout.setSpacing(14)

        hint = QLabel("Self bot é uma automação de conta pessoal — use com responsabilidade.")
        hint.setObjectName("Muted")
        layout.addWidget(hint)
        layout.addStretch(1)

        data_button = QPushButton("Abrir pasta de dados")
        data_button.setObjectName("LinkButton")
        data_button.setCursor(Qt.PointingHandCursor)
        data_button.clicked.connect(lambda: self._open_path(data_dir()))
        layout.addWidget(data_button)

        repo_button = QPushButton("Repositório")
        repo_button.setObjectName("LinkButton")
        repo_button.setCursor(Qt.PointingHandCursor)
        repo_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL)))
        layout.addWidget(repo_button)
        return footer

    # ============================================================== wiring
    def _wire_bot(self) -> None:
        self.bot.state_changed.connect(self._on_bot_state)
        self.bot.log.connect(self._on_bot_log)
        self.bot.info_changed.connect(self._on_bot_info)
        self.bot.exited.connect(self._on_bot_exited)

    def _restore_state(self) -> None:
        """Reaplica o estado salvo (token, ambiente, execucao)."""
        if self.settings.token:
            self.token_input.setText(self.settings.token)
            username = self.settings.token_username or "token salvo"
            self._set_feedback("success", f"Token aplicado anteriormente — {username} ({mask_token(self.settings.token)}).")

        self.metric_folder.set_value(self.selfbot_dir.name, tooltip=str(self.selfbot_dir))

        if self.settings.node_version:
            self.metric_node.set_value(f"{self.settings.node_version}")
        if self.settings.npm_path:
            self.metric_npm.set_value("disponível")
        if self.settings.environment_ready:
            self._log("info", "Ambiente marcado como pronto no último uso.")
            self.steps_panel.set_step("done", "ok", "pronto (verificado anteriormente)")
        else:
            self._log("warn", "Ambiente ainda não preparado. Clique em 'Preparar Ambiente'.")

        self._update_action_buttons()

    # ============================================================== token
    def _toggle_token_visibility(self, visible: bool) -> None:
        self.token_input.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.reveal_button.setText("Ocultar" if visible else "Mostrar")

    def _apply_token(self) -> None:
        token = self.token_input.text().strip()
        ok, message = validate_token_format(token)
        if not ok:
            self._set_feedback("error", message)
            self._log("error", f"Token rejeitado: {message}")
            self.settings.token_applied = False
            self._update_action_buttons()
            return

        self.apply_button.setEnabled(False)
        self.apply_button.setText("Validando…")
        self._set_feedback("warning", "Validando o token com o Discord…")
        self._log("info", f"Aplicando token {mask_token(token)}…")

        self.token_worker = TokenWorker(token, self)
        self.token_worker.finished_check.connect(self._on_token_checked)
        self.token_worker.start()

    def _on_token_checked(self, status: str, message: str, user_id: str) -> None:
        token = self.token_input.text().strip()
        self.apply_button.setEnabled(True)
        self.apply_button.setText("Aplicar Token")

        if status == "invalid":
            self.settings.token = ""
            self.settings.token_applied = False
            self.settings.token_username = ""
            self.settings.save()
            self._set_feedback("error", f"Token inválido — {message}")
            self._log("error", f"Token inválido: {message}")
            self._update_action_buttons()
            return

        self.settings.token = token
        self.settings.token_applied = True
        self.settings.token_username = message if status == "valid" else ""
        self.settings.token_checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.settings.save()

        try:
            env_path = apply_token_to_env(token, self.selfbot_dir)
            self._log("info", f"Token gravado em {env_path}")
        except OSError as error:
            self._log("error", f"Falha ao gravar o .env: {error}")

        if status == "valid":
            self._set_feedback("success", f"Token aplicado com sucesso — conectado como {message}.")
            self._log("success", f"Token validado pelo Discord: {message} (id {user_id}).")
        else:
            self._set_feedback("warning", f"Token salvo, mas não validado online ({message})")
            self._log("warn", f"Validação online indisponível: {message}")

        self._update_action_buttons()

    def _set_feedback(self, level: str, message: str) -> None:
        colors = {
            "success": COLORS["success"],
            "error": COLORS["danger"],
            "warning": COLORS["warning"],
            "info": COLORS["text_secondary"],
        }
        icons = {"success": "✓ ", "error": "✗ ", "warning": "! ", "info": ""}
        self.token_feedback.setStyleSheet(f"color: {colors.get(level, COLORS['text_secondary'])};")
        self.token_feedback.setText(f"{icons.get(level, '')}{message}")

    # ========================================================== ambiente
    def _prepare_environment(self) -> None:
        if self.env_worker is not None and self.env_worker.isRunning():
            self._log("warn", "O preparo do ambiente já está em andamento.")
            return

        self.prepare_button.setEnabled(False)
        self.prepare_button.setText("Preparando…")
        self.force_checkbox.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # indeterminado
        self.steps_panel.reset(STEPS)
        self._log("info", "Iniciando verificação e preparo do ambiente…")

        token = self.token_input.text().strip() if self.settings.token_applied else self.settings.token
        self.env_worker = EnvironmentWorker(token=token, force=self.force_checkbox.isChecked(), parent=self)
        self.env_worker.step.connect(self._on_env_step)
        self.env_worker.log.connect(self._on_env_log)
        self.env_worker.progress.connect(self._on_env_progress)
        self.env_worker.finished_result.connect(self._on_env_finished)
        self.env_worker.start()

    def _on_env_step(self, step_id: str, title: str, status: str, detail: str) -> None:
        self.steps_panel.set_step(step_id, status, detail, title)
        if status == "running":
            self._log("info", f"{title}…")
        elif status == "ok":
            self._log("success", f"{title}: {detail or 'ok'}")
        elif status == "warn":
            self._log("warn", f"{title}: {detail or 'atenção'}")
        elif status == "error":
            self._log("error", f"{title}: {detail or 'falhou'}")

    def _on_env_log(self, level: str, message: str) -> None:
        self._log(level, message)

    def _on_env_progress(self, value: int) -> None:
        if value < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(value)

    def _on_env_finished(self, success: bool, message: str) -> None:
        worker = self.env_worker
        self.prepare_button.setEnabled(True)
        self.prepare_button.setText("Preparar Ambiente")
        self.force_checkbox.setEnabled(True)

        if worker is not None:
            if worker.node_path:
                self.settings.node_path = worker.node_path
            if worker.node_version:
                self.settings.node_version = worker.node_version
                color = COLORS["success"]
                self.metric_node.set_value(worker.node_version, color=color)
            if worker.npm_path:
                self.settings.npm_path = worker.npm_path
                self.metric_npm.set_value("disponível", color=COLORS["success"])
            if worker.installed_lib_version:
                self.metric_library.set_value(f"v{worker.installed_lib_version}", color=COLORS["success"])
            if worker.selfbot_dir:
                self.selfbot_dir = worker.selfbot_dir
                self.metric_folder.set_value(worker.selfbot_dir.name, tooltip=str(worker.selfbot_dir))

        self.settings.environment_ready = bool(success)
        self.settings.last_environment_check = datetime.now().astimezone().isoformat(timespec="seconds")
        self.settings.force_reinstall = self.force_checkbox.isChecked()
        self.settings.save()

        if success:
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self.progress.setVisible(False)
            self._log("success", "Ambiente preparado com sucesso. Você já pode iniciar o bot.")
        else:
            self.progress.setVisible(False)
            self._log("error", f"Falha ao preparar o ambiente: {message}")
            if self.isVisible():
                QMessageBox.warning(
                    self,
                    "Falha ao preparar o ambiente",
                    f"{message}\n\nConfira o painel de status e o console de log para mais detalhes.",
                )

        self.env_worker = None
        self._update_action_buttons()

    # ========================================================== execucao
    def _resolve_node_for_run(self) -> str:
        """Garante um caminho valido do Node.js antes de iniciar o bot."""
        for candidate in (self.settings.node_path, shutil.which("node") or ""):
            if candidate and Path(candidate).is_file():
                return candidate
        managed = runtime_dir() / ("node.exe" if os.name == "nt" else "node")
        return str(managed) if managed.is_file() else ""

    def _start_bot(self) -> None:
        if not self.settings.ready_to_run:
            missing = []
            if not (self.settings.has_token and self.settings.token_applied):
                missing.append("aplicar o token")
            if not self.settings.environment_ready:
                missing.append("preparar o ambiente")
            self._log("warn", f"Antes de iniciar o bot é preciso: {' e '.join(missing)}.")
            return

        node_path = self._resolve_node_for_run()
        if not node_path:
            self._log("error", "Node.js não encontrado — execute 'Preparar Ambiente' novamente.")
            self.settings.environment_ready = False
            self.settings.save()
            self._update_action_buttons()
            return

        # Mantem o .env sempre sincronizado com o token aplicado.
        try:
            apply_token_to_env(self.settings.token, self.selfbot_dir)
        except OSError as error:
            self._log("error", f"Não foi possível atualizar o .env: {error}")

        if self.bot.start(self.selfbot_dir, node_path):
            self._log("info", "Iniciando o self bot…")
            self._update_action_buttons()

    def _stop_bot(self) -> None:
        if not self.bot.is_running:
            self._log("warn", "O self bot não está em execução.")
            return
        self.bot.stop()
        self._update_action_buttons()

    def _on_bot_state(self, state: str) -> None:
        label, color = PILL_STATES.get(state, PILL_STATES[STATE_STOPPED])
        self.pill.set_state(label, color)
        self.bot_status_label.setText(label)
        self.bot_status_label.setStyleSheet(f"color: {color}; font-weight: 600;")
        self._update_action_buttons()

        if state in (STATE_STARTING, STATE_ONLINE, STATE_ERROR):
            # Mantem a area de execucao/comando visivel quando o bot muda de estado.
            self.scroll_area.ensureWidgetVisible(self.execution_card, 0, 0)

        if state == STATE_ONLINE:
            self._log("success", "Self bot online! Use os comandos no Discord com o prefixo configurado.")
        elif state == STATE_ERROR:
            self._log("error", "O self bot entrou em estado de erro.")

    def _on_bot_log(self, level: str, message: str) -> None:
        self._log(level, message, prefix="bot")

    def _on_bot_info(self, info) -> None:
        self.metric_user.set_value(info.tag or (info.username or "—"), color=COLORS["success"] if info.username else None)
        self.metric_guilds.set_value(str(info.guilds) if info.username else "—")
        self.metric_latency.set_value(f"{info.latency} ms" if info.latency is not None else "—")
        if info.uptime:
            self.metric_uptime.set_value(info.uptime)
        elif info.started_at:
            delta = datetime.now() - info.started_at
            self.metric_uptime.set_value(str(delta).split(".")[0])
        if info.prefix:
            self.metric_user.setToolTip(f"Prefixo dos comandos: {info.prefix}")

    def _on_bot_exited(self, exit_code: int, detail: str) -> None:
        self._log("info", f"Processo finalizado (código {exit_code}) — {detail}")
        self.metric_latency.set_value("—")
        self.metric_guilds.set_value("—")
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        ready = self.settings.ready_to_run
        running = self.bot.is_running
        busy = self.env_worker is not None and self.env_worker.isRunning()

        self.start_button.setEnabled(ready and not running and not busy)
        self.stop_button.setEnabled(running)
        self.prepare_button.setEnabled(not busy)
        self.apply_button.setEnabled(not busy)

        if running:
            tooltip = "O self bot já está em execução."
        elif not (self.settings.has_token and self.settings.token_applied):
            tooltip = "Aplique o token para habilitar."
        elif not self.settings.environment_ready:
            tooltip = "Prepare o ambiente para habilitar."
        else:
            tooltip = "Inicia o self bot com o token aplicado."
        self.start_button.setToolTip(tooltip)

    # ============================================================== logs
    def _log(self, level: str, message: str, prefix: str = "app") -> None:
        self.console.append_line(level, f"[{prefix}] {message}" if prefix else message)
        try:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"[{stamp}] [{(level or 'info').upper():7}] [{prefix}] {message}\n")
        except OSError:
            pass

    # =============================================================== misc
    def _open_path(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event) -> None:  # noqa: N802 - assinatura do Qt
        if self.bot.is_running:
            answer = QMessageBox.question(
                self,
                "Sair",
                "O self bot está em execução. Deseja parar e sair?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.bot.stop()

        if self.env_worker is not None and self.env_worker.isRunning():
            self.env_worker.wait(1500)

        self._log("info", "Aplicativo encerrado.")
        event.accept()

    def showEvent(self, event) -> None:  # noqa: N802 - assinatura do Qt
        super().showEvent(event)
        apply_dark_title_bar(self)
