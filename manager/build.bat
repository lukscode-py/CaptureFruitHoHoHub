@echo off
REM ===========================================================================
REM  CaptureFruitHoHoHub Control Hub - atalho de build para o Windows
REM  Gera a pasta dist\CaptureFruitHoHoHub-ControlHub com o .exe dentro.
REM  Para um arquivo unico: build.bat --onefile
REM ===========================================================================
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "EXTRA="
if /I "%~1"=="--onefile" set "EXTRA=-OneFile"
if /I "%~1"=="-onefile" set "EXTRA=-OneFile"
if /I "%~1"=="/onefile" set "EXTRA=-OneFile"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%build.ps1" %EXTRA%
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Build finalizado com erros. Codigo: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
