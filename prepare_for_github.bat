@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   PREGATIRE PENTRU GITHUB DEPLOYMENT
echo ========================================
echo.

echo [*] Curatam fisierele temporare...
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "*.pyc" del /q "*.pyc"
if exist "test_*.py" (
    echo [!] Fisierele de test vor fi excluse din deployment
)

echo.
echo [+] Fisiere care vor fi incarcate pe GitHub:
echo [+] app.py
echo [+] bot.py  
echo [+] downloader.py
echo [+] requirements.txt
echo [+] Procfile
echo [+] .gitignore
echo [+] README.md
echo [+] .env.example

echo.
echo [-] Fisiere care NU vor fi incarcate:
echo [-] test_downloader.py
echo [-] test_platforms.py
echo [-] start.bat
echo [-] prepare_for_github.bat
echo [-] __pycache__/
echo [-] *.pyc

echo.
echo [?] Verifica ca ai:
echo   1. [+] Cont GitHub creat
echo   2. [+] Token bot Telegram de la @BotFather
echo   3. [+] Cont Render.com creat

echo.
echo [OK] Toate fisierele sunt pregatite!
echo [>>] Urmatorul pas: Incarca pe GitHub si deploy pe Render
echo [>>] Urmeaza instructiunile din RENDER_DEPLOYMENT.md

echo.
pause