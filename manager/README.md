# CaptureFruitHoHoHub Control Hub

Aplicativo Windows (**`.exe`**) com interface **dark** (estilo Fluent/WinUI) que gerencia todo o self bot:

1. **Aplicar Token** — cola o token, valida o formato e confere na API do Discord.
2. **Preparar Ambiente** — instala o Node.js (se faltar) e as dependências do self bot.
3. **Status em tempo real** — checklist colorida de cada etapa.
4. **Iniciar/Parar Bot** — com indicador `Parado · Iniciando · Online · Erro` e console de log.

![Tela principal](../docs/screenshots/03-bot-online.png)

**Tecnologia:** Python 3.10+ + PySide6 (Qt 6), empacotado com PyInstaller em `.exe` único ou em pasta.

---

## Como compilar o `.exe`

### Pré-requisitos

- **Windows 10/11** (x64)
- **Python 3.10+** com a opção *Add python.exe to PATH* marcada
- Conexão com a internet (para baixar `PySide6` e `PyInstaller`)
- Node.js **não** é necessário na máquina de build — o app instala no computador do usuário final

### Build com um comando

```powershell
cd manager
.\build.ps1
```

Saída: `manager\dist\CaptureFruitHoHoHub-ControlHub\` com `CaptureFruitHoHoHub-ControlHub.exe`.

Para gerar **um único arquivo**:

```powershell
.\build.ps1 -OneFile        # dist\CaptureFruitHoHoHub-ControlHub.exe (~60 MB)
```

Atalho alternativo, sem PowerShell explícito:

```bat
build.bat
build.bat --onefile
```

O que o script faz:

1. cria/reaproveita o ambiente virtual `.venv`;
2. instala `PySide6` e `PyInstaller` de `requirements.txt`;
3. roda os testes de fumaça (`python -m unittest discover -s tests`);
4. chama o PyInstaller com `CaptureFruitHoHoHub-ControlHub.spec`;
5. mostra onde estão os artefatos e o que distribuir.

Parâmetros disponíveis: `-OneFile`, `-Clean`, `-SkipInstall`, `-Python "py -3.12"`.

### Build manual (sem script)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\pyinstaller --noconfirm --clean CaptureFruitHoHoHub-ControlHub.spec
# arquivo unico:
$env:CFH_ONEFILE = "1"; .\.venv\Scripts\pyinstaller --noconfirm --clean CaptureFruitHoHoHub-ControlHub.spec
```

### Rodar em modo desenvolvimento

```bash
python -m pip install -r requirements.txt
python app.py
```

---

## Como o `.exe` encontra o self bot

O app procura a pasta `selfbot` nesta ordem:

1. variável de ambiente `CFH_SELFBOT_DIR`;
2. `<pasta do exe>\selfbot` (**modo portátil** — ideal para distribuir junto);
3. dados do usuário: `%LOCALAPPDATA%\CaptureFruitHoHoHub.ControlHub\selfbot` (cópia criada a partir do pacote embutido no `.exe` quando nenhuma das anteriores existe).

Ou seja: o `.exe` funciona sozinho (o código do self bot vai embutido no PyInstaller), mas se a pasta `selfbot` estiver ao lado dele, ela tem prioridade — útil para editar comandos sem recompilar.

---

## Onde os dados são gravados

Tudo em `%LOCALAPPDATA%\CaptureFruitHoHoHub.ControlHub\`:

| Caminho | Conteúdo |
| --- | --- |
| `settings.json` | Token aplicado, caminho do Node.js, estado do ambiente (permissões restritas ao usuário) |
| `logs\manager-AAAA-MM-DD.log` | Log completo da interface |
| `runtime\node\` | Node.js portátil baixado automaticamente |
| `runtime\downloads\` | Cache dos instaladores do Node.js |
| `selfbot\` | Cópia do self bot (quando não há uma pasta `selfbot` ao lado do `.exe`) |

Variável `CFH_DATA_DIR` permite trocar a pasta (usada nos testes).

---

## Testes

```bash
cd manager
python -m unittest discover -s tests -v
```

Oito testes de fumaça cobrem: validação do token, persistência das configurações, escrita do `.env`, preparo completo do ambiente (com Node/npm simulados), falha tratada sem Node.js e o ciclo de vida do processo do bot (`Iniciando → Online → Parado`) incluindo leitura do protocolo de eventos.

Em Linux/macOS, rode com `QT_QPA_PLATFORM=offscreen` (as dependências gráficas do Qt podem não estar instaladas).

---

## Estrutura do código

```
manager/
├── app.py                       # Entrada do aplicativo (QApplication + tema)
├── requirements.txt
├── build.ps1 / build.bat        # Compilação do .exe
├── CaptureFruitHoHoHub-ControlHub.spec
├── assets/                      # icon.ico, icon.png, check.png
├── tests/test_smoke.py
└── cfh_manager/
    ├── paths.py                 # Localização de pastas, self bot e dados
    ├── settings.py              # Token, .env, permissões e preferências
    ├── workers.py               # TokenWorker + EnvironmentWorker (threads)
    ├── bot_process.py           # QProcess do self bot + estados + eventos
    ├── theme.py                 # Paleta e QSS do tema dark (Fluent)
    └── ui/
        ├── main_window.py       # Janela única com os 4 cartões
        └── widgets.py           # Card, StatusPill, Metric, StepsPanel, LogConsole
```

### Fluxo interno

```
[ Aplicar Token ]      → TokenWorker (QThread) → GET /api/v9/users/@me
                                               → settings.json + .env
[ Preparar Ambiente ]  → EnvironmentWorker (QThread)
                         ├─ localiza/copia o self bot
                         ├─ verifica Node.js (baixa LTS se faltar) e npm
                         ├─ grava o token no .env
                         ├─ npm install
                         └─ confere discord.js-selfbot-v13
[ Iniciar Bot ]        → QProcess: node index.js (cwd = selfbot)
                         ├─ lê stdout: linhas JSON {"cfh":true,...} → UI
                         └─ stop: stdin "stop" + taskkill /T
```

---

## Solução de problemas no build

| Erro | Solução |
| --- | --- |
| `Python nao encontrado` | Instale o Python 3.10+ marcando *Add python.exe to PATH* |
| `PythonLibraryNotFoundError` | Você está compilando com um Python sem biblioteca compartilhada. Use o Python oficial de python.org (o `.exe` **precisa** ser gerado no Windows) |
| `Access is denied` ao executar o build | Feche o aplicativo aberto ou rode o PowerShell como administrador |
| Antivírus bloqueando o `.exe` | Falso positivo comum do PyInstaller — adicione uma exceção |
| Janela abre e fecha rápido | Rode `python app.py` no terminal para ver a mensagem de erro |
| `Não foi possível validar online` | Sem internet/proxy: o token ainda é salvo e o bot pode ser iniciado |
