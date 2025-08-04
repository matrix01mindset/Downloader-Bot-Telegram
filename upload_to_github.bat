@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    TELEGRAM VIDEO DOWNLOADER BOT
echo    Upload automat pe GitHub
echo ========================================
echo.

:: Verifica daca Git este instalat
set "GIT_PATH=C:\Program Files\Git\bin\git.exe"
if not exist "%GIT_PATH%" (
    echo [EROARE] Git nu este instalat!
    echo Descarca Git de la: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [INFO] Git detectat cu succes!
echo.

:: Cere utilizatorului URL-ul repository-ului
set /p REPO_URL="Introdu URL-ul repository-ului GitHub (ex: https://github.com/username/repo.git): "

if "%REPO_URL%"=="" (
    echo [EROARE] URL-ul repository-ului este obligatoriu!
    pause
    exit /b 1
)

echo.
echo [INFO] Incepem procesul de upload...
echo.

:: Initializeaza Git daca nu exista deja
if not exist ".git" (
    echo [STEP 1] Initializam repository-ul Git local...
    "%GIT_PATH%" init
    if errorlevel 1 (
        echo [EROARE] Nu s-a putut initializa Git!
        pause
        exit /b 1
    )
    echo [OK] Git initializat cu succes!
) else (
    echo [INFO] Repository Git exista deja.
)

echo.
echo [STEP 2] Adaugam fisierele necesare...

:: Adauga fisierele importante
"%GIT_PATH%" add app.py
"%GIT_PATH%" add bot.py
"%GIT_PATH%" add downloader.py
"%GIT_PATH%" add requirements.txt
"%GIT_PATH%" add Procfile
"%GIT_PATH%" add .gitignore
"%GIT_PATH%" add README.md
"%GIT_PATH%" add .env.example

if errorlevel 1 (
    echo [EROARE] Nu s-au putut adauga fisierele!
    pause
    exit /b 1
)
echo [OK] Fisiere adaugate cu succes!

echo.
echo [STEP 3] Cream commit-ul...
"%GIT_PATH%" commit -m "Add interactive menu with inline buttons and enhanced UX"
if errorlevel 1 (
    echo [ATENTIE] Commit-ul a esuat (posibil ca nu sunt modificari noi)
) else (
    echo [OK] Commit creat cu succes!
)

echo.
echo [STEP 4] Conectam la repository-ul GitHub...
"%GIT_PATH%" remote remove origin >nul 2>&1
"%GIT_PATH%" remote add origin "%REPO_URL%"
if errorlevel 1 (
    echo [EROARE] Nu s-a putut conecta la repository!
    pause
    exit /b 1
)
echo [OK] Conectat la repository!

echo.
echo [STEP 5] Incarcam pe GitHub...
"%GIT_PATH%" branch -M main
"%GIT_PATH%" push -u origin main
if errorlevel 1 (
    echo [EROARE] Upload-ul a esuat!
    echo.
    echo Posibile solutii:
    echo 1. Verifica ca repository-ul este gol
    echo 2. Verifica ca ai permisiuni de scriere
    echo 3. Incearca sa rulezi manual: "%GIT_PATH%" push --force origin main
    pause
    exit /b 1
)

echo.
echo ========================================
echo     UPLOAD FINALIZAT CU SUCCES!
echo ========================================
echo.
echo Proiectul a fost incarcat pe GitHub!
echo Acum poti continua cu deployment pe Render.com
echo.
echo Urmatoarele fisiere au fost incarcate:
echo - app.py
echo - bot.py  
echo - downloader.py
echo - requirements.txt
echo - Procfile
echo - .gitignore
echo - README.md
echo - .env.example
echo.
echo Pentru deployment pe Render, vezi: RENDER_DEPLOYMENT.md
echo.
pause