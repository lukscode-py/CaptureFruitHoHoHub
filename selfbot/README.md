# Self Bot — CaptureFruitHoHoHub

Self bot simples construído com **[discord.js-selfbot-v13](https://www.npmjs.com/package/discord.js-selfbot-v13)**.
Pode ser executado sozinho (`npm start`) ou pelo aplicativo **Control Hub**, que cuida do token, das dependências e da execução.

> ⚠️ Self bots violam os Termos de Serviço do Discord e podem causar **banimento da conta**. Use apenas em uma conta descartável e por sua conta e risco.

## Requisitos

- **Node.js 16.6+** (recomendado 18 LTS ou superior)
- Um token de conta (o aplicativo grava automaticamente no `.env`)

O aplicativo Control Hub instala o Node.js e as dependências sozinho — as instruções abaixo são para uso manual.

## Instalação

```bash
cd selfbot
cp .env.example .env        # Windows: copy .env.example .env
npm install
npm start
```

Edite o `.env` e preencha `DISCORD_TOKEN=` com o token da conta antes de iniciar.

## Comandos

| Comando | Aliases | Descrição |
| --- | --- | --- |
| `!ping` | `!latencia` | Latência do gateway |
| `!help` | `!ajuda`, `!comandos` | Lista os comandos |
| `!status <online\|idle\|dnd\|invisible>` | — | Altera a presença |
| `!presence <texto>` | `!atividade`, `!custom` | Status personalizado |
| `!say <texto>` | `!echo`, `!falar` | Envia uma mensagem no canal |
| `!info` | `!userinfo`, `!conta` | Dados da conta conectada |
| `!uptime` | `!online` | Tempo de execução |
| `!del <1-20>` | `!limpar`, `!apagar` | Apaga suas últimas mensagens do canal |

Novos comandos: edite [`src/commands.js`](src/commands.js) e adicione um item com `name`, `aliases`, `description`, `usage` e `run({ client, message, args, rawArgs, config, logger })`. Retorne uma `string` para responder no canal.

## Configuração (`.env`)

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `DISCORD_TOKEN` | — | **Obrigatório.** Token da conta |
| `COMMAND_PREFIX` | `!` | Prefixo dos comandos |
| `STATUS` | `online` | `online`, `idle`, `dnd` ou `invisible` |
| `CUSTOM_STATUS_TEXT` | vazio | Texto do status personalizado |
| `SHOW_BANNER` | `true` | Banner inicial no terminal |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warn`, `error` |
| `LOG_TO_FILE` | `true` | Grava em `selfbot/logs/bot-AAAA-MM-DD.log` |
| `ALLOWED_GUILD_IDS` | vazio | IDs de servidores permitidos (separados por vírgula) |
| `RESPOND_TO_SELF` | `true` | Responde aos seus próprios comandos |
| `RESPOND_TO_OTHERS` | `false` | Responde comandos de outras pessoas |
| `HEARTBEAT_INTERVAL` | `30` | Intervalo (s) do evento de status enviado ao app |

## Integração com o aplicativo

O processo fala com o Control Hub por **linhas JSON no `stdout`**:

```json
{"cfh":true,"event":"ready","id":"123","username":"fulano","guilds":27,"latency":38,"prefix":"!"}
```

| Evento | Quando acontece | Dados principais |
| --- | --- | --- |
| `starting` | Processo iniciado | `pid`, `node`, `prefix` |
| `ready` | Login confirmado | `id`, `username`, `tag`, `guilds`, `latency` |
| `heartbeat` | A cada `HEARTBEAT_INTERVAL` | `latency`, `guilds`, `uptime` |
| `command` | Comando executado | `name`, `args`, `latency` |
| `presence` | Status alterado | `status` ou `customStatus` |
| `disconnect` / `resume` | Queda e reconexão | `shardId`, `code` |
| `error` | Erro tratado | `scope`, `message`, (opcional) `code` |
| `exit` | Encerramento | `code`, `reason` |

O app também pode enviar comandos pelo **stdin**: `stop`, `status`, `ping`.

### Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Encerrado normalmente (stop/SIGINT/SIGTERM) |
| `2` | Token ausente ou com formato inválido |
| `3` | Token recusado pelo Discord (401/403) |
| `4` | Falha de rede ao conectar |
| `1` | Erro inesperado |

## Estrutura

```
selfbot/
├── index.js          # Entrada: login, heartbeat, stdin, tratamento de erros
├── package.json
├── .env.example
└── src/
    ├── config.js     # Leitura do .env + validação do formato do token
    ├── logger.js     # Logs coloridos, arquivo e eventos JSON
    ├── client.js     # Client do discord.js-selfbot-v13 + eventos
    ├── commands.js   # Registro de comandos
    └── utils.js      # Utilidades (máscara do token, duração, status)
```
