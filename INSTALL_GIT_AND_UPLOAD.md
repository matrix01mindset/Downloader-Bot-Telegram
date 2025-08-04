# 📦 Ghid pentru Instalarea Git și Upload pe GitHub

## 🔧 Pasul 1: Instalează Git

### Descarcă Git pentru Windows:
1. Mergi la: https://git-scm.com/download/win
2. Descarcă versiunea pentru Windows
3. Rulează installer-ul și urmează pașii
4. **IMPORTANT**: În timpul instalării, alege "Git from the command line and also from 3rd-party software"

### Verifică instalarea:
```bash
git --version
```

## 🚀 Pasul 2: Upload pe GitHub

### Opțiunea A: Folosește batch-ul automat
După instalarea Git, rulează:
```cmd
.\upload_to_github.bat
```

### Opțiunea B: Upload manual

1. **Creează repository pe GitHub**:
   - Mergi pe github.com
   - Click pe "+" → "New repository"
   - Nume: `telegram-video-downloader`
   - Bifează "Add a README file" = **NU**
   - Click "Create repository"

2. **Rulează comenzile în terminal**:
```bash
# Inițializează Git
git init

# Adaugă fișierele
git add .

# Creează commit-ul
git commit -m "Add interactive menu with inline buttons and enhanced UX"

# Conectează la GitHub (înlocuiește cu URL-ul tău)
git remote add origin https://github.com/USERNAME/REPO-NAME.git

# Upload pe GitHub
git branch -M main
git push -u origin main
```

## 📋 Fișierele care vor fi încărcate:

- ✅ `bot.py` - Bot principal cu meniu interactiv
- ✅ `app.py` - Server pentru Render
- ✅ `downloader.py` - Logica de descărcare
- ✅ `requirements.txt` - Dependențe Python
- ✅ `Procfile` - Configurare Render
- ✅ `README.md` - Documentație completă
- ✅ `.gitignore` - Fișiere ignorate
- ✅ `.env.example` - Template variabile

## 🔄 Următorii Pași

După upload pe GitHub:
1. **Deploy pe Render**: Vezi `RENDER_QUICK_SETUP.md`
2. **Configurează token-ul**: Adaugă `TELEGRAM_BOT_TOKEN` în Render
3. **Testează botul**: Trimite `/start` în Telegram

## 🆘 Probleme Comune

### Git nu este recunoscut
- Restart terminal după instalare
- Verifică că Git este în PATH
- Reinstalează Git cu opțiunea "command line"

### Eroare la push
- Verifică că repository-ul GitHub este gol
- Folosește `git push --force origin main` dacă e necesar
- Verifică permisiunile de scriere

### Token invalid
- Verifică token-ul în BotFather
- Asigură-te că nu are spații extra
- Regenerează token-ul dacă e necesar

---

**💡 Tip**: După instalarea Git, poți folosa `upload_to_github.bat` pentru upload-uri viitoare!