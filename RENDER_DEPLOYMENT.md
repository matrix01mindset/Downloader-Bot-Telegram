# 🚀 DEPLOYMENT PE RENDER.COM - GHID PAS CU PAS

## 📋 Pregătiri necesare

### 1. Creează cont pe GitHub (dacă nu ai)
- Mergi pe [github.com](https://github.com)
- Creează cont gratuit
- Verifică email-ul

### 2. Creează cont pe Render.com
- Mergi pe [render.com](https://render.com)
- Apasă "Get Started for Free"
- Conectează-te cu GitHub

### 3. Creează bot Telegram
- Deschide [@BotFather](https://t.me/botfather) în Telegram
- Trimite `/newbot`
- Alege nume pentru bot (ex: "Video Downloader Bot")
- Alege username (ex: "my_video_downloader_bot")
- **SALVEAZĂ TOKEN-UL** primit (ex: `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ`)

## 🔧 PASUL 1: Încarcă codul pe GitHub

### Opțiunea A: Prin interfața web GitHub
1. **Creează repository nou:**
   - Mergi pe [github.com](https://github.com)
   - Apasă "+" → "New repository"
   - Nume: `telegram-video-downloader`
   - Bifează "Public"
   - Apasă "Create repository"

2. **Încarcă fișierele:**
   - Apasă "uploading an existing file"
   - Selectează TOATE fișierele din folderul curent:
     - `app.py`
     - `bot.py` 
     - `downloader.py`
     - `requirements.txt`
     - `Procfile`
     - `.gitignore`
     - `README.md`
   - Scrie commit message: "Initial commit"
   - Apasă "Commit changes"

### Opțiunea B: Prin Git (dacă știi să folosești)
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/telegram-video-downloader.git
git push -u origin main
```

## 🌐 PASUL 2: Deploy pe Render

### 1. Creează Web Service
- Mergi pe [dashboard.render.com](https://dashboard.render.com)
- Apasă "New +" → "Web Service"
- Conectează repository-ul GitHub creat
- Selectează `telegram-video-downloader`

### 2. Configurează deployment
**Settings obligatorii:**
- **Name:** `telegram-video-downloader` (sau alt nume)
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python app.py`
- **Plan:** `Free` (0$/lună)

### 3. Setează Environment Variables
În secțiunea "Environment Variables", adaugă:

```
TELEGRAM_BOT_TOKEN = 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
WEBHOOK_URL = https://your-app-name.onrender.com
PORT = 10000
```

**⚠️ IMPORTANT:**
- Înlocuiește `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ` cu token-ul tău real
- Înlocuiește `your-app-name` cu numele aplicației tale Render

### 4. Deploy aplicația
- Apasă "Create Web Service"
- Așteaptă 5-10 minute pentru build
- Verifică că status-ul este "Live"

## ⚙️ PASUL 3: Configurează Webhook

### 1. Găsește URL-ul aplicației
- În dashboard Render, copiază URL-ul (ex: `https://telegram-video-downloader-abc123.onrender.com`)

### 2. Setează webhook-ul
- Deschide browser-ul
- Mergi la: `https://telegram-video-downloader-abc123.onrender.com/set_webhook`
- Ar trebui să vezi: `✅ Webhook setat cu succes!`

### 3. Testează botul
- Deschide Telegram
- Caută botul tău după username
- Trimite `/start`
- Trimite un link YouTube pentru test

## 🔍 VERIFICARE ȘI TROUBLESHOOTING

### Verifică că totul funcționează:
1. **Status aplicație:** Dashboard Render → "Live" verde
2. **Logs:** Dashboard Render → "Logs" → nu ar trebui să fie erori
3. **Webhook:** Accesează `/set_webhook` → mesaj de succes
4. **Bot răspunde:** Trimite `/start` în Telegram

### Probleme frecvente:

**🔴 Build failed:**
- Verifică că `requirements.txt` există
- Verifică că toate fișierele sunt încărcate

**🔴 Bot nu răspunde:**
- Verifică `TELEGRAM_BOT_TOKEN` în Environment Variables
- Verifică că webhook-ul este setat (`/set_webhook`)

**🔴 "Application failed to respond":**
- Verifică că `PORT = 10000` în Environment Variables
- Verifică că `app.py` rulează pe portul corect

**🔴 Descărcarea nu funcționează:**
- Testează cu link-uri YouTube publice
- Verifică logs-urile în Render pentru erori

## 📱 TESTARE FINALĂ

### Link-uri de test recomandate:
1. **YouTube:** `https://www.youtube.com/watch?v=jNQXAC9IVRw`
2. **TikTok:** Link public recent
3. **Instagram:** Link public recent

### Comenzi bot:
- `/start` - Pornește botul
- `/help` - Afișează ajutorul
- Trimite orice link suportat pentru descărcare

## 🎉 FELICITĂRI!

Botul tău este acum LIVE pe internet! 🚀

**URL aplicație:** `https://your-app-name.onrender.com`
**Bot Telegram:** `@your_bot_username`

### Limitări plan gratuit Render:
- ✅ 750 ore/lună (suficient pentru uz personal)
- ✅ Aplicația "doarme" după 15 min inactivitate
- ✅ Se "trezește" automat la primul request
- ✅ Bandwidth nelimitat

### Următorii pași:
1. **Partajează botul** cu prietenii
2. **Monitorizează** usage-ul în dashboard
3. **Upgrade la plan plătit** dacă ai nevoie de uptime 24/7

---

**📞 Suport:** Dacă întâmpini probleme, verifică logs-urile în Render și compară cu acest ghid.