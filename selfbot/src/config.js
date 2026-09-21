'use strict';

/**
 * Carregamento de configuracao.
 *
 * Fontes (a ultima sobrescreve a anterior):
 *   1. Valores padrao abaixo
 *   2. Arquivo ".env" na raiz do self bot (gerado pelo app ao "Aplicar Token")
 *   3. Variaveis de ambiente reais do processo
 *   4. Arquivo "config.json" na raiz do self bot (opcional, avancado)
 */

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');

const DEFAULTS = {
  token: '',
  prefix: '!',
  status: 'online',
  customStatusText: '',
  showBanner: true,
  logLevel: 'info',
  logToFile: true,
  allowedGuildIds: [],
  respondToSelf: true,
  respondToOthers: false,
  heartbeatInterval: 30,
};

/** Le um arquivo .env e devolve um objeto simples de chave/valor. */
function parseDotEnv(content) {
  const result = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const separator = line.indexOf('=');
    if (separator === -1) continue;
    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"') && value.length > 1) ||
      (value.startsWith("'") && value.endsWith("'") && value.length > 1)
    ) {
      value = value.slice(1, -1);
    }
    result[key] = value;
  }
  return result;
}

function readJsonIfExists(filePath) {
  try {
    if (!fs.existsSync(filePath)) return {};
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return {};
  }
}

function toBool(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback;
  if (typeof value === 'boolean') return value;
  return ['1', 'true', 'yes', 'on', 'sim'].includes(String(value).toLowerCase());
}

function toInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toList(value) {
  if (Array.isArray(value)) return value.map(String).map((item) => item.trim()).filter(Boolean);
  if (!value) return [];
  return String(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * @returns {ReturnType<typeof DEFAULTS> & { root: string, envFile: string }}
 */
function loadConfig() {
  const envFile = path.join(ROOT, '.env');
  const envFromFile = fs.existsSync(envFile) ? parseDotEnv(fs.readFileSync(envFile, 'utf8')) : {};
  const envFromProcess = process.env;
  const jsonConfig = readJsonIfExists(path.join(ROOT, 'config.json'));

  const pick = (key) => jsonConfig[key] ?? envFromProcess[key] ?? envFromFile[key];

  const token = String(pick('DISCORD_TOKEN') ?? DEFAULTS.token).trim();

  const config = {
    root: ROOT,
    envFile,
    token,
    prefix: String(pick('COMMAND_PREFIX') ?? DEFAULTS.prefix) || DEFAULTS.prefix,
    status: String(pick('STATUS') ?? DEFAULTS.status).toLowerCase() || DEFAULTS.status,
    customStatusText: String(pick('CUSTOM_STATUS_TEXT') ?? DEFAULTS.customStatusText),
    showBanner: toBool(pick('SHOW_BANNER'), DEFAULTS.showBanner),
    logLevel: String(pick('LOG_LEVEL') ?? DEFAULTS.logLevel).toLowerCase() || DEFAULTS.logLevel,
    logToFile: toBool(pick('LOG_TO_FILE'), DEFAULTS.logToFile),
    allowedGuildIds: toList(pick('ALLOWED_GUILD_IDS') ?? DEFAULTS.allowedGuildIds),
    respondToSelf: toBool(pick('RESPOND_TO_SELF'), DEFAULTS.respondToSelf),
    respondToOthers: toBool(pick('RESPOND_TO_OTHERS'), DEFAULTS.respondToOthers),
    heartbeatInterval: toInt(pick('HEARTBEAT_INTERVAL'), DEFAULTS.heartbeatInterval),
  };

  if (jsonConfig.prefix) config.prefix = String(jsonConfig.prefix);

  return config;
}

const VALID_STATUS = ['online', 'idle', 'dnd', 'invisible', 'offline'];
const TOKEN_REGEX = /^[\w-]{20,40}\.[\w-]{5,10}\.[\w-]{25,60}$/;

/**
 * Verifica o formato do token (nao valida com a API do Discord).
 * @param {string} token
 * @returns {{ ok: boolean, reason?: string }}
 */
function validateTokenFormat(token) {
  const value = String(token ?? '').trim();
  if (!value) return { ok: false, reason: 'Token vazio.' };
  if (/^Bot\s/i.test(value)) return { ok: false, reason: 'Remova o prefixo "Bot " (ele e apenas para bots oficiais).' };
  if (/^mfa\./i.test(value)) return { ok: true }; // tokens com 2FA continuam validos no login
  if (!TOKEN_REGEX.test(value)) {
    return { ok: false, reason: 'Formato inesperado. O token tem 3 partes separadas por ponto (base64.base64.base64).' };
  }
  return { ok: true };
}

module.exports = { loadConfig, validateTokenFormat, parseDotEnv, DEFAULTS, ROOT, VALID_STATUS };
