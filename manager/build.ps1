# =============================================================================
#  CaptureFruitHoHoHub Control Hub — script de build do .exe (Windows)
# =============================================================================
#  Uso (PowerShell, na pasta manager):
#      .\build.ps1                 -> gera dist\CaptureFruitHoHoHub-ControlHub\ (pasta)
#      .\build.ps1 -OneFile        -> gera dist\CaptureFruitHoHoHub-ControlHub.exe (arquivo unico)
#      .\build.ps1 -Python "py -3.12"   -> escolhe o interpretador Python
#
#  Requisitos: Python 3.10+ (com pip). O Node.js NAO e necessario agora:
#  o aplicativo instala o Node.js automaticamente na maquina do usuario final.
# =============================================================================

[CmdletBinding()]
param(
    [switch]$OneFile,
    [string]$Python = "python",
    [switch]$Clean,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Write-Step($message) { Write-Host "==> $message" -ForegroundColor Cyan }
function Write-Ok($message)   { Write-Host "    $message" -ForegroundColor Green }

Write-Step "Verificando o Python"
& $Python --version
if ($LASTEXITCODE -ne 0) {
    throw "Python nao encontrado. Instale o Python 3.10+ e habilite a opcao 'Add python.exe to PATH'."
}

$venvDir = Join-Path $scriptDir ".venv"
if (-not (Test-Path $venvDir)) {
    Write-Step "Criando ambiente virtual (.venv)"
    & $Python -m venv $venvDir
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Falha ao criar o ambiente virtual em $venvDir"
}
Write-Ok "Ambiente virtual pronto: $venvPython"

if (-not $SkipInstall) {
    Write-Step "Instalando dependencias (PySide6 + PyInstaller)"
    & $venvPython -m pip install --upgrade pip | Out-Null
    & $venvPython -m pip install -r (Join-Path $scriptDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependencias." }
}
Write-Ok "Dependencias instaladas"

if ($Clean) {
    Write-Step "Limpando builds anteriores"
    foreach ($dir in @("build", "dist")) {
        $path = Join-Path $scriptDir $dir
        if (Test-Path $path) { Remove-Item $path -Recurse -Force }
    }
}

Write-Step "Executando os testes de fumaca"
Push-Location $scriptDir
$env:QT_QPA_PLATFORM = "offscreen"
& $venvPython -m unittest discover -s tests
$testResult = $LASTEXITCODE
Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
Pop-Location
if ($testResult -ne 0) { Write-Host "    Testes falharam — seguindo com o build mesmo assim." -ForegroundColor Yellow }

if ($OneFile) {
    Write-Step "Gerando executavel unico (.exe)"
    $env:CFH_ONEFILE = "1"
} else {
    Write-Step "Gerando pasta de distribuicao (dist\CaptureFruitHoHoHub-ControlHub)"
    Remove-Item Env:\CFH_ONEFILE -ErrorAction SilentlyContinue
}

& $venvPython -m PyInstaller --noconfirm --clean "CaptureFruitHoHoHub-ControlHub.spec"
Remove-Item Env:\CFH_ONEFILE -ErrorAction SilentlyContinue
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o executavel." }

Write-Host ""
Write-Host "Build concluido!" -ForegroundColor Green
Write-Host ""
Write-Host "Artefatos gerados em: $(Join-Path $scriptDir 'dist')" -ForegroundColor Cyan
Write-Host ""
Write-Host "Como distribuir:" -ForegroundColor Yellow
if ($OneFile) {
    Write-Host "  - Envie apenas o arquivo dist\CaptureFruitHoHoHub-ControlHub.exe"
} else {
    Write-Host "  - Envie a pasta inteira dist\CaptureFruitHoHoHub-ControlHub\"
    Write-Host "    (o .exe depende das DLLs que ficam dentro dessa pasta)"
}
Write-Host "  - O aplicativo baixa o Node.js e as dependencias do self bot no primeiro uso."
Write-Host "  - Opcional: coloque a pasta 'selfbot' ao lado do .exe para editar os comandos"
Write-Host "    (sem ela, o app usa a copia embutida no proprio executavel)."
Write-Host ""
