# 🎬 Telegram Video Downloader Bot

Un bot Telegram complet pentru descărcarea videoclipurilor de pe YouTube, TikTok, Instagram, Facebook și Twitter/X.

## 🚀 Funcționalități

- ✅ Descărcare de pe YouTube, TikTok, Instagram, Facebook, Twitter/X
- ✅ Interfață simplă prin Telegram
- ✅ Hosting gratuit pe Render/Railway/Replit
- ✅ Procesare automată și trimitere directă în chat
- ✅ Limitări de siguranță (max 15 min, max 100MB)
- ✅ Mesaje de eroare prietenoase

## 📁 Structura Proiectului

```
downloader_bot/
├── app.py              # Server Flask pentru webhook
├── bot.py              # Logica botului Telegram (pentru rulare locală)
├── downloader.py       # Logică de descărcare cu yt-dlp
├── requirements.txt    # Dependențe Python
├── Procfile           # Pentru deployment
└── README.md          # Acest fișier
```

## 🛠️ Configurare

### 1. Creează Bot Telegram

1. Deschide [@BotFather](https://t.me/botfather) pe Telegram
2. Trimite `/newbot`
3. Alege un nume pentru bot (ex: "Video Downloader")
4. Alege un username (ex: "my_video_downloader_bot")
5. Salvează token-ul primit (ex: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Instalare Locală

```bash
# Clonează sau descarcă proiectul
cd downloader_bot

# Instalează dependențele
pip install -r requirements.txt

# Setează token-ul (Windows)
set TELEGRAM_BOT_TOKEN=your_bot_token_here

# Setează token-ul (Linux/Mac)
export TELEGRAM_BOT_TOKEN=your_bot_token_here

# Rulează botul local
python bot.py
```

## 🌐 Deployment Gratuit

### Opțiunea 1: Render.com (Recomandat)

1. **Creează cont pe [Render.com](https://render.com)**

2. **Conectează repository-ul:**
   - Creează un repository GitHub cu aceste fișiere
   - În Render, click "New" → "Web Service"
   - Conectează repository-ul GitHub

3. **Configurează serviciul:**
   - **Name:** `video-downloader-bot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`

4. **Adaugă variabile de mediu:**
   - `TELEGRAM_BOT_TOKEN` = token-ul tău de bot
   - `WEBHOOK_URL` = URL-ul serviciului Render (ex: `https://video-downloader-bot.onrender.com`)

5. **Deploy și setează webhook:**
   - După deployment, accesează: `https://your-app.onrender.com/set_webhook`
   - Verifică statusul: `https://your-app.onrender.com/health`

### Opțiunea 2: Railway.app

1. **Creează cont pe [Railway.app](https://railway.app)**
2. **Deploy din GitHub:**
   - Click "Deploy from GitHub repo"
   - Selectează repository-ul
3. **Adaugă variabile:**
   - `TELEGRAM_BOT_TOKEN` = token-ul tău
   - `WEBHOOK_URL` = URL-ul Railway
4. **Setează webhook:** accesează `/set_webhook`

### Opțiunea 3: Replit

1. **Creează cont pe [Replit.com](https://replit.com)**
2. **Importă din GitHub sau încarcă fișierele**
3. **Adaugă în Secrets:**
   - `TELEGRAM_BOT_TOKEN` = token-ul tău
4. **Rulează `python bot.py`** (pentru polling, nu webhook)

## 🔧 Configurare Avansată

### Variabile de Mediu

- `TELEGRAM_BOT_TOKEN` - Token-ul botului (obligatoriu)
- `WEBHOOK_URL` - URL-ul pentru webhook (pentru hosting)
- `PORT` - Portul serverului (default: 5000)

### Limitări Configurabile

În `downloader.py` poți modifica:

```python
# Durata maximă (secunde)
if duration and duration > 900:  # 15 minute

# Calitatea video
'format': 'best[height<=720]/best',  # 720p max

# Mărimea fișierului
if file_size > 100 * 1024 * 1024:  # 100MB
```

## 📱 Utilizare

1. **Pornește botul:** trimite `/start`
2. **Trimite un link** de video de pe:
   - YouTube: `https://youtube.com/watch?v=...`
   - TikTok: `https://tiktok.com/@user/video/...`
   - Instagram: `https://instagram.com/p/...`
   - Facebook: `https://facebook.com/watch?v=...`
   - Twitter/X: `https://twitter.com/user/status/...`
3. **Așteaptă** procesarea și descărcarea
4. **Primești** videoclipul în chat

## 🐛 Depanare

### Probleme Comune

**Bot nu răspunde:**
- Verifică că token-ul este corect
- Verifică că webhook-ul este setat: `/set_webhook`
- Verifică logs-urile în platforma de hosting

**Erori de descărcare:**
- Videoclipul poate fi privat
- Platforma poate bloca bot-urile
- Videoclipul poate fi prea lung/mare

**Webhook nu funcționează:**
- Verifică că `WEBHOOK_URL` este setat corect
- URL-ul trebuie să fie HTTPS
- Accesează `/health` pentru verificare

### Logs și Monitoring

```python
# Pentru debugging, adaugă în app.py:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔒 Securitate

- Token-ul botului nu este hardcodat
- Fișierele temporare sunt șterse automat
- Limitări de mărime și durată pentru siguranță
- Validare URL-uri pentru platforme suportate

## 📄 Licență

Acest proiect este open source și poate fi folosit liber.

## 🤝 Contribuții

Contribuțiile sunt binevenite! Poți:
- Raporta bug-uri
- Sugera funcționalități noi
- Îmbunătăți codul
- Adăuga suport pentru alte platforme

## 📞 Suport

Dacă întâmpini probleme:
1. Verifică acest README
2. Verifică logs-urile aplicației
3. Testează local cu `python bot.py`
4. Verifică că toate dependențele sunt instalate

---

**Enjoy downloading! 🎉**