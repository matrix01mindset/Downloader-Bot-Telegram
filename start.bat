@echo off
echo ========================================
echo   TELEGRAM VIDEO DOWNLOADER BOT
echo ========================================
echo.

REM Verifică dacă Python este instalat
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python nu este instalat sau nu este in PATH!
    echo.
    echo 📥 Te rog sa instalezi Python de pe:
    echo    https://www.python.org/downloads/
    echo.
    echo ⚠️  IMPORTANT: Bifează "Add Python to PATH" la instalare!
    echo.
    pause
    exit /b 1
)

echo ✅ Python găsit!
python --version
echo.

REM Verifică dacă dependențele sunt instalate
echo 📦 Verific dependențele...
pip show python-telegram-bot >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Dependențele nu sunt instalate!
    echo 📥 Instalez dependențele...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Eroare la instalarea dependențelor!
        pause
        exit /b 1
    )
)

echo ✅ Dependențele sunt instalate!
echo.

REM Verifică token-ul
if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo ⚠️  TELEGRAM_BOT_TOKEN nu este setat!
    echo.
    echo 🤖 Pentru a seta token-ul:
    echo    1. Deschide @BotFather pe Telegram
    echo    2. Creează un bot nou cu /newbot
    echo    3. Copiază token-ul primit
    echo    4. Rulează: set TELEGRAM_BOT_TOKEN=your_token_here
    echo.
    set /p token="Introdu token-ul botului (sau apasă Enter pentru a continua fără): "
    if not "%token%"=="" (
        set TELEGRAM_BOT_TOKEN=%token%
        echo ✅ Token setat temporar!
    )
    echo.
)

REM Meniu principal
:menu
echo ========================================
echo   OPȚIUNI DISPONIBILE:
echo ========================================
echo 1. Rulează botul local (polling)
echo 2. Rulează serverul web (webhook)
echo 3. Testează funcționalitatea
echo 4. Afișează informații despre bot
echo 5. Ieșire
echo.
set /p choice="Alege o opțiune (1-5): "

if "%choice%"=="1" goto run_bot
if "%choice%"=="2" goto run_server
if "%choice%"=="3" goto test_bot
if "%choice%"=="4" goto bot_info
if "%choice%"=="5" goto exit

echo ❌ Opțiune invalidă!
goto menu

:run_bot
echo.
echo 🤖 Pornesc botul în modul polling...
echo 📱 Testează botul pe Telegram!
echo 🛑 Apasă Ctrl+C pentru a opri
echo.
python bot.py
goto menu

:run_server
echo.
echo 🌐 Pornesc serverul web...
echo 🔗 Accesează http://localhost:5000 pentru status
echo 🛑 Apasă Ctrl+C pentru a opri
echo.
python app.py
goto menu

:test_bot
echo.
echo 🧪 Rulez testele...
echo.
python test_downloader.py
echo.
pause
goto menu

:bot_info
echo.
echo ========================================
echo   INFORMAȚII BOT
echo ========================================
if not "%TELEGRAM_BOT_TOKEN%"=="" (
    echo ✅ Token setat: %TELEGRAM_BOT_TOKEN:~0,10%...
) else (
    echo ❌ Token nu este setat
)
echo 📁 Director: %CD%
echo 🐍 Python: 
python --version
echo 📦 Dependențe: requirements.txt
echo.
echo 📖 Pentru mai multe informații, vezi:
echo    - README.md
echo    - INSTALL.md
echo.
pause
goto menu

:exit
echo.
echo 👋 La revedere!
echo.
pause
exit /b 0