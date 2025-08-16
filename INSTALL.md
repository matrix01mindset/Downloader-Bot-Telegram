# 📥 Ghid de Instalare - Telegram Video Downloader Bot

## 🐍 1. Instalarea Python

### Windows

**Opțiunea A: De pe python.org (Recomandat)**
1. Mergi la [python.org/downloads](https://www.python.org/downloads/)
2. Descarcă Python 3.9+ (versiunea cea mai recentă)
3. **IMPORTANT:** Bifează "Add Python to PATH" în timpul instalării
4. Rulează installer-ul și urmează instrucțiunile
5. Verifică instalarea:
   ```cmd
   python --version
   pip --version
   ```

**Opțiunea B: Din Microsoft Store**
1. Deschide Microsoft Store
2. Caută "Python 3.11" sau "Python 3.12"
3. Instalează versiunea oficială
4. Verifică instalarea în Command Prompt

**Opțiunea C: Folosind Chocolatey**
```powershell
# Instalează Chocolatey mai întâi (dacă nu îl ai)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Instalează Python
choco install python
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### macOS
```bash
# Folosind Homebrew
brew install python

# Sau descarcă de pe python.org
```

## 📦 2. Instalarea Dependențelor

### Pas 1: Navighează în directorul proiectului
```cmd
cd "C:\Users\matri\Desktop\Downloader Bot telegram"
```

### Pas 2: Creează mediu virtual (Recomandat)
```cmd
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Pas 3: Instalează dependențele
```cmd
pip install -r requirements.txt
```

### Pas 4: Verifică instalarea
```cmd
python test_downloader.py
```

## 🤖 3. Configurarea Botului Telegram

### Pas 1: Creează Bot
1. Deschide [@BotFather](https://t.me/botfather) pe Telegram
2. Trimite `/newbot`
3. Urmează instrucțiunile pentru nume și username
4. Salvează token-ul primit

### Pas 2: Setează Token-ul

**Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

**Sau creează fișier .env:**
```bash
# Copiază .env.example ca .env
copy .env.example .env

# Editează .env și adaugă token-ul
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

## 🚀 4. Rularea Botului

### Rulare Locală (pentru testare)
```cmd
python bot.py
```

### Rulare cu Webhook (pentru hosting)
```cmd
python app.py
```

## 🌐 5. Deployment pe Hosting Gratuit

### Render.com
1. Creează cont pe [render.com](https://render.com)
2. Conectează repository-ul GitHub
3. Creează "Web Service"
4. Setează:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Adaugă variabile de mediu:
   - `TELEGRAM_BOT_TOKEN`
   - `WEBHOOK_URL` (URL-ul aplicației Render)
6. Deploy și accesează `/set_webhook`

### Railway.app
1. Creează cont pe [railway.app](https://railway.app)
2. "Deploy from GitHub repo"
3. Adaugă variabile de mediu
4. Deploy automat

### Replit
1. Creează cont pe [replit.com](https://replit.com)
2. Importă din GitHub
3. Adaugă token în "Secrets"
4. Rulează `python bot.py`

## 🔧 6. Depanare

### Python nu este găsit
```cmd
# Verifică dacă Python este în PATH
where python

# Sau încearcă
py --version
python3 --version
```

### Erori de instalare pip
```cmd
# Actualizează pip
python -m pip install --upgrade pip

# Instalează cu --user dacă ai probleme de permisiuni
pip install --user -r requirements.txt
```

### Erori de import
```cmd
# Verifică că ești în mediul virtual corect
which python  # Linux/Mac
where python  # Windows

# Reinstalează dependențele
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### Bot nu răspunde
1. Verifică că token-ul este corect
2. Verifică că botul rulează
3. Pentru webhook, verifică că URL-ul este setat
4. Verifică logs-urile pentru erori

## 📋 7. Checklist Final

- [ ] Python 3.9+ instalat
- [ ] Dependențele instalate (`pip install -r requirements.txt`)
- [ ] Bot Telegram creat cu @BotFather
- [ ] Token setat în variabilele de mediu
- [ ] Testul `python test_downloader.py` trece
- [ ] Botul rulează local cu `python bot.py`
- [ ] (Opțional) Deployment pe platformă de hosting
- [ ] (Pentru hosting) Webhook setat cu `/set_webhook`

## 🆘 Suport

Dacă întâmpini probleme:
1. Verifică că toate dependențele sunt instalate
2. Verifică că Python este în PATH
3. Verifică că token-ul este setat corect
4. Rulează `python test_downloader.py` pentru diagnostic
5. Verifică logs-urile pentru erori specifice

---

**Succes cu botul tău! 🎉**