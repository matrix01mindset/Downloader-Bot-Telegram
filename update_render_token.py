#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pentru actualizarea tokenului pe Render.com
Autor: Assistant
Data: 2025-08-11
"""

import os
import sys
import requests
import json
from datetime import datetime
import subprocess
import time

class RenderUpdater:
    def __init__(self):
        self.new_token = None
        self.render_service_id = "telegram-video-downloader-1471"
        self.env_file = '.env'
        
    def load_new_token(self):
        """Încarcă noul token din .env"""
        try:
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r') as f:
                    for line in f:
                        if line.startswith('BOT_TOKEN='):
                            self.new_token = line.split('=', 1)[1].strip()
                            print(f"✅ Token nou găsit: {self.new_token[:15]}...")
                            return True
            print("❌ Nu s-a găsit tokenul în .env")
            return False
        except Exception as e:
            print(f"❌ Eroare la citirea .env: {e}")
            return False
    
    def test_token_telegram(self, token):
        """Testează dacă tokenul funcționează cu Telegram API"""
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    print(f"✅ Token valid pentru @{bot_info.get('username', 'unknown')}")
                    return True
            
            print(f"❌ Token invalid")
            return False
            
        except Exception as e:
            print(f"❌ Eroare la testarea tokenului: {e}")
            return False
    
    def create_deployment_script(self):
        """Creează script pentru deployment pe Render"""
        deploy_script = f"""
#!/usr/bin/env python3
# Script automat pentru deployment cu noul token
# Generat la: {datetime.now().isoformat()}

import subprocess
import sys
import os

def deploy_with_new_token():
    print("🚀 Deployment automat cu noul token...")
    
    try:
        # Verifică dacă avem modificări
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            print("📝 Commit modificări locale...")
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', 
                          'SECURITY: Update bot token after compromise - {datetime.now().strftime("%Y-%m-%d %H:%M")}'], 
                          check=True)
        
        # Push la repository
        print("📤 Push la GitHub...")
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print("✅ Deployment complet!")
        print("\n🔄 Render va redeployă automat în ~2-3 minute")
        print("\n📊 Verifică status la:")
        print("https://dashboard.render.com/web/srv-{self.render_service_id}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Eroare deployment: {{e}}")
        return False
    except Exception as e:
        print(f"❌ Eroare neașteptată: {{e}}")
        return False

if __name__ == "__main__":
    deploy_with_new_token()
"""
        
        try:
            with open('deploy_secure.py', 'w', encoding='utf-8') as f:
                f.write(deploy_script)
            print("✅ Script de deployment creat: deploy_secure.py")
            return True
        except Exception as e:
            print(f"❌ Eroare la crearea scriptului: {e}")
            return False
    
    def create_render_instructions(self):
        """Creează instrucțiuni detaliate pentru Render"""
        instructions = f"""
🌐 INSTRUCȚIUNI ACTUALIZARE RENDER.COM
=====================================

🔑 NOUL TOKEN: {self.new_token}

📋 PAȘI MANUALI:

1. 🌍 Accesează Render Dashboard:
   https://dashboard.render.com

2. 🔍 Găsește serviciul:
   Nume: telegram-video-downloader-1471
   Tip: Web Service

3. ⚙️ Accesează Environment:
   - Click pe serviciu
   - Tab "Environment"
   - Găsește variabila "BOT_TOKEN"

4. ✏️ Editează tokenul:
   - Click "Edit" lângă BOT_TOKEN
   - Șterge tokenul vechi
   - Introdu: {self.new_token}
   - Click "Save Changes"

5. 🔄 Redeployment automat:
   - Render va detecta schimbarea
   - Va redeployă automat în ~2-3 minute
   - Verifică logs-urile pentru confirmare

📊 VERIFICARE DEPLOYMENT:

✅ Semne că deployment-ul a reușit:
- Status: "Live" (verde)
- Logs: "Application started successfully"
- Bot răspunde la comenzi

❌ Semne de probleme:
- Status: "Deploy failed" (roșu)
- Logs: erori de autentificare
- Bot nu răspunde

🆘 DACĂ CEVA NU MERGE:

1. Verifică că tokenul este corect copiat
2. Așteaptă 5 minute pentru propagare
3. Restart manual serviciul
4. Verifică logs-urile pentru erori

🔒 SECURITATE SUPLIMENTARĂ:

- Activează notificări Render pentru deployment-uri
- Monitorizează logs-urile zilnic
- Setează alerte pentru erori
- Backup periodic al configurației

📞 SUPORT:
- Render Support: https://render.com/support
- Telegram Bot API: https://core.telegram.org/bots/api

