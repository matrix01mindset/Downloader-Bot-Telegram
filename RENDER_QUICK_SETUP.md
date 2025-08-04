# ⚡ SETUP RAPID RENDER.COM

## 🔑 Token-ul tău Telegram Bot:
```
8253089686:AAGNOvUHXTVwz2Bi9KEpBpY4OAkTPC7ICAs
```

## 🚀 Pași rapizi pentru deployment:

### 1. Mergi pe Render.com
- **Deschide:** https://render.com
- **Creează cont** sau **Login** cu GitHub

### 2. Conectează repository-ul
- **Click:** "New" → "Web Service"
- **Conectează:** repository-ul GitHub `matrix01mindset/Downloader-Bot-Telegram`
- **Selectează:** branch-ul `main`

### 3. Configurează serviciul

#### **Build & Deploy Settings:**
- **Name:** `telegram-video-downloader` (sau alt nume)
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python app.py`
- **Plan:** `Free` (0$/lună)

#### **Environment Variables (IMPORTANT!):**
Adaugă aceste variabile în secțiunea "Environment":

| Key | Value |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | `8253089686:AAGNOvUHXTVwz2Bi9KEpBpY4OAkTPC7ICAs` |
| `PORT` | `10000` |
| `WEBHOOK_URL` | `https://NUMELE-SERVICIULUI.onrender.com/webhook` |

**⚠️ IMPORTANT:** Înlocuiește `NUMELE-SERVICIULUI` cu numele real al serviciului tău!

### 4. Deploy
- **Click:** "Create Web Service"
- **Așteaptă:** 5-10 minute pentru build și deploy
- **Verifică:** că serviciul este "Live" (verde)

### 5. Setează webhook-ul

După ce serviciul este live, deschide în browser:
```
https://NUMELE-SERVICIULUI.onrender.com/set_webhook
```

**Exemplu:** Dacă serviciul se numește `telegram-video-downloader`, URL-ul va fi:
```
https://telegram-video-downloader.onrender.com/set_webhook
```

### 6. Testează bot-ul

1. **Deschide Telegram**
2. **Caută bot-ul** după username (îl găsești în BotFather)
3. **Trimite:** `/start`
4. **Testează:** cu un link YouTube, TikTok, etc.

## 🎯 Verificare finală

### ✅ Checklist:
- [ ] Serviciul este "Live" pe Render
- [ ] Webhook-ul este setat (vizitează `/set_webhook`)
- [ ] Bot-ul răspunde la `/start`
- [ ] Bot-ul descarcă video-uri cu succes

### 🔧 Dacă ceva nu merge:

1. **Verifică logs-urile** pe Render (tab "Logs")
2. **Verifică variabilele** de mediu
3. **Redeployează** serviciul
4. **Setează din nou** webhook-ul

## 📱 Bot-ul tău este gata!

**Token:** `8253089686:AAGNOvUHXTVwz2Bi9KEpBpY4OAkTPC7ICAs`
**Platforme suportate:** YouTube, TikTok, Instagram, Facebook, Twitter/X
**Limite:** 100MB, 15 minute
**Status:** 24/7 online pe Render.com

---
**🎉 Felicitări! Bot-ul tău Telegram Video Downloader este acum live!**