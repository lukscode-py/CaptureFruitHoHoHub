'use strict';

/**
 * Criacao e ligacao do Client (discord.js-selfbot-v13) com os comandos.
 */

const { Client } = require('discord.js-selfbot-v13');
const { buildCommandMap } = require('./commands');
const { formatDuration, validateStatus } = require('./utils');

const COMMAND_COOLDOWN_MS = 1500;

/**
 * @param {object} config Configuracao carregada de src/config.js
 * @param {import('./logger').Logger} logger
 */
function createClient(config, logger) {
  const startedAt = Date.now();
  const commands = buildCommandMap();
  const cooldowns = new Map();

  const client = new Client({
    // O self bot nao tem "bot user": desabilitamos checagem de atualizacao e
    // deixamos a presenca inicial definida pelo arquivo .env
    checkUpdate: false,
    retryLimit: 2,
    restGlobalRateLimit: 20,
    restTimeOffset: 400,
    presence: {
      status: validateStatus(config.status) ?? 'online',
      activities: config.customStatusText
        ? [{ name: 'Custom Status', state: config.customStatusText, type: 'CUSTOM' }]
        : [],
      afk: false,
    },
  });

  let connectedAt = null;

  client.on('ready', () => {
    connectedAt = Date.now();
    const user = client.user;
    logger.success(`Conectado como ${user.username} (${user.id})`);
    logger.emit('ready', {
      id: user.id,
      username: user.username,
      tag: user.tag ?? user.username,
      discriminator: user.discriminator ?? '0',
      guilds: client.guilds.cache.size,
      prefix: config.prefix,
      latency: Math.max(0, Math.round(client.ws.ping)),
    });
  });

  client.on('messageCreate', async (message) => {
    try {
      await handleMessage(message);
    } catch (error) {
      logger.error(`Erro ao processar mensagem: ${error?.stack ?? error}`);
      logger.emit('error', { scope: 'messageCreate', message: String(error?.message ?? error) });
    }
  });

  client.on('error', (error) => {
    logger.error(`Erro do client: ${error?.message ?? error}`);
    logger.emit('error', { scope: 'client', message: String(error?.message ?? error) });
  });

  client.on('warn', (info) => {
    logger.warn(`[discord] ${info}`);
  });

  client.on('rateLimit', (info) => {
    logger.warn(
      `Rate limit (${info?.route ?? 'desconhecido'}): aguardando ${formatDuration(info?.timeoutToReset ?? 0)}`,
    );
    logger.emit('warn', { scope: 'rateLimit', route: info?.route ?? null });
  });

  client.on('shardDisconnect', (event, shardId) => {
    logger.warn(`Conexao perdida (shard ${shardId}) — codigo ${event?.code ?? 'desconhecido'}. Reconectando...`);
    logger.emit('disconnect', { shardId, code: event?.code ?? null });
  });

  client.on('shardResume', (shardId) => {
    logger.success(`Conexao restabelecida (shard ${shardId}).`);
    logger.emit('resume', { shardId });
  });

  client.on('shardError', (error, shardId) => {
    logger.error(`Erro no shard ${shardId}: ${error?.message ?? error}`);
    logger.emit('error', { scope: 'shard', shardId, message: String(error?.message ?? error) });
  });

  /** Trata as mensagens que chegam, procurando por comandos. */
  async function handleMessage(message) {
    const isSelf = message.author?.id === client.user?.id;
    if (isSelf && !config.respondToSelf) return;
    if (!isSelf && !config.respondToOthers) return;
    if (!isSelf && (message.author?.bot || message.webhookId)) return;

    if (config.allowedGuildIds.length && message.guild && !config.allowedGuildIds.includes(message.guild.id)) return;

    const content = message.content ?? '';
    if (!content.startsWith(config.prefix)) return;

    const withoutPrefix = content.slice(config.prefix.length).trim();
    if (!withoutPrefix) return;

    const [rawName, ...args] = withoutPrefix.split(/\s+/);
    const command = commands.get(rawName.toLowerCase());
    if (!command) return;

    const cooldownKey = `${message.author?.id ?? 'self'}:${command.name}`;
    const lastRun = cooldowns.get(cooldownKey) ?? 0;
    if (Date.now() - lastRun < COMMAND_COOLDOWN_MS) return;
    cooldowns.set(cooldownKey, Date.now());

    const rawArgs = withoutPrefix.slice(rawName.length).trim();
    logger.info(`Comando recebido: ${config.prefix}${command.name} (${args.length} argumento(s))`);

    const result = await command.run({
      client,
      message,
      args,
      rawArgs,
      config,
      logger,
      commands,
      startedAt,
    });

    if (typeof result === 'string' && result.trim()) {
      await message.channel.send(result).catch(async () => {
        // Alguns canais nao aceitam envio direto (ex.: DM fechada) — tenta responder direto.
        await message.author?.send(result).catch(() => undefined);
      });
    }

    logger.emit('command', { name: command.name, args: args.length, latency: Math.round(client.ws.ping) });
  }

  return {
    client,
    commands,
    startedAt,
    get connectedAt() {
      return connectedAt;
    },
    async stop() {
      logger.info('Encerrando conexao com o Discord...');
      try {
        await client.destroy();
      } catch (error) {
        logger.warn(`Falha ao encerrar o client: ${error?.message ?? error}`);
      }
    },
  };
}

module.exports = { createClient, COMMAND_COOLDOWN_MS };
