'use strict';

const { VALID_STATUS } = require('./config');

/** Normaliza o argumento de status. */
function validateStatus(value) {
  const status = String(value ?? '').toLowerCase();
  if (status === 'offline') return 'invisible';
  return VALID_STATUS.includes(status) ? status : null;
}

/** Formata duracao em ms como "1h 2m 3s". */
function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  parts.push(`${seconds}s`);
  return parts.join(' ');
}

/** Mascara o token para que ele nunca apareca em logs. */
function maskToken(token) {
  const value = String(token ?? '');
  if (value.length <= 12) return '***';
  return `${value.slice(0, 6)}...${value.slice(-4)}`;
}

module.exports = { validateStatus, formatDuration, maskToken };
