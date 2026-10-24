@echo off
rem Runs inside its own "AeroOps Backend" window, launched by ..\run-dev.bat via
rem `start "AeroOps Backend" cmd /k "<this file>"`.
rem
rem Why this is a separate file instead of an inline multi-step command string:
rem the repo path contains spaces ("Military Project"), so `cd /d "<path>"` needs
rem its own quotes. Nesting that inside an outer `cmd /k "...multiple steps..."`
rem string creates unescaped nested quotes, which cmd.exe mis-parses (the backend
rem silently never starts, with no visible error — this is exactly what happened
rem the first time this launcher was written as one inline command). Giving each
rem step its own file means each needs only one, non-nested, pair of quotes.
cd /d "%~dp0..\legacy-backend"
if not exist .venv (
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements-dev.txt
)
call .venv\Scripts\activate.bat
alembic upgrade head
uvicorn app.main:app --reload
