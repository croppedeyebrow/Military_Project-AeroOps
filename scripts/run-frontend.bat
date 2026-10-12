@echo off
rem Runs inside its own "AeroOps Frontend" window, launched by ..\run-dev.bat.
rem See run-backend.bat for why this is a separate file (avoids nested quotes
rem around a path that contains spaces).
cd /d "%~dp0..\frontend"
if not exist node_modules (
    yarn install
)
yarn dev
