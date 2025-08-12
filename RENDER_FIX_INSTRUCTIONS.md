
🚀 PAȘI PENTRU REDEPLOY PE RENDER:

1. **Commit modificările:**
   git add .
   git commit -m "Fix Render deployment issues"
   git push origin main

2. **Pe Render Dashboard:**
   - Mergi la serviciul tău
   - Click pe "Manual Deploy" → "Deploy latest commit"
   - SAU schimbă temporar Procfile la: web: python app_simple.py

3. **Setează Environment Variables în Render:**
   - TELEGRAM_BOT_TOKEN: [token-ul tău real]
   - WEBHOOK_URL: https://telegram-video-downloader-1471.onrender.com
   - PORT: 10000

4. **După deploy, testează:**
   - https://telegram-video-downloader-1471.onrender.com/
   - https://telegram-video-downloader-1471.onrender.com/health
   - https://telegram-video-downloader-1471.onrender.com/debug

5. **Setează webhook-ul:**
   - https://telegram-video-downloader-1471.onrender.com/set_webhook

⚠️ IMPORTANT: Dacă app.py nu funcționează, folosește app_simple.py temporar!