⏰ Generat la: {datetime.now().isoformat()}
"""
        
        try:
            with open('RENDER_UPDATE_INSTRUCTIONS.txt', 'w', encoding='utf-8') as f:
                f.write(instructions)
            print("✅ Instrucțiuni Render create: RENDER_UPDATE_INSTRUCTIONS.txt")
            return True
        except Exception as e:
            print(f"❌ Eroare la crearea instrucțiunilor: {e}")
            return False
    
    def create_monitoring_script(self):
        """Creează script pentru monitorizarea botului"""
        monitor_script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script de monitorizare bot după actualizarea tokenului

import requests
import time
import json
from datetime import datetime

BOT_TOKEN = "{self.new_token}"
CHECK_INTERVAL = 30  # secunde

def check_bot_status():
    """Verifică statusul botului"""
    try:
        url = f"https://api.telegram.org/bot{{BOT_TOKEN}}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {{}})
                print(f"✅ {{datetime.now().strftime('%H:%M:%S')}} - Bot activ: @{{bot_info.get('username', 'unknown')}}")
                return True
        
        print(f"❌ {{datetime.now().strftime('%H:%M:%S')}} - Bot inactiv")
        return False
        
    except Exception as e:
        print(f"❌ {{datetime.now().strftime('%H:%M:%S')}} - Eroare: {{e}}")
        return False

def main():
    print("🔍 MONITORIZARE BOT TELEGRAM")
    print("============================\\n")
    print(f"Token: {{BOT_TOKEN[:15]}}...")
    print(f"Interval verificare: {{CHECK_INTERVAL}} secunde")
    print("Apasă Ctrl+C pentru a opri\\n")
    
    try:
        while True:
            if check_bot_status():
                print("🟢 Bot funcționează\\n")
            else:
                print("🔴 Bot inactiv\\n")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\\n👋 Monitorizare oprită")
    except Exception as e:
        print(f"\\n💥 Eroare: {{e}}")

if __name__ == "__main__":
    main()
'''
        
        try:
            with open('monitor_bot.py', 'w', encoding='utf-8') as f:
                f.write(monitor_script)
            print("✅ Script de monitorizare creat: monitor_bot.py")
            return True
        except Exception as e:
            print(f"❌ Eroare la crearea scriptului de monitorizare: {e}")
            return False

def main():
    print("🌐 ACTUALIZARE RENDER.COM - TOKEN SECURIZAT")
    print("============================================\n")
    
    updater = RenderUpdater()
    
    # Pas 1: Încarcă noul token
    print("📋 Pas 1: Verificare token nou...")
    if not updater.load_new_token():
        print("❌ Nu s-a putut încărca tokenul nou din .env")
        return
    
    # Pas 2: Testează tokenul
    print("\n📋 Pas 2: Testare token...")
    if not updater.test_token_telegram(updater.new_token):
        print("❌ Tokenul nu funcționează - verifică din nou")
        return
    
    # Pas 3: Creează instrucțiuni Render
    print("\n📋 Pas 3: Generare instrucțiuni Render...")
    updater.create_render_instructions()
    
    # Pas 4: Creează script de deployment
    print("\n📋 Pas 4: Creare script deployment...")
    updater.create_deployment_script()
    
    # Pas 5: Creează script de monitorizare
    print("\n📋 Pas 5: Creare script monitorizare...")
    updater.create_monitoring_script()
    
    # Finalizare
    print("\n" + "="*60)
    print("✅ PREGĂTIT PENTRU ACTUALIZARE RENDER!")
    print("="*60)
    
    print("\n🎯 URMĂTORII PAȘI:")
    print("\n1. 📖 Citește instrucțiunile:")
    print("   type RENDER_UPDATE_INSTRUCTIONS.txt")
    
    print("\n2. 🌐 Actualizează manual pe Render:")
    print("   https://dashboard.render.com")
    print(f"   Serviciu: {updater.render_service_id}")
    print(f"   Noul token: {updater.new_token}")
    
    print("\n3. 🚀 SAU folosește deployment automat:")
    print("   python deploy_secure.py")
    
    print("\n4. 🔍 Monitorizează după actualizare:")
    print("   python monitor_bot.py")
    
    print("\n🔒 IMPORTANT:")
    print("- Așteaptă 2-3 minute pentru redeployment")
    print("- Verifică logs-urile Render pentru erori")
    print("- Testează botul cu un mesaj simplu")
    print("- Monitorizează activitatea suspectă")
    
    print("\n✨ Botul va fi complet securizat după acești pași!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Script întrerupt de utilizator")
    except Exception as e:
        print(f"\n\n💥 Eroare critică: {e}")
        print("🆘 Contactează suportul pentru ajutor!")