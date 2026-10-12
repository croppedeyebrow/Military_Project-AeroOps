@echo off
rem Runs inside its own "AeroOps Simulator" window, launched by ..\run-dev.bat.
rem See run-backend.bat for why this is a separate file (avoids nested quotes
rem around a path that contains spaces).
rem
rem Purpose: run-dev.bat without this produced a UI with no data to look at -
rem nothing feeds /telemetry unless something runs the simulator. 8 hours real-time
rem is long enough to leave running for a whole dev session; HttpSink
rem (simulator/simulator/sinks.py) logs and continues on failure, so it is safe to
rem start this before the backend has finished its own startup - the first few
rem frames just get a connection error on stderr and later ones succeed once the
rem backend is listening.
cd /d "%~dp0..\simulator"
if not exist .venv (
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)
call .venv\Scripts\activate.bat
python -m simulator.main run --num-drones 10 --duration-sec 28800 --real-time --ingest-url http://localhost:8000/telemetry
