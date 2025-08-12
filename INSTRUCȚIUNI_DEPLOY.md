# 🚀 INSTRUCȚIUNI COMPLETE - Deploy Telegram Video Downloader Bot

## 📋 Cuprins
1. [Pregătire Mediu Local](#1-pregătire-mediu-local)
2. [Configurare Variabile de Mediu](#2-configurare-variabile-de-mediu)
3. [Testare Locală](#3-testare-locală)
4. [Deploy pe Render](#4-deploy-pe-render)
5. [Verificare și Monitorizare](#5-verificare-și-monitorizare)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Pregătire Mediu Local

### 1.1 Verificare Cerințe Sistem
```bash
# Verifică versiunea Python (necesită 3.11+)
python --version

# Verifică pip
pip --version
```

### 1.2 Instalare Dependențe
```bash
# Instalează toate dependențele
pip install -r requirements.txt

# Sau instalează manual pachetele principale:
pip install flask python-telegram-bot yt-dlp requests cryptography python-dotenv
```

### 1.3 Verificare Instalare
```bash
# Verifică că toate pachetele sunt instalate
pip list | grep -E "flask|telegram|yt-dlp|requests|cryptography|dotenv"
```

---

## 2. Configurare Variabile de Mediu

### 2.1 Creează Fișierul .env
```bash
# Copiază template-ul
copy .env.example .env

# Sau pe Linux/Mac:
cp .env.example .env
```

### 2.2 Configurează Token-ul Telegram
1. Mergi la [@BotFather](https://t.me/BotFather) pe Telegram
2. Creează un bot nou cu `/newbot`
3. Copiază token-ul primit
4. Editează `.env` și înlocuiește `your_telegram_bot_token_here` cu token-ul real

### 2.3 Exemplu Fișier .env
```env
# Token-ul botului Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# URL pentru webhook (va fi completat la deploy)
WEBHOOK_URL=https://your-app-name.onrender.com

# Port pentru server
PORT=10000

# Configurări opționale
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=45
DOWNLOAD_TIMEOUT=300
```

---

## 3. Testare Locală

### 3.1 Rulează Testele Automate
```bash
# Rulează scriptul de testare
python test_local.py
```

### 3.2 Testare Manuală
```bash
# Pornește botul local
python app.py
```

### 3.3 Testare Funcționalitate
1. Deschide Telegram și găsește botul tău
2. Trimite `/start` pentru a verifica că botul răspunde
3. Testează cu URL-uri de pe platforme suportate:
   - TikTok: `https://www.tiktok.com/@user/video/123`
   - Instagram: `https://www.instagram.com/p/ABC123/`
   - Facebook: `https://www.facebook.com/watch?v=123`
   - Twitter: `https://twitter.com/user/status/123`

---

## 4. Deploy pe Render

### 4.1 Pregătire Repository
```bash
# Asigură-te că .env nu este în git
echo ".env" >> .gitignore
echo "*.log" >> .gitignore
echo "temp_downloads/" >> .gitignore

# Commit modificările
git add .
git commit -m "Securizare bot și pregătire pentru deploy"
git push origin main
```

### 4.2 Creează Serviciul pe Render
1. Mergi la [render.com](https://render.com) și loghează-te
2. Click pe "New" → "Web Service"
3. Conectează repository-ul GitHub
4. Configurează serviciul:
   - **Name**: `telegram-video-downloader-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Plan**: Free (pentru început)

### 4.3 Configurează Variabilele de Mediu pe Render
1. În dashboard-ul serviciului, mergi la "Environment"
2. Adaugă următoarele variabile:
   ```
   TELEGRAM_BOT_TOKEN = [token-ul tău real]
   WEBHOOK_URL = https://your-app-name.onrender.com
   PORT = 10000
   PYTHON_VERSION = 3.11.9
   PYTHONUNBUFFERED = 1
   PYTHONDONTWRITEBYTECODE = 1
   ```

### 4.4 Deploy Automat
1. Render va detecta `render.yaml` și va configura automat serviciul
2. Așteaptă ca build-ul să se termine (5-10 minute)
3. Verifică logs pentru erori

---

## 5. Verificare și Monitorizare

### 5.1 Verificare Deploy
```bash
# Testează endpoint-ul de health check
curl https://your-app-name.onrender.com/health

# Ar trebui să returneze: {"status": "healthy"}
```

### 5.2 Setare Webhook
1. Botul va seta automat webhook-ul la pornire
2. Verifică în logs că webhook-ul a fost setat cu succes
3. Testează botul pe Telegram

### 5.3 Monitorizare Logs
1. În dashboard Render, mergi la "Logs"
2. Monitorizează pentru:
   - Erori de conexiune
   - Probleme de descărcare
   - Rate limiting
   - Erori de memorie

---

## 6. Troubleshooting

### 6.1 Probleme Comune

#### Bot nu răspunde
```bash
# Verifică că token-ul este corect
curl https://api.telegram.org/bot<TOKEN>/getMe

# Verifică webhook-ul
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

#### Erori de descărcare
- Verifică că URL-ul este de pe o platformă suportată
- Verifică logs pentru erori specifice
- Testează local cu același URL

#### Probleme de memorie pe Render
- Reduce `MAX_FILE_SIZE_MB` în variabilele de mediu
- Optimizează procesul de descărcare
- Consideră upgrade la plan plătit

### 6.2 Comenzi Utile pentru Debug

```bash
# Verifică webhook-ul curent
python -c "import requests; print(requests.get('https://api.telegram.org/bot<TOKEN>/getWebhookInfo').json())"

# Șterge webhook-ul (pentru testare locală)
python -c "import requests; print(requests.get('https://api.telegram.org/bot<TOKEN>/deleteWebhook').json())"

# Testează conexiunea la Render
curl -I https://your-app-name.onrender.com
```

### 6.3 Logs și Debugging

```bash
# Pentru debugging local, setează în .env:
DEBUG_MODE=true
LOG_LEVEL=DEBUG
ENABLE_DETAILED_LOGS=true

# Apoi rulează:
python app.py
```

---

## 🔐 Securitate și Best Practices

### ✅ Verificări de Securitate
- [ ] Token-ul nu este hardcodat în cod
- [ ] `.env` este în `.gitignore`
- [ ] Webhook folosește HTTPS
- [ ] Rate limiting este activat
- [ ] Logs nu conțin informații sensibile

### 🚀 Optimizări pentru Producție
- [ ] Monitorizare activă a logs
- [ ] Backup regulat al configurărilor
- [ ] Testare periodică a funcționalității
- [ ] Update regulat al dependențelor
- [ ] Rotarea periodică a token-ului

---

## 📞 Suport

Dacă întâmpini probleme:
1. Verifică logs pe Render
2. Rulează `python test_local.py` pentru diagnostic
3. Verifică că toate variabilele de mediu sunt setate corect
4. Testează local înainte de a investiga probleme de deploy

**Succes cu deploy-ul! 🎉**