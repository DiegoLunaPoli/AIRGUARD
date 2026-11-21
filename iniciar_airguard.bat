@echo off
chcp 65001 >nul
title AIRGUARD — Iniciando sistema

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║           AIRGUARD  v1.0.0                   ║
echo  ║   Sistema Experimental de Monitoreo          ║
echo  ║   Ambiental con ESP32 y Sensor MQ-2          ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ── Ubicarse en la carpeta del proyecto ──────────────────
cd /d "%~dp0"

:: ── Verificar Python ─────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python no encontrado.
    echo  Instala Python 3.8+ desde https://www.python.org/downloads/
    echo  y asegurate de marcar "Add Python to PATH".
    pause
    exit /b 1
)

echo  [OK] Python encontrado.

:: ── Verificar dependencias ────────────────────────────────
echo  [..] Verificando dependencias...

python -c "import flask"   2>nul
if %errorlevel% neq 0 (
    echo  [..] Instalando Flask...
    python -m pip install flask --quiet
)

python -c "import serial"  2>nul
if %errorlevel% neq 0 (
    echo  [..] Instalando pyserial...
    python -m pip install pyserial --quiet
)

echo  [OK] Dependencias verificadas.

:: ── Crear carpeta data si no existe ──────────────────────
if not exist "data" mkdir data

:: ── Iniciar servidor Flask ────────────────────────────────
echo.
echo  [..] Iniciando servidor AIRGUARD...
echo.
echo  ┌─────────────────────────────────────────────┐
echo  │  Dashboard:  http://127.0.0.1:5000           │
echo  │  API:        http://127.0.0.1:5000/api/status│
echo  │                                              │
echo  │  Presiona Ctrl+C para detener el servidor.  │
echo  └─────────────────────────────────────────────┘
echo.
echo  Abre tu navegador y navega a http://127.0.0.1:5000
echo.

:: Esperar 1 segundo y abrir el navegador automaticamente
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000"

:: Iniciar Flask
python backend\servidor.py

echo.
echo  Servidor detenido.
pause
