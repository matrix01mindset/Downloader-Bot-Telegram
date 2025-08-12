# 🚀 Ghid Complet Deployment pe Render.com

**Telegram Video Downloader Bot - Versiune Securizată**

## 📋 Cerințe Preliminare

### 1. Conturi Necesare
- ✅ Cont GitHub (pentru repository)
- ✅ Cont Render.com (gratuit)
- ✅ Bot Telegram creat via @BotFather

### 2. Verificare Locală
```bash
# Verifică că toate fișierele sunt prezente
ls -la
# Trebuie să vezi: app.py, requirements.txt, Dockerfile, render.yaml

# Verifică că .env nu este în repository
git status
# .env NU trebuie să apară în lista de fișiere
```

## 🔧 Pasul 1: Pregătire Repository GitHub

### Creează Repository
```bash
# Inițializează Git (dacă nu e deja)
git init

# Adaugă toate fișierele (fără .env)
git add .
git commit -m "Initial commit - Secure Telegram Bot"

# Conectează la GitHub
git remote add origin https://github.com/USERNAME/telegram-video-downloader.git
git branch -M main
git push -u origin main
```

### Verifică .gitignore
```bash
# Asigură-te că .env este exclus
cat .gitignore | grep ".env"
# Trebuie să vezi: .env
```

## 🌐 Pasul 2: Creare Serviciu Render

### 2.1 Conectare Repository
1. Mergi pe [render.com](https://render.com)
2. Click **"New +"** → **"Web Service"**
3. Conectează repository-ul GitHub
4. Selectează repository-ul `telegram-video-downloader`

### 2.2 Configurare Serviciu
```yaml
# Render va detecta automat render.yaml
# Verifică setările:
Name: telegram-video-downloader
Environment: Docker
Region: Frankfurt (sau cel mai apropiat)
Branch: main
Build Command: (automat din render.yaml)
Start Command: (automat din render.yaml)
```

## 🔐 Pasul 3: Configurare Variabile de Mediu

### 3.1 Variabile OBLIGATORII
În Render Dashboard → Environment:

```bash
# OBLIGATORIU - Token-ul botului
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789

# OBLIGATORIU - URL-ul webhook-ului (va fi generat de Render)
WEBHOOK_URL=https://telegram-video-downloader-xxxx.onrender.com
```

### 3.2 Variabile OPȚIONALE
```bash
# Configurare generală
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=50
DOWNLOAD_TIMEOUT=300
RATE_LIMIT_PER_MINUTE=30
DEBUG_MODE=false
ENABLE_DETAILED_LOGS=true

# Platforme activate/dezactivate
FACEBOOK=true
INSTAGRAM=true
TIKTOK=true
TWITTER=true
YOUTUBE=false
```

### 3.3 Cum să Setezi Variabilele
1. În Render Dashboard → serviciul tău
2. Tab **"Environment"**
3. Click **"Add Environment Variable"**
4. Adaugă fiecare variabilă (Key = Value)
5. Click **"Save Changes"**

## 🚀 Pasul 4: Deployment

### 4.1 Deploy Automat
```bash
# Render va începe deployment-ul automat după configurare
# Monitorizează în Dashboard → "Logs"
```

### 4.2 Verificare Deployment
```bash
# Verifică status în browser
https://YOUR-SERVICE-NAME.onrender.com/health

# Răspuns așteptat:
{
  "status": "healthy",
  "timestamp": "2025-01-27"
}
```

## 🔗 Pasul 5: Configurare Webhook

### 5.1 Setare Automată
```bash
# Accesează endpoint-ul de configurare
https://YOUR-SERVICE-NAME.onrender.com/set_webhook

# Răspuns așteptat:
{
  "status": "success",
  "webhook_url": "https://YOUR-SERVICE-NAME.onrender.com/webhook"
}
```

### 5.2 Verificare Webhook
```bash
# Testează bot-ul în Telegram
# Trimite /start la bot
# Trimite un link de video pentru testare
```

## 🧪 Comenzi de Testare Locală

### Înainte de Deployment
```bash
# 1. Creează .env local
cp .env.example .env
# Editează .env cu token-ul real

# 2. Instalează dependențele
pip install -r requirements.txt

# 3. Rulează testele
python test_local.py

# 4. Testează aplicația local
python app.py
# Accesează: http://localhost:5000/health
```

### Testare Funcționalitate
```bash
# Test download (fără bot)
python -c "
from downloader import download_video
result = download_video('https://www.tiktok.com/@test/video/123')
print(result)
"

# Test platforme
python -c "
from platforms.tiktok import TikTokDownloader
downloader = TikTokDownloader()
print(downloader.can_handle('https://tiktok.com/@test/video/123'))
"
```

## 🔍 Monitorizare și Debugging

### Logs în Render
```bash
# În Render Dashboard
1. Mergi la serviciul tău
2. Tab "Logs"
3. Monitorizează pentru erori
```

### Endpoint-uri de Debug
```bash
# Status general
https://YOUR-SERVICE-NAME.onrender.com/

# Verificare sănătate
https://YOUR-SERVICE-NAME.onrender.com/health

# Debug variabile de mediu
https://YOUR-SERVICE-NAME.onrender.com/debug

# Test ping
https://YOUR-SERVICE-NAME.onrender.com/ping
```

## ⚠️ Troubleshooting

### Probleme Comune

#### 1. Bot nu răspunde
```bash
# Verifică token-ul
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Verifică webhook-ul
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

#### 2. Erori de download
```bash
# Verifică logs în Render Dashboard
# Caută erori de tip:
# - "Platform not supported"
# - "Download timeout"
# - "File too large"
```

#### 3. Probleme de memorie
```bash
# În render.yaml, schimbă plan-ul:
plan: starter  # în loc de free
```

### Comenzi de Debug
```bash
# Resetează webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://YOUR-SERVICE-NAME.onrender.com/webhook"

# Verifică status serviciu
curl https://YOUR-SERVICE-NAME.onrender.com/health
```

## 🔒 Securitate în Producție

### Verificări Finale
- ✅ `.env` NU este în repository
- ✅ Token-ul este setat doar în Render Environment Variables
- ✅ Webhook URL folosește HTTPS
- ✅ Logs nu conțin informații sensibile

### Rotație Token
```bash
# Pentru a schimba token-ul:
1. Generează token nou în @BotFather
2. Actualizează în Render Environment Variables
3. Redeploy serviciul
4. Revocă token-ul vechi
```

## 📊 Optimizări Producție

### Performance
```bash
# În render.yaml, pentru trafic mare:
plan: starter
instanceCount: 2
autoscaling:
  minInstances: 1
  maxInstances: 3
```

### Monitoring
```bash
# Adaugă în Environment Variables:
ENABLE_DETAILED_LOGS=true
LOG_LEVEL=INFO

# Pentru debugging:
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

---

## 🎯 Checklist Final

- [ ] Repository GitHub creat și sincronizat
- [ ] Serviciu Render configurat
- [ ] Variabile de mediu setate
- [ ] Deployment reușit
- [ ] Webhook configurat
- [ ] Bot testât și funcțional
- [ ] Logs monitorizate
- [ ] Securitate verificată

**🎉 Bot-ul este gata pentru producție!**

Pentru suport: verifică logs în Render Dashboard sau contactează echipa de dezvoltare.