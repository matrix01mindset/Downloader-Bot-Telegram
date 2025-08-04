@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    REMEDIERE PROBLEME GIT
echo ========================================
echo.

echo [STEP 1] Configurez identitatea Git...
echo.
set /p USER_EMAIL="Introdu email-ul tau GitHub (ex: nume@gmail.com): "
set /p USER_NAME="Introdu numele tau (ex: Nume Prenume): "

if "%USER_EMAIL%"=="" (
    echo [EROARE] Email-ul este obligatoriu!
    pause
    exit /b 1
)

if "%USER_NAME%"=="" (
    echo [EROARE] Numele este obligatoriu!
    pause
    exit /b 1
)

echo.
echo [INFO] Configurez Git cu:
echo Email: %USER_EMAIL%
echo Nume: %USER_NAME%
echo.

git config --global user.email "%USER_EMAIL%"
git config --global user.name "%USER_NAME%"

if errorlevel 1 (
    echo [EROARE] Nu s-a putut configura Git!
    pause
    exit /b 1
)
echo [OK] Git configurat cu succes!

echo.
echo [STEP 2] Verific statusul repository-ului...
git status

echo.
echo [STEP 3] Adaug din nou toate fisierele...
git add app.py bot.py downloader.py requirements.txt Procfile .gitignore README.md .env.example

if errorlevel 1 (
    echo [EROARE] Nu s-au putut adauga fisierele!
    pause
    exit /b 1
)
echo [OK] Fisiere adaugate!

echo.
echo [STEP 4] Creez commit-ul...
git commit -m "Initial commit: Telegram Video Downloader Bot"

if errorlevel 1 (
    echo [ATENTIE] Commit-ul a esuat - posibil ca nu sunt modificari noi
    echo Incerc sa verific branch-urile existente...
    git branch -a
else
    echo [OK] Commit creat cu succes!
)

echo.
echo [STEP 5] Verific si creez branch-ul main...
git branch
echo.
echo [INFO] Creez branch-ul main daca nu exista...
git checkout -b main 2>nul
if errorlevel 1 (
    echo [INFO] Branch-ul main exista deja sau suntem pe el
    git checkout main
) else (
    echo [OK] Branch-ul main a fost creat!
)

echo.
echo [STEP 6] Incerc upload-ul pe GitHub...
set /p REPO_URL="Introdu URL-ul repository-ului GitHub: "

if "%REPO_URL%"=="" (
    echo [EROARE] URL-ul repository-ului este obligatoriu!
    pause
    exit /b 1
)

echo.
echo [INFO] Conectez la repository...
git remote remove origin 2>nul
git remote add origin "%REPO_URL%"

echo.
echo [INFO] Incerc push pe main...
git push -u origin main

if errorlevel 1 (
    echo.
    echo [ATENTIE] Push-ul normal a esuat. Incerc cu --force...
    echo.
    git push --force origin main
    
    if errorlevel 1 (
        echo.
        echo [EROARE] Upload-ul a esuat complet!
        echo.
        echo Posibile cauze:
        echo 1. Repository-ul nu este gol
        echo 2. Nu ai permisiuni de scriere
        echo 3. URL-ul repository-ului este gresit
        echo 4. Nu esti autentificat pe GitHub
        echo.
        echo Solutii:
        echo 1. Verifica ca repository-ul este gol pe GitHub
        echo 2. Verifica ca esti logat pe GitHub in browser
        echo 3. Incearca sa creezi un Personal Access Token
        echo.
        pause
        exit /b 1
    )
fi

echo.
echo ========================================
echo     UPLOAD FINALIZAT CU SUCCES!
echo ========================================
echo.
echo Proiectul a fost incarcat pe GitHub!
echo Repository: %REPO_URL%
echo.
echo Acum poti continua cu deployment pe Render.com
echo Vezi fisierul: RENDER_DEPLOYMENT.md
echo.
pause