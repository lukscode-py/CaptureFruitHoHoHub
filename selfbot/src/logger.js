'use strict';

/**
 * Logger simples com niveis, cores ANSI, escrita opcional em arquivo e
 * protocolo de eventos em JSON para o aplicativo gerenciador (Control Hub).
 *
 * Cada linha do protocolo segue o formato:
 *   {"cfh":true,"event":"ready","ts":1699999999999, ...dados}
 * O gerenciador le o stdout do bot e usa esses eventos para atualizar a UI.
 */

const fs = require('node:fs');
const path = require('node:path');

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };

const COLORS = {
  reset: '\u001b[0m',
  gray: '\u001b[90m',
  cyan: '\u001b[36m',
  green: '\u001b[32m',
  yellow: '\u001b[33m',
  red: '\u001b[31m',
  magenta: '\u001b[35m',
};

const LEVEL_STYLE = {
  debug: { label: 'DEBUG', color: COLORS.gray },
  info: { label: 'INFO ', color: COLORS.cyan },
  warn: { label: 'WARN ', color: COLORS.yellow },
  error: { label: 'ERROR', color: COLORS.red },
  event: { label: 'EVENT', color: COLORS.magenta },
};

class Logger {
  /**
   * @param {object} [options]
   * @param {'debug'|'info'|'warn'|'error'} [options.level='info']
   * @param {boolean} [options.color=true] Usar cores ANSI no terminal
   * @param {boolean} [options.toFile=false] Gravar em arquivo
   * @param {string} [options.filePath] Caminho do arquivo de log
   * @param {boolean} [options.protocol=true] Emitir eventos JSON no stdout
   */
  constructor(options = {}) {
    this.level = LEVELS[options.level] ?? LEVELS.info;
    this.color = options.color !== false;
    this.protocol = options.protocol !== false;
    this.stream = options.stream ?? process.stdout;
    this.fileStream = null;

    if (options.toFile) {
      const filePath =
        options.filePath ?? path.join(__dirname, '..', 'logs', `bot-${new Date().toISOString().slice(0, 10)}.log`);
      try {
        fs.mkdirSync(path.dirname(filePath), { recursive: true });
        this.fileStream = fs.createWriteStream(filePath, { flags: 'a' });
      } catch (error) {
        this.warn(`Nao foi possivel abrir o arquivo de log (${error.message})`);
      }
    }
  }

  /** Monta a linha formatada para o terminal. */
  _format(level, message) {
    const style = LEVEL_STYLE[level] ?? LEVEL_STYLE.info;
    const time = new Date().toLocaleTimeString('pt-BR', { hour12: false });
    const prefix = `[${time}] [${style.label}]`;
    if (!this.color) return `${prefix} ${message}`;
    return `${COLORS.gray}[${time}]${COLORS.reset} ${style.color}${prefix.slice(prefix.indexOf('['))}${COLORS.reset} ${message}`;
  }

  /** Escreve uma linha no terminal e, se habilitado, no arquivo. */
  _write(level, message) {
    const line = this._format(level, message);
    this.stream.write(`${line}\n`);
    if (this.fileStream) {
      this.fileStream.write(`${this._stripAnsi(line)}\n`);
    }
  }

  _stripAnsi(text) {
    // eslint-disable-next-line no-control-regex
    return text.replace(/\u001b\[[0-9;]*m/g, '');
  }

  log(level, message) {
    if ((LEVELS[level] ?? LEVELS.info) < this.level) return;
    this._write(level, message);
  }

  debug(message) {
    this.log('debug', message);
  }

  info(message) {
    this.log('info', message);
  }

  warn(message) {
    this.log('warn', message);
  }

  error(message) {
    this.log('error', message);
  }

  /** Sucesso em verde, independente do nivel configurado. */
  success(message) {
    this._write('info', this.color ? `${COLORS.green}${message}${COLORS.reset}` : message);
  }

  /**
   * Emite um evento estruturado para o aplicativo gerenciador.
   * @param {string} event
   * @param {object} [data]
   */
  emit(event, data = {}) {
    if (!this.protocol) return;
    try {
      this.stream.write(`${JSON.stringify({ cfh: true, event, ts: Date.now(), ...data })}\n`);
    } catch {
      /* ignora falhas de serializacao */
    }
    if (this.fileStream) {
      this.fileStream.write(`${JSON.stringify({ ts: new Date().toISOString(), event, ...data })}\n`);
    }
  }

  close() {
    if (this.fileStream) {
      this.fileStream.end();
      this.fileStream = null;
    }
  }
}

module.exports = { Logger, LEVELS };
