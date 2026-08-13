@echo off
REM ============================================================
REM  stop.bat — Arrete STOCK APP proprement (Windows 10)
REM  Ferme le processus Python qui ecoute sur le port 5000.
REM ============================================================
title STOCK APP - Arret du serveur

echo Recherche du processus STOCK APP (port 5000)...

set FOUND=0
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo Arret du processus PID %%P...
    taskkill /F /PID %%P >nul 2>nul
    set FOUND=1
)

if "%FOUND%"=="1" (
    echo STOCK APP a ete arrete.
) else (
    echo Aucun processus STOCK APP actif trouve sur le port 5000.
    echo Vous pouvez aussi simplement fermer la fenetre de start.bat.
)

pause
