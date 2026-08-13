@echo off
REM ============================================================
REM  start.bat — Lance STOCK APP (Windows 10)
REM ============================================================
title STOCK APP - Serveur local

cd /d "%~dp0"

echo ============================================
echo   STOCK APP - V1 TEST
echo ============================================
echo.

REM Verifier que Python 3 est installe
where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python n'a pas ete trouve dans le PATH.
    echo Installez Python 3.13 ^(voir README.md, section Installation^)
    echo puis relancez ce fichier.
    pause
    exit /b 1
)

REM Creer un environnement isole pour l'application si necessaire.
set PYTHON=.venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo Creation de l'environnement Python...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Creation de l'environnement Python impossible.
        pause
        exit /b 1
    )
)

"%PYTHON%" -c "import flask, werkzeug" >nul 2>nul
if errorlevel 1 (
    echo Installation des dependances essentielles...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERREUR] Installation de Flask impossible.
        echo Verifiez la connexion Internet puis relancez ce fichier.
        pause
        exit /b 1
    )
)

REM L'impression directe est optionnelle. Le navigateur reste utilisable sans elle.
if exist "requirements-printer.txt" (
    "%PYTHON%" -c "import win32print" >nul 2>nul
    if errorlevel 1 (
        echo Installation du support imprimante...
        "%PYTHON%" -m pip install -r requirements-printer.txt
    )
)

echo.
echo Demarrage du serveur local...
echo Ouvrez votre navigateur a l'adresse : http://127.0.0.1:5000
echo Identifiant : admin   /   Mot de passe : admin123
echo.
echo Laissez cette fenetre ouverte pendant l'utilisation de l'application.
echo Fermez-la ou appuyez sur Ctrl+C pour arreter le serveur.
echo.

"%PYTHON%" app.py

pause
