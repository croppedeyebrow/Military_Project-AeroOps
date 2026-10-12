@echo off
rem run-dev.bat - backend+frontend local dev launcher.
rem
rem Purpose: the repo root README documents two ways to run this project locally -
rem a full "docker compose up --build" (rebuilds images every time, slow to iterate
rem on) and a faster per-service path (Postgres/Redis in Docker, backend/frontend run
rem directly with --reload/HMR). This script automates that second, faster path
rem exactly as backend/README.md and frontend/README.md describe it, so day-to-day
rem dev doesn't need four manual terminals.
rem
rem Why two separate "start" windows instead of one script blocking on both: backend
rem and frontend are long-running dev servers with their own live logs (uvicorn
rem --reload, vite HMR) - keeping them in separate windows lets you watch/restart one
rem without killing the other.
rem
rem This file is intentionally plain ASCII (no em-dashes, no non-English text):
rem cmd.exe reads .bat files using the system codepage, not UTF-8, so special
rem punctuation or Korean text here would render as garbled "??" on a machine whose
rem codepage doesn't match (the same class of bug hit in simulator/requirements.txt).

setlocal enabledelayedexpansion
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [1/5] Checking .env files (copied from .env.example if missing)...
if not exist "backend\.env" copy "backend\.env.example" "backend\.env" >nul
if not exist "frontend\.env" copy "frontend\.env.example" "frontend\.env" >nul
if not exist "infra\.env" copy "infra\.env.example" "infra\.env" >nul

echo [2/5] Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker daemon not responding - attempting to start Docker Desktop...
    set "DOCKER_DESKTOP_EXE=C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if not exist "!DOCKER_DESKTOP_EXE!" (
        echo Could not find "!DOCKER_DESKTOP_EXE!".
        echo Please start Docker Desktop yourself, then re-run this script.
        exit /b 1
    )
    start "" "!DOCKER_DESKTOP_EXE!"
    echo Waiting for Docker to become ready - this can take a minute...
    set WAITED=0
    :waitloop
    timeout /t 5 /nobreak >nul
    set /a WAITED+=5
    docker info >nul 2>&1
    if not errorlevel 1 goto dockerready
    if !WAITED! GEQ 120 (
        echo Docker did not become ready within 120 seconds.
        echo Please start Docker Desktop manually, wait for it, then re-run this script.
        exit /b 1
    )
    goto waitloop
    :dockerready
    echo Docker is ready.
)

echo [3/5] Starting Postgres/Redis (Docker) - not api/web, those run locally below...
docker compose -f infra\docker-compose.yml --env-file infra\.env up -d postgres redis
if errorlevel 1 (
    echo.
    echo Docker Compose failed to start postgres/redis - see the error above.
    exit /b 1
)

echo [4/5] Launching backend (uvicorn --reload) in a new window...
rem Each step (venv setup, migrate, run) lives in scripts\run-backend.bat instead
rem of being inlined here - see that file's header comment for why (nested-quote
rem bug when the repo path contains spaces).
start "AeroOps Backend" cmd /k "%ROOT%scripts\run-backend.bat"

echo [5/5] Launching frontend (yarn dev) in a new window...
start "AeroOps Frontend" cmd /k "%ROOT%scripts\run-frontend.bat"

echo.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Each dev server runs in its own window - close that window (or Ctrl+C inside
echo it) to stop it. To stop Postgres/Redis: docker compose -f infra\docker-compose.yml down
endlocal
