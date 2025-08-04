# 🎬 Bot Telegram pentru Descărcare Video

Un bot Telegram modern și interactiv pentru descărcarea videoclipurilor de pe diverse platforme, cu meniu intuitiv și experiență utilizator îmbunătățită.

## 🚀 Funcționalități

- **🎯 Meniu interactiv** cu butoane inline
- **📥 Descărcare automată** de videoclipuri
- **🔗 Platforme multiple** suportate
- **✅ Confirmare descărcare** cu preview link
- **🔄 Opțiuni post-descărcare** (descărcare nouă, meniu)
- **❓ Secțiune FAQ** integrată
- **⚙️ Informații detaliate** despre limitări

## 🎮 Comenzi Disponibile

- `/start` - Afișează meniul principal interactiv
- `/menu` - Accesează rapid meniul principal
- `/help` - Informații de ajutor cu butoane

## 🔗 Platforme Suportate

- **🎥 YouTube** (youtube.com, youtu.be)
  - Videoclipuri publice și unlisted
  - Playlist-uri (primul video)
- **📱 TikTok** (tiktok.com)
  - Videoclipuri publice, fără watermark
- **📸 Instagram** (instagram.com/p/)
  - Postări video publice, Reels și IGTV
- **📘 Facebook** (facebook.com, fb.watch)
  - Videoclipuri publice
- **🐦 Twitter/X** (twitter.com, x.com)
  - Tweet-uri cu video publice

## 📱 Cum să Folosești

### 🎯 Metoda Interactivă (Recomandată)
1. **Pornește botul** - Trimite `/start`
2. **Explorează meniul** cu butoanele interactive
3. **Trimite link-ul** videoclipului
4. **Confirmă descărcarea** cu butonul "✅ Da, descarcă!"
5. **Primești videoclipul** și alegi următoarea acțiune

### ⚡ Metoda Rapidă
1. Trimite direct link-ul în chat
2. Confirmă cu butonul de descărcare
3. Primești videoclipul instant

## 🎨 Interfața Interactivă

### 🏠 Meniu Principal
- **📖 Cum să folosesc botul** - Ghid pas cu pas
- **🔗 Platforme suportate** - Detalii despre fiecare platformă
- **⚙️ Setări și limitări** - Informații tehnice
- **❓ Întrebări frecvente** - Răspunsuri la probleme comune

### 📥 Procesul de Descărcare
1. **Preview link** cu confirmare
2. **Progres în timp real** cu mesaje de status
3. **Opțiuni post-descărcare**:
   - 📥 Descarcă alt videoclip
   - 🏠 Înapoi la meniu principal

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