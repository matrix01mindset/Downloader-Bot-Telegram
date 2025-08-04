# 🚀 Comenzi Git pentru încărcarea pe GitHub

## ⚠️ REZOLVAREA PROBLEMELOR ÎNTÂLNITE

### Problema 1: Git nu știe cine ești
```bash
# Configurează email-ul și numele (înlocuiește cu datele tale)
git config --global user.email "numele.tau@gmail.com"
git config --global user.name "Numele Tau"
```

### Problema 2: Branch-ul main nu există
```bash
# Verifică ce branch-uri ai
git branch

# Creează și schimbă pe branch-ul main
git checkout -b main
```

## 📋 Pași COMPLETI pentru rezolvare

### 1. Configurează Git (OBLIGATORIU)
```bash
# Înlocuiește cu datele tale reale
git config --global user.email "numele.tau@gmail.com"
git config --global user.name "Numele Tau"
```

### 2. Verifică statusul
```bash
git status
```

### 3. Adaugă fișierele din nou
```bash
git add app.py bot.py downloader.py requirements.txt Procfile .gitignore README.md .env.example
```

### 4. Creează commit-ul
```bash
git commit -m "Initial commit: Telegram Video Downloader Bot"
```

### 5. Creează branch-ul main
```bash
# Verifică branch-urile existente
git branch

# Creează și schimbă pe main
git checkout -b main
```

### 6. Conectează la GitHub
```bash
# Înlocuiește cu URL-ul tău real
git remote add origin https://github.com/matrix01mindset/Downloader-Bot-Telegram.git
```

### 7. Încarcă pe GitHub
```bash
# Încearcă push normal
git push -u origin main

# Dacă nu merge, forțează (ATENȚIE: șterge istoricul)
git push --force origin main
```

## 🔧 Comenzi alternative pentru probleme

### Dacă repository-ul nu este gol:
```bash
# Descarcă conținutul existent
git pull origin main --allow-unrelated-histories

# Apoi încarcă
git push origin main
```

### Dacă ai probleme de autentificare:
```bash
# Folosește Personal Access Token în loc de parolă
# Mergi pe GitHub → Settings → Developer settings → Personal access tokens
# Creează un token nou și folosește-l ca parolă
```

### Pentru a șterge și recrea totul:
```bash
# Șterge .git folder
rmdir /s .git

# Începe din nou
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin URL_REPOSITORY
git push -u origin main
```

## ⚡ Secvența COMPLETĂ (copy-paste):

```bash
# 1. Configurează Git (înlocuiește cu datele tale!)
git config --global user.email "numele.tau@gmail.com"
git config --global user.name "Numele Tau"

# 2. Verifică statusul
git status

# 3. Adaugă fișierele
git add app.py bot.py downloader.py requirements.txt Procfile .gitignore README.md .env.example

# 4. Creează commit
git commit -m "Initial commit: Telegram Video Downloader Bot"

# 5. Creează branch main
git checkout -b main

# 6. Conectează la GitHub (înlocuiește URL-ul!)
git remote add origin https://github.com/matrix01mindset/Downloader-Bot-Telegram.git

# 7. Încarcă pe GitHub
git push -u origin main
```

## 🎯 Verificare finală

După upload, verifică pe GitHub că toate fișierele sunt acolo:
- ✅ app.py
- ✅ bot.py
- ✅ downloader.py
- ✅ requirements.txt
- ✅ Procfile
- ✅ .gitignore
- ✅ README.md
- ✅ .env.example

## 📱 Următorul pas: Deployment

După încărcarea cu succes pe GitHub, continuă cu deployment pe Render.com folosind ghidul din `RENDER_DEPLOYMENT.md`.

---
**💡 Tip:** Dacă întâmpini în continuare probleme, folosește scriptul `fix_git_upload.bat` care automatizează toate aceste comenzi!