#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pentru crearea automată a serviciului pe Render.com
Autor: Assistant
Data: 2025-08-12
"""

import os
import sys
import requests
import json
from datetime import datetime
import webbrowser
import time

class RenderServiceCreator:
    def __init__(self):
        self.bot_token = None
        self.github_repo = "https://github.com/matrix01mindset/Downloader-Bot-Telegram"
        self.service_name = "telegram-video-downloader-bot"
        self.env_file = '.env'
        
    def load_bot_token(self):
        """Încarcă tokenul bot din .env"""
        try:
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r') as f:
                    for line in f:
                        if line.startswith('BOT_TOKEN='):
                            self.bot_token = line.split('=', 1)[1].strip()
                            print(f"✅ Token găsit: {self.bot_token[:15]}...")
                            return True
            print("❌ Nu s-a găsit tokenul în .env")
            return False
        except Exception as e:
            print(f"❌ Eroare la citirea .env: {e}")
            return False
    
    def test_bot_token(self):
        """Testează dacă tokenul funcționează"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    print(f"✅ Bot valid: @{bot_info.get('username', 'unknown')}")
                    return True
            
            print(f"❌ Token invalid")
            return False
            
        except Exception as e:
            print(f"❌ Eroare la testarea tokenului: {e}")
            return False
    
    def create_render_instructions(self):
        """Creează instrucțiuni pas cu pas pentru Render"""
        instructions = f"""
🚀 CREARE SERVICIU RENDER.COM - PAS CU PAS
==========================================

🔑 TOKEN BOT: {self.bot_token}
📂 REPOSITORY: {self.github_repo}
🏷️  NUME SERVICIU: {self.service_name}

📋 PAȘI DETALIAȚI:

1️⃣ ACCESEAZĂ RENDER DASHBOARD
   🌐 Deschide: https://dashboard.render.com
   🔐 Login cu GitHub (dacă nu ești logat)

2️⃣ CREEAZĂ SERVICIU NOU
   ➕ Click "New" (buton albastru sus-dreapta)
   🌐 Selectează "Web Service"

3️⃣ CONECTEAZĂ REPOSITORY
   📂 Caută: "Downloader-Bot-Telegram"
   🔗 Click "Connect" lângă repository
   
   DACĂ NU VEZI REPOSITORY-UL:
   - Click "Configure GitHub App"
   - Selectează "matrix01mindset"
   - Bifează "Downloader-Bot-Telegram"
   - Click "Save"

4️⃣ CONFIGUREAZĂ SERVICIUL
   📝 Nume: {self.service_name}
   🌍 Region: Frankfurt (EU Central)
   🌿 Branch: main
   📁 Root Directory: (lasă gol)
   🏗️  Build Command: pip install -r requirements.txt
   ▶️  Start Command: python app.py

5️⃣ SELECTEAZĂ PLANUL
   💰 Plan: Free (0$/lună)
   ⚡ Instance Type: Free

6️⃣ CONFIGUREAZĂ ENVIRONMENT VARIABLES
   ⚙️  Click "Advanced" → "Add Environment Variable"
   
   Variabila 1:
   🔑 Key: BOT_TOKEN
   🔒 Value: {self.bot_token}
   
   Variabila 2:
   🔑 Key: PORT
   🔒 Value: 10000
   
   Variabila 3:
   🔑 Key: PYTHON_VERSION
   🔒 Value: 3.11.0

7️⃣ DEPLOY SERVICIUL
   🚀 Click "Create Web Service"
   ⏳ Așteaptă 3-5 minute pentru build
   ✅ Verifică că statusul devine "Live"

8️⃣ CONFIGUREAZĂ WEBHOOK TELEGRAM
   📋 Copiază URL-ul serviciului (ex: https://{self.service_name}.onrender.com)
   🔗 Setează webhook: https://{self.service_name}.onrender.com/webhook

📊 VERIFICARE FINALĂ:

✅ Checklist:
   □ Serviciul este "Live" (verde)
   □ Logs arată "Application started successfully"
   □ Botul răspunde la comenzi în Telegram
   □ Nu sunt erori în logs

❌ Probleme comune:
   - Build failed: verifică requirements.txt
   - Start failed: verifică app.py și PORT
   - Bot nu răspunde: verifică BOT_TOKEN
   - Timeout: verifică că app.py rulează pe PORT 10000

🆘 SUPORT:
   📧 Render Support: https://render.com/support
   📚 Documentație: https://render.com/docs
   🤖 Telegram Bot API: https://core.telegram.org/bots/api

⏰ Generat la: {datetime.now().isoformat()}
"""
        
        try:
            with open('RENDER_SERVICE_SETUP.txt', 'w', encoding='utf-8') as f:
                f.write(instructions)
            print("✅ Instrucțiuni create: RENDER_SERVICE_SETUP.txt")
            return True
        except Exception as e:
            print(f"❌ Eroare la crearea instrucțiunilor: {e}")
            return False
    
    def create_webhook_setup_script(self):
        """Creează script pentru configurarea webhook-ului"""
        webhook_script = f"""
#!/usr/bin/env python3
# Script pentru configurarea webhook-ului Telegram

import requests
import sys

BOT_TOKEN = "{self.bot_token}"
WEBHOOK_URL = "https://{self.service_name}.onrender.com/webhook"

def set_webhook():
    \"\"\"Setează webhook-ul Telegram\"\"\"
    try:
        url = f"https://api.telegram.org/bot{{BOT_TOKEN}}/setWebhook"
        data = {{
            'url': WEBHOOK_URL,
            'max_connections': 40,
            'allowed_updates': ['message', 'callback_query']
        }}
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Webhook setat cu succes: {{WEBHOOK_URL}}")
                return True
            else:
                print(f"❌ Eroare API: {{result.get('description', 'Unknown error')}}")
        else:
            print(f"❌ HTTP Error: {{response.status_code}}")
        
        return False
        
    except Exception as e:
        print(f"❌ Eroare: {{e}}")
        return False

def get_webhook_info():
    \"\"\"Verifică informațiile webhook-ului\"\"\"
    try:
        url = f"https://api.telegram.org/bot{{BOT_TOKEN}}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                info = result.get('result', {{}})
                print(f"\n📊 INFORMAȚII WEBHOOK:")
                print(f"URL: {{info.get('url', 'Nu este setat')}}")
                print(f"Pending updates: {{info.get('pending_update_count', 0)}}")
                print(f"Ultima eroare: {{info.get('last_error_message', 'Nicio eroare')}}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Eroare: {{e}}")
        return False

def main():
    print("🔗 CONFIGURARE WEBHOOK TELEGRAM")
    print("================================\n")
    
    print(f"Bot Token: {{BOT_TOKEN[:15]}}...")
    print(f"Webhook URL: {{WEBHOOK_URL}}\n")
    
    # Verifică webhook-ul curent
    print("📋 Verificare webhook curent...")
    get_webhook_info()
    
    # Setează noul webhook
    print("\n📋 Setare webhook nou...")
    if set_webhook():
        print("\n📋 Verificare finală...")
        get_webhook_info()
        print("\n✅ Webhook configurat cu succes!")
        print("🤖 Botul este gata să primească mesaje!")
    else:
        print("\n❌ Webhook nu a putut fi setat")
        print("🔍 Verifică că serviciul Render este activ")

if __name__ == "__main__":
    main()
"""
        
        try:
            with open('setup_webhook.py', 'w', encoding='utf-8') as f:
                f.write(webhook_script)
            print("✅ Script webhook creat: setup_webhook.py")
            return True
        except Exception as e:
            print(f"❌ Eroare la crearea scriptului webhook: {e}")
            return False
    
    def open_render_dashboard(self):
        """Deschide Render Dashboard în browser"""
        try:
            print("🌐 Deschid Render Dashboard...")
            webbrowser.open('https://dashboard.render.com')
            time.sleep(2)
            print("✅ Dashboard deschis în browser")
            return True
        except Exception as e:
            print(f"❌ Nu s-a putut deschide browser-ul: {e}")
            return False

def main():
    print("🚀 CREARE SERVICIU RENDER.COM")
    print("==============================\n")
    
    creator = RenderServiceCreator()
    
    # Pas 1: Încarcă tokenul
    print("📋 Pas 1: Verificare token bot...")
    if not creator.load_bot_token():
        print("❌ Nu s-a putut încărca tokenul")
        return
    
    # Pas 2: Testează tokenul
    print("\n📋 Pas 2: Testare token...")
    if not creator.test_bot_token():
        print("❌ Tokenul nu funcționează")
        return
    
    # Pas 3: Creează instrucțiuni
    print("\n📋 Pas 3: Generare instrucțiuni...")
    creator.create_render_instructions()
    
    # Pas 4: Creează script webhook
    print("\n📋 Pas 4: Creare script webhook...")
    creator.create_webhook_setup_script()
    
    # Pas 5: Deschide dashboard
    print("\n📋 Pas 5: Deschidere Render Dashboard...")
    creator.open_render_dashboard()
    
    # Finalizare
    print("\n" + "="*60)
    print("✅ PREGĂTIT PENTRU CREARE SERVICIU!")
    print("="*60)
    
    print("\n🎯 URMĂTORII PAȘI:")
    print("\n1. 📖 Citește instrucțiunile:")
    print("   type RENDER_SERVICE_SETUP.txt")
    
    print("\n2. 🌐 Urmează pașii în Render Dashboard")
    print("   (s-a deschis automat în browser)")
    
    print("\n3. 🔗 După ce serviciul este Live, rulează:")
    print("   python setup_webhook.py")
    
    print("\n4. 🧪 Testează botul în Telegram")
    
    print("\n📊 INFORMAȚII IMPORTANTE:")
    print(f"- Repository: {creator.github_repo}")
    print(f"- Nume serviciu: {creator.service_name}")
    print(f"- Token bot: {creator.bot_token[:15]}...")
    print(f"- Webhook URL: https://{creator.service_name}.onrender.com/webhook")
    
    print("\n🔒 Botul va fi complet funcțional după acești pași!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Script întrerupt de utilizator")
    except Exception as e:
        print(f"\n\n💥 Eroare critică: {e}")
        print("🆘 Contactează suportul pentru ajutor!")