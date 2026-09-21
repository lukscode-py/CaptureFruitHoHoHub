'use strict';

/**
 * CaptureFruitHoHoHub — Self Bot (discord.js-selfbot-v13)
 * -------------------------------------------------------
 * Ponto de entrada. Pode ser executado:
 *   - manualmente:  npm start
 *   - pelo app:     CaptureFruitHoHoHub-Manager.exe (le stdout/stderr deste processo)
 *
 * Protocolo com o app: linhas JSON com a marca {"cfh":true,...} no stdout.
 * Os comandos "stop", "status" e "ping" tambem podem ser enviados via stdin.
 */

const process = require('node:process');
const readline = require('node:readline');

const { loadConfig, validateTokenFormat } = require('./src/config');
const { Logger } = require('./src/logger');
const { createClient } = require('./src/client');
const { formatDuration, maskToken } = require('./src/utils');

const EXIT_CONFIG = 2;
const EXIT_AUTH = 3;
const EXIT_NETWORK = 4;
const EXIT_FATAL = 1;

const config = loadConfig();
const logger = new Logger({
  level: config.logLevel,
  toFile: config.logToFile,
  color: process.stdout.isTTY === true,
});

let app = null;
let heartbeat = null;
let shuttingDown = false;

function printBanner() {
  if (!config.showBanner) return;
  const lines = [
    '=====================================================',
    '   CaptureFruitHoHoHub  |  Self Bot (v1.0.0)',
    '   discord.js-selfbot-v13  •  uso pessoal/estudo',
    '=====================================================',
    `   Prefixo dos comandos : ${config.prefix}`,
    `   Status inicial       : ${config.status}`,
    `   Token                : ${maskToken(config.token)}`,
    '=====================================================',
  ];
  for (const line of lines) logger.info(line);
}

/** Encerra o processo de forma limpa. */
async function shutdown(exitCode = 0, reason = 'encerrado') {
  if (shuttingDown) return;
  shuttingDown = true;
  if (heartbeat) clearInterval(heartbeat);

  logger.info(`Desligando... (${reason})`);
  if (app) await app.stop();
  logger.emit('exit', { code: exitCode, reason });
  logger.close();

  // Pequeno atraso para dar tempo de esvaziar os buffers de stdout.
  setTimeout(() => process.exit(exitCode), 150);
}

async function start() {
  printBanner();
  logger.emit('starting', { pid: process.pid, node: process.version, prefix: config.prefix });

  const tokenCheck = validateTokenFormat(config.token);
  if (!tokenCheck.ok) {
    logger.error(`Token ausente ou invalido: ${tokenCheck.reason}`);
    logger.error('Abra o CaptureFruitHoHoHub Manager, cole o token e clique em "Aplicar Token".');
    logger.emit('error', { scope: 'config', message: tokenCheck.reason });
    await shutdown(EXIT_CONFIG, 'token invalido');
    return;
  }

  logger.info('Fazendo login no Discord...');
  app = createClient(config, logger);

  try {
    await app.client.login(config.token);
  } catch (error) {
    const message = String(error?.message ?? error);
    const isAuth = /invalid token|TOKEN_INVALID|401|unauthorized/i.test(message);
    const isNetwork = /ENOTFOUND|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|fetch failed|getaddrinfo/i.test(message);

    if (isAuth) {
      logger.error('Login recusado pelo Discord: token invalido, expirado ou revogado.');
      logger.error('Gere um novo token na sua conta e aplique novamente no app.');
      logger.emit('error', { scope: 'login', code: 'TOKEN_INVALID', message });
      await shutdown(EXIT_AUTH, 'token invalido');
      return;
    }

    if (isNetwork) {
      logger.error(`Sem conexao com o Discord: ${message}`);
      logger.emit('error', { scope: 'login', code: 'NETWORK', message });
      await shutdown(EXIT_NETWORK, 'falha de rede');
      return;
    }

    logger.error(`Falha inesperada no login: ${message}`);
    logger.emit('error', { scope: 'login', code: 'UNKNOWN', message });
    await shutdown(EXIT_FATAL, 'falha no login');
  }
}

/** Escuta comandos enviados pelo app (stdin). */
function listenToStdin() {
  if (!process.stdin.isTTY && !process.stdin.readable) return;
  const rl = readline.createInterface({ input: process.stdin, terminal: false });

  rl.on('line', (line) => {
    const command = line.trim().toLowerCase();
    if (!command) return;

    if (command === 'stop' || command === 'exit' || command === 'quit') {
      shutdown(0, 'solicitado pelo app');
      return;
    }

    if (command === 'status') {
      const uptimeMs = app ? Date.now() - app.startedAt : 0;
      logger.emit('status', {
        online: Boolean(app?.client?.user),
        uptime: formatDuration(uptimeMs),
        latency: app ? Math.max(0, Math.round(app.client.ws.ping)) : null,
        guilds: app?.client?.guilds?.cache?.size ?? 0,
      });
      return;
    }

    if (command === 'ping') {
      logger.emit('heartbeat', { latency: app ? Math.max(0, Math.round(app.client.ws.ping)) : null });
    }
  });

  // Observacao: NAO encerramos o bot apenas porque o stdin foi fechado — isso
  // aconteceria ao rodar o processo com a entrada redirecionada. O encerramento
  // acontece pelo comando "stop", por SIGINT/SIGTERM ou pelo app (taskkill).
  rl.on('error', () => rl.close());
}

process.on('SIGINT', () => shutdown(0, 'SIGINT'));
process.on('SIGTERM', () => shutdown(0, 'SIGTERM'));

process.on('unhandledRejection', (reason) => {
  logger.error(`Promise rejeitada sem tratamento: ${reason?.stack ?? reason}`);
  logger.emit('error', { scope: 'unhandledRejection', message: String(reason?.message ?? reason) });
});

process.on('uncaughtException', (error) => {
  logger.error(`Excecao nao tratada: ${error?.stack ?? error}`);
  logger.emit('error', { scope: 'uncaughtException', message: String(error?.message ?? error) });
  shutdown(EXIT_FATAL, 'excecao nao tratada');
});

(async () => {
  listenToStdin();

  if (config.heartbeatInterval > 0) {
    heartbeat = setInterval(() => {
      if (!app?.client?.user) return;
      logger.emit('heartbeat', {
        latency: Math.max(0, Math.round(app.client.ws.ping)),
        guilds: app.client.guilds.cache.size,
        uptime: formatDuration(Date.now() - app.startedAt),
      });
    }, config.heartbeatInterval * 1000);
    if (typeof heartbeat.unref === 'function') heartbeat.unref();
  }

  await start();
})();
