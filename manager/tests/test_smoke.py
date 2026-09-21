"""Testes de fumaca do CaptureFruitHoHoHub Control Hub.

Cobrem, sem depender de rede nem do Discord:

1. Validacao de formato do token e persistencia das configuracoes.
2. Fluxo completo de "Preparar Ambiente" com um Node.js/npm simulados
   (verificacao de versao, escrita do .env, npm install e conferencia da lib).
3. Ciclo de vida do processo do self bot (Iniciar -> Online -> Parar),
   incluindo a leitura do protocolo de eventos JSON.

Execucao:
    cd manager && python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path

MANAGER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MANAGER_DIR))

# O app usa Qt; nos testes rodamos sempre em modo offscreen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FAKE_NODE_VERSION = "v20.11.0"
FAKE_NPM_VERSION = "10.2.0"
# Token ficticio usado nos testes. Ele e montado em tempo de execucao para que
# nunca exista um literal com "cara de token" no repositorio (scanners de
# seguranca, como o push protection do GitHub, bloqueiam arquivos assim).
def make_fake_token() -> str:
    """Gera uma string no formato a.b.c aceito pela validacao do aplicativo."""
    return ".".join(("A1b2C3d4E5f6G7h8I9j0K1l2", "Qw3rTy", "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6"))


FAKE_FAKE_TOKEN = make_fake_token()


def _write_executable(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


class ManagerTestCase(unittest.TestCase):
    """Base que isola cada teste em uma pasta de dados temporaria."""

    def setUp(self) -> None:
        self._original_path = os.environ.get("PATH", "")
        self.temp = Path(tempfile.mkdtemp(prefix="cfh-test-"))
        self.data_dir = self.temp / "data"
        self.selfbot_dir = self.temp / "selfbot"
        self.bin_dir = self.temp / "bin"

        os.environ["CFH_DATA_DIR"] = str(self.data_dir)
        os.environ["CFH_SELFBOT_DIR"] = str(self.selfbot_dir)
        os.environ["PATH"] = f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"

        self._create_selfbot_skeleton()
        self._create_fake_node()

    def tearDown(self) -> None:
        os.environ.pop("CFH_DATA_DIR", None)
        os.environ.pop("CFH_SELFBOT_DIR", None)
        os.environ["PATH"] = self._original_path  # cada teste comeca do zero
        shutil.rmtree(self.temp, ignore_errors=True)

    # ------------------------------------------------------------ fixtures
    def _create_selfbot_skeleton(self) -> None:
        (self.selfbot_dir / "src").mkdir(parents=True, exist_ok=True)
        (self.selfbot_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": "selfbot-test",
                    "version": "1.0.0",
                    "main": "index.js",
                    "dependencies": {"discord.js-selfbot-v13": "^3.7.1"},
                }
            ),
            encoding="utf-8",
        )
        (self.selfbot_dir / "index.js").write_text("// self bot falso\n", encoding="utf-8")
        (self.selfbot_dir / ".env.example").write_text("DISCORD_TOKEN=\nCOMMAND_PREFIX=!\n", encoding="utf-8")

    def _create_fake_node(self) -> None:
        """Cria executaveis 'node' e 'npm' simulados para o fluxo de preparo."""
        self.bin_dir.mkdir(parents=True, exist_ok=True)

        _write_executable(
            self.bin_dir / "node",
            "#!/bin/sh\n"
            'if [ "$1" = "--version" ]; then\n'
            f'  echo "{FAKE_NODE_VERSION}"\n'
            "  exit 0\n"
            "fi\n"
            "# Executa o index.js do self bot (que nos testes apenas emite eventos JSON)\n"
            'exec "$(dirname "$0")/node-runner" "$@"\n',
        )
        _write_executable(
            self.bin_dir / "npm",
            "#!/bin/sh\n"
            'case "$1" in\n'
            "  --version|--v|-v) echo \"" + FAKE_NPM_VERSION + '"; exit 0;;\n'
            "esac\n"
            "# Simula um 'npm install' criando node_modules\n"
            'TARGET="$(pwd)/node_modules/discord.js-selfbot-v13"\n'
            'mkdir -p "$TARGET"\n'
            'printf \'{"name":"discord.js-selfbot-v13","version":"3.7.1"}\\n\' > "$TARGET/package.json"\n'
            'printf \'{"name":"selfbot-test"}\\n\' > "$(pwd)/package-lock.json"\n'
            'echo "added 75 packages"\n'
            "exit 0\n",
        )
        _write_executable(
            self.bin_dir / "node-runner",
            "#!/bin/sh\n"
            "# Simula o self bot real: emite o protocolo de eventos do CFH\n"
            'echo \'{"cfh":true,"event":"starting","pid":1,"node":"v20.11.0","prefix":"!"}\'\n'
            'echo "[12:00:00] [INFO ] conectando"\n'
            'echo \'{"cfh":true,"event":"ready","id":"1","username":"teste","tag":"teste","guilds":3,"latency":42,"prefix":"!"}\'\n'
            "while read -r line; do\n"
            '  if [ "$line" = "stop" ]; then\n'
            '    echo \'{"cfh":true,"event":"exit","code":0,"reason":"comando stop"}\'\n'
            "    exit 0\n"
            "  fi\n"
            "done\n",
        )


class TokenAndSettingsTests(ManagerTestCase):
    def test_formato_do_token(self) -> None:
        from cfh_manager.settings import validate_token_format

        ok, _ = validate_token_format(FAKE_FAKE_TOKEN)
        self.assertTrue(ok, "token em formato valido deveria ser aceito")

        for invalid in ("", "abc", "Bot " + FAKE_FAKE_TOKEN, FAKE_FAKE_TOKEN.rsplit(".", 1)[0]):
            ok, message = validate_token_format(invalid)
            self.assertFalse(ok, f"token invalido aceito: {invalid!r}")
            self.assertTrue(message)

    def test_persistencia_das_configuracoes(self) -> None:
        from cfh_manager.settings import Settings

        settings = Settings()
        settings.token = FAKE_FAKE_TOKEN
        settings.token_applied = True
        settings.environment_ready = True
        settings.save()

        restored = Settings.load()
        self.assertEqual(restored.token, FAKE_FAKE_TOKEN)
        self.assertTrue(restored.ready_to_run)

    def test_token_corrompido_nao_habilita_o_bot(self) -> None:
        from cfh_manager.settings import Settings, settings_file

        settings = Settings(token="valor-invalido", token_applied=True, environment_ready=True)
        settings.save()
        self.assertTrue(settings_file().is_file())

        restored = Settings.load()
        self.assertEqual(restored.token, "")
        self.assertFalse(restored.ready_to_run)

    def test_env_grava_e_preserva_outras_chaves(self) -> None:
        from cfh_manager.settings import apply_token_to_env, env_token

        env_path = apply_token_to_env(FAKE_FAKE_TOKEN, self.selfbot_dir)
        self.assertEqual(env_token(env_path), FAKE_FAKE_TOKEN)

        # Segunda aplicacao com token novo nao deve duplicar a chave.
        novo = FAKE_FAKE_TOKEN[:-3] + "abc"
        apply_token_to_env(novo, self.selfbot_dir)
        content = env_path.read_text(encoding="utf-8")
        self.assertEqual(content.count("DISCORD_TOKEN="), 1)
        self.assertEqual(env_token(env_path), novo)
        self.assertIn("COMMAND_PREFIX=", content)


class EnvironmentWorkerTests(ManagerTestCase):
    def test_preparo_completo_do_ambiente(self) -> None:
        from cfh_manager.workers import EnvironmentWorker

        worker = EnvironmentWorker(token=make_fake_token())
        steps: list[tuple[str, str, str]] = []
        worker.step.connect(lambda step_id, title, status, detail: steps.append((step_id, status, detail)))

        result: dict = {}
        worker.finished_result.connect(lambda ok, message: result.update(ok=ok, message=message))

        worker.run()  # execucao sincrona: o proprio metodo 'run' faz todo o trabalho

        self.assertTrue(result.get("ok"), f"preparo falhou: {result.get('message')}")

        statuses = {step_id: status for step_id, status, _ in steps}
        self.assertEqual(statuses.get("node"), "ok")
        self.assertEqual(statuses.get("npm"), "ok")
        self.assertEqual(statuses.get("deps"), "ok")
        self.assertEqual(statuses.get("deps_check"), "ok")
        self.assertEqual(statuses.get("done"), "ok")

        self.assertTrue((self.selfbot_dir / "node_modules" / "discord.js-selfbot-v13").is_dir())
        self.assertEqual(worker.installed_lib_version, "3.7.1")
        self.assertTrue(worker.node_version.startswith(FAKE_NODE_VERSION[0]))

        env_path = self.selfbot_dir / ".env"
        self.assertTrue(env_path.is_file())
        self.assertIn(FAKE_FAKE_TOKEN, env_path.read_text(encoding="utf-8"))

    def test_falha_quando_node_nao_existe(self) -> None:
        from cfh_manager import workers

        # Sem 'node' no PATH e sem rede, o preparo precisa falhar de forma tratada.
        vazio = self.bin_dir / "vazio"
        vazio.mkdir(parents=True, exist_ok=True)
        os.environ["PATH"] = str(vazio)
        original_install = workers.EnvironmentWorker._install_node
        workers.EnvironmentWorker._install_node = lambda self: ""  # type: ignore[assignment]
        try:
            worker = workers.EnvironmentWorker()
            result: dict = {}
            worker.finished_result.connect(lambda ok, message: result.update(ok=ok, message=message))
            worker.run()
        finally:
            workers.EnvironmentWorker._install_node = original_install  # type: ignore[assignment]
            os.environ["PATH"] = self._original_path

        self.assertFalse(result.get("ok"))
        self.assertIn("Node.js", result.get("message", ""))


class BotProcessTests(ManagerTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_ciclo_de_vida_do_bot(self) -> None:
        from PySide6.QtCore import QTimer

        from cfh_manager.bot_process import STATE_ONLINE, STATE_STOPPED, BotProcess

        node_path = str(self.bin_dir / "node")
        bot = BotProcess()
        states: list[str] = []
        logs: list[tuple[str, str]] = []
        infos: list = []
        bot.state_changed.connect(states.append)
        bot.log.connect(lambda level, message: logs.append((level, message)))
        bot.info_changed.connect(infos.append)

        self.assertTrue(bot.start(self.selfbot_dir, node_path))
        self.assertEqual(bot.state, "starting")

        # Aguarda o evento "ready" chegar pela fila de eventos do Qt.
        deadline = 30
        for _ in range(deadline * 10):
            self.app.processEvents()
            if bot.state == STATE_ONLINE:
                break
            QTimer.singleShot(0, lambda: None)
            self.app.processEvents()
            time.sleep(0.1)

        self.assertEqual(bot.state, STATE_ONLINE, f"estados observados: {states}")
        self.assertEqual(bot.info.username, "teste")
        self.assertEqual(bot.info.guilds, 3)
        self.assertEqual(bot.info.latency, 42)
        self.assertTrue(any(level == "info" for level, _ in logs), "esperava logs do bot no painel")

        bot.stop()
        for _ in range(300):
            self.app.processEvents()
            if bot.state == STATE_STOPPED and not bot.is_running:
                break
            time.sleep(0.05)

        self.assertEqual(bot.state, STATE_STOPPED)
        self.assertFalse(bot.is_running)
        self.assertIn(STATE_STOPPED, states)

    def test_saida_com_token_invalido_leva_a_estado_de_erro(self) -> None:
        from cfh_manager.bot_process import STATE_ERROR, BotProcess

        # Um "index.js" que termina com codigo 2 (token invalido) deve gerar estado de erro.
        (self.selfbot_dir / "index.js").write_text("// nada\n", encoding="utf-8")
        broken_dir = self.temp / "broken-selfbot"
        broken_dir.mkdir()
        (broken_dir / "package.json").write_text('{"name":"broken"}', encoding="utf-8")
        (broken_dir / "index.js").write_text("(function(){process.exit(2);})();\n", encoding="utf-8")

        runner = self.bin_dir / "node-exit2"
        _write_executable(runner, "#!/bin/sh\nexit 2\n")

        bot = BotProcess()
        result: dict = {}
        bot.exited.connect(lambda code, detail: result.update(code=code, detail=detail))
        bot.start(broken_dir, str(runner))

        for _ in range(400):
            self.app.processEvents()
            if not bot.is_running and "code" in result:
                break
            time.sleep(0.05)

        self.assertEqual(result.get("code"), 2)
        self.assertEqual(bot.state, STATE_ERROR)
        self.assertIn("token", str(result.get("detail", "")).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
