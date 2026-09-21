'use strict';

/**
 * Registro de comandos do self bot.
 *
 * Cada comando recebe um contexto:
 *   { client, message, args, rawArgs, config, logger, commands }
 * e deve devolver uma string (resposta enviada no mesmo canal) ou nada.
 */

const { validateStatus } = require('./utils');

/** @typedef {{ name: string, aliases?: string[], description: string, usage?: string, run: (ctx: any) => Promise<any>|any }} Command */

/** @type {Command[]} */
const commandList = [
  {
    name: 'ping',
    aliases: ['latencia', 'latência'],
    description: 'Mostra a latencia (ping) do gateway.',
    run: ({ client }) => {
      const ping = Math.max(0, Math.round(client.ws.ping));
      const emoji = ping < 100 ? '🟢' : ping < 250 ? '🟡' : '🔴';
      return `${emoji} **Pong!** Latencia do gateway: \`${ping}ms\``;
    },
  },
  {
    name: 'help',
    aliases: ['ajuda', 'comandos'],
    description: 'Lista os comandos disponiveis.',
    run: ({ config, commands }) => {
      const lines = [...commands.values()]
        .map((command) => `\`${config.prefix}${command.name}\` — ${command.description}`)
        .join('\n');
      return `**CaptureFruitHoHoHub Self Bot**\nPrefixo: \`${config.prefix}\`\n\n${lines}`;
    },
  },
  {
    name: 'status',
    description: 'Altera a sua presenca (online, idle, dnd ou invisible).',
    usage: 'status <online|idle|dnd|invisible>',
    run: ({ client, args, logger }) => {
      const status = validateStatus(args[0]);
      if (!status) return 'Uso correto: `status <online|idle|dnd|invisible>`';
      client.user.setStatus(status);
      logger.emit('presence', { status });
      return `Status alterado para **${status}**.`;
    },
  },
  {
    name: 'presence',
    aliases: ['atividade', 'custom'],
    description: 'Define o texto do status personalizado.',
    usage: 'presence <texto>',
    run: ({ client, rawArgs, logger }) => {
      const text = rawArgs.trim();
      if (!text) return 'Uso correto: `presence <texto>`';
      client.user.setActivity({ name: 'Custom Status', state: text, type: 'CUSTOM' });
      logger.emit('presence', { customStatus: text });
      return `Status personalizado definido para: **${text}**`;
    },
  },
  {
    name: 'say',
    aliases: ['echo', 'falar'],
    description: 'Envia uma mensagem no canal atual.',
    usage: 'say <texto>',
    run: ({ rawArgs }) => (rawArgs.trim() ? rawArgs.trim() : 'Uso correto: `say <texto>`'),
  },
  {
    name: 'info',
    aliases: ['userinfo', 'conta'],
    description: 'Mostra informacoes da conta conectada.',
    run: ({ client, message }) => {
      const user = client.user;
      const created = `<t:${Math.floor(user.createdTimestamp / 1000)}:F>`;
      return [
        `**${user.username}**${user.discriminator && user.discriminator !== '0' ? `#${user.discriminator}` : ''}`,
        `ID: \`${user.id}\``,
        `Conta criada em: ${created}`,
        `Servidores: \`${client.guilds.cache.size}\``,
        `Canal: ${message.channel?.toString?.() ?? 'desconhecido'}`,
      ].join('\n');
    },
  },
  {
    name: 'uptime',
    aliases: ['online'],
    description: 'Mostra ha quanto tempo o self bot esta rodando.',
    run: ({ startedAt }) => {
      const seconds = Math.floor((Date.now() - startedAt) / 1000);
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `🕒 Online ha **${hours}h ${minutes}m ${seconds % 60}s**.`;
    },
  },
  {
    name: 'del',
    aliases: ['limpar', 'apagar'],
    description: 'Apaga as suas ultimas N mensagens no canal atual (max. 20).',
    usage: 'del <quantidade>',
    run: async ({ message, args, logger }) => {
      const amount = Number.parseInt(args[0], 10);
      if (!Number.isFinite(amount) || amount < 1) return 'Uso correto: `del <quantidade>` (1 a 20)';
      const limit = Math.min(amount, 20);
      const messages = await message.channel.messages.fetch({ limit: 50 });
      const mine = messages.filter((item) => item.author.id === message.client.user.id).first(limit);
      let deleted = 0;
      for (const item of mine) {
        try {
          await item.delete();
          deleted += 1;
        } catch (error) {
          logger.warn(`Falha ao apagar mensagem ${item.id}: ${error.message}`);
        }
      }
      logger.emit('command', { name: 'del', deleted });
      return deleted ? `🧹 Apaguei **${deleted}** mensagem(ns).` : 'Nao encontrei mensagens minhas para apagar.';
    },
  },
];

/** Cria o mapa de comandos (nome + aliases). */
function buildCommandMap() {
  /** @type {Map<string, Command>} */
  const map = new Map();
  for (const command of commandList) {
    map.set(command.name, command);
    for (const alias of command.aliases ?? []) map.set(alias, command);
  }
  return map;
}

module.exports = { buildCommandMap, commandList };
