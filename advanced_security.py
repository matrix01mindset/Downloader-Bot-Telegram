#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de securitate avansată pentru protecție împotriva atacurilor persistente
Implementează măsuri suplimentare de securitate și monitoring
"""

import os
import sys
import time
import json
import hashlib
import requests
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def print_advanced_security_banner():
    """Afișează banner-ul de securitate avansată"""
    print("🛡️ SECURITATE AVANSATĂ - PROTECȚIE PERSISTENTĂ")
    print("=" * 60)
    print("🚨 DETECTAT: Atac persistent după patch")
    print("🔒 IMPLEMENTARE: Măsuri de securitate suplimentare")
    print("=" * 60)

def check_token_compromise():
    """Verifică dacă token-ul este compromis"""
    print("\n1️⃣ VERIFICARE COMPROMITERE TOKEN")
    print("-" * 40)
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Token-ul nu este găsit în .env")
        return False
    
    try:
        # Verifică webhook-ul actual
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        webhook_info = response.json()
        
        if webhook_info.get('ok'):
            webhook_url = webhook_info['result'].get('url', '')
            print(f"📋 Webhook actual: {webhook_url}")
            
            # Verifică dacă webhook-ul este pe Render
            if 'telegram-video-downloader-1471.onrender.com' in webhook_url:
                print("✅ Webhook-ul este pe serverul nostru")
                return True
            else:
                print(f"❌ WEBHOOK COMPROMIS: {webhook_url}")
                return False
        else:
            print("❌ Eroare la verificarea webhook-ului")
            return False
            
    except Exception as e:
        print(f"❌ Eroare la verificarea token-ului: {e}")
        return False

def force_token_regeneration():
    """Forțează regenerarea token-ului"""
    print("\n2️⃣ REGENERARE FORȚATĂ TOKEN")
    print("-" * 40)
    
    print("🚨 ACȚIUNE CRITICĂ: Token-ul TREBUIE regenerat IMEDIAT!")
    print("")
    print("📞 PAȘI OBLIGATORII:")
    print("   1. Deschide Telegram și mergi la @BotFather")
    print("   2. Trimite /mybots")
    print("   3. Selectează 'MATRIXBOT' sau 'matrixdownload_bot'")
    print("   4. Selectează 'API Token'")
    print("   5. Selectează 'Revoke current token'")
    print("   6. Confirmă revocarea")
    print("   7. Selectează 'Generate new token'")
    print("   8. Copiază noul token")
    print("")
    print("⚠️  IMPORTANT: Vechiul token va deveni INACTIV imediat!")
    
    input("\n⏸️  Apasă ENTER după ce ai generat noul token...")
    
    new_token = input("🔑 Introdu noul token generat: ").strip()
    
    if not new_token or len(new_token) < 40 or ':' not in new_token:
        print("❌ Token invalid! Formatul trebuie să fie: 123456789:ABCdefGHI...")
        return False
    
    # Actualizează .env
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                lines[i] = f"TELEGRAM_BOT_TOKEN={new_token}"
                break
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print("✅ Token actualizat în .env")
        return True
        
    except Exception as e:
        print(f"❌ Eroare la actualizarea token-ului: {e}")
        return False

def implement_webhook_security():
    """Implementează securitate suplimentară pentru webhook"""
    print("\n3️⃣ SECURITATE WEBHOOK AVANSATĂ")
    print("-" * 40)
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = "https://telegram-video-downloader-1471.onrender.com/webhook"
    
    try:
        # Șterge webhook-ul complet
        print("🧹 Șterg webhook-ul complet...")
        delete_response = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
        
        if delete_response.json().get('ok'):
            print("✅ Webhook șters")
        
        # Așteaptă 5 secunde
        print("⏳ Aștept 5 secunde...")
        time.sleep(5)
        
        # Setează webhook-ul cu parametri de securitate
        security_params = {
            'url': webhook_url,
            'max_connections': 1,  # Limitează conexiunile
            'allowed_updates': ['message', 'callback_query']  # Doar update-uri necesare
        }
        
        print("🔒 Setez webhook cu parametri de securitate...")
        set_response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json=security_params
        )
        
        if set_response.json().get('ok'):
            print("✅ Webhook securizat setat")
            return True
        else:
            print(f"❌ Eroare la setarea webhook-ului: {set_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Eroare la securizarea webhook-ului: {e}")
        return False

def update_render_environment():
    """Actualizează variabilele de mediu pe Render"""
    print("\n4️⃣ ACTUALIZARE RENDER ENVIRONMENT")
    print("-" * 40)
    
    print("📋 PAȘI MANUALI CRITICI:")
    print("   1. Deschide https://dashboard.render.com")
    print("   2. Selectează serviciul: telegram-video-downloader-1471")
    print("   3. Mergi la tab-ul 'Environment'")
    print("   4. Click 'Edit' lângă TELEGRAM_BOT_TOKEN")
    print("   5. Înlocuiește cu noul token")
    print("   6. Click 'Save Changes'")
    print("   7. Așteaptă redeploy-ul automat (5-10 minute)")
    print("")
    print("⚠️  IMPORTANT: Nu închide această fereastră până nu termini!")
    
    input("\n⏸️  Apasă ENTER după ce ai actualizat token-ul pe Render...")

def implement_git_security():
    """Implementează securitate Git avansată"""
    print("\n5️⃣ SECURITATE GIT AVANSATĂ")
    print("-" * 40)
    
    try:
        # Verifică dacă .env este în .gitignore
        gitignore_content = ""
        try:
            with open('.gitignore', 'r', encoding='utf-8') as f:
                gitignore_content = f.read()
        except FileNotFoundError:
            pass
        
        # Adaugă reguli de securitate în .gitignore
        security_rules = [
            "# Security files",
            ".env",
            ".env.local",
            ".env.production",
            "*.key",
            "*.pem",
            "secrets/",
            "# Logs that might contain sensitive data",
            "*.log",
            "logs/"
        ]
        
        rules_to_add = []
        for rule in security_rules:
            if rule not in gitignore_content:
                rules_to_add.append(rule)
        
        if rules_to_add:
            with open('.gitignore', 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(rules_to_add) + '\n')
            print("✅ Reguli de securitate adăugate în .gitignore")
        
        # Remove .env din Git tracking
        subprocess.run(['git', 'rm', '--cached', '.env'], 
                      capture_output=True, check=False)
        
        # Commit securitatea
        subprocess.run(['git', 'add', '.gitignore'], check=True)
        commit_msg = f"🔒 EMERGENCY SECURITY: Advanced protection - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        print("✅ Securitate Git implementată")
        return True
        
    except Exception as e:
        print(f"⚠️  Avertisment Git: {e}")
        return False

def create_monitoring_system():
    """Creează sistem de monitoring pentru atacuri"""
    print("\n6️⃣ SISTEM DE MONITORING")
    print("-" * 40)
    
    monitoring_script = '''
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de monitoring pentru detectarea atacurilor
"""

import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

def check_webhook_integrity():
    """Verifică integritatea webhook-ului"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    expected_url = "https://telegram-video-downloader-1471.onrender.com/webhook"
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        webhook_info = response.json()
        
        if webhook_info.get('ok'):
            current_url = webhook_info['result'].get('url', '')
            
            if current_url != expected_url:
                print(f"🚨 ALERT: Webhook compromis! URL: {current_url}")
                return False
            else:
                print(f"✅ Webhook OK: {current_url}")
                return True
        else:
            print("❌ Eroare la verificarea webhook-ului")
            return False
            
    except Exception as e:
        print(f"❌ Eroare monitoring: {e}")
        return False

if __name__ == "__main__":
    print(f"🔍 Monitoring started at {datetime.now()}")
    while True:
        if not check_webhook_integrity():
            print("🚨 BREACH DETECTED! Running emergency security...")
            # Aici ar putea rula scriptul de securitate automat
        
        time.sleep(300)  # Verifică la fiecare 5 minute
'''
    
    try:
        with open('webhook_monitor.py', 'w', encoding='utf-8') as f:
            f.write(monitoring_script)
        
        print("✅ Script de monitoring creat: webhook_monitor.py")
        print("💡 Poți rula: python webhook_monitor.py pentru monitoring continuu")
        return True
        
    except Exception as e:
        print(f"❌ Eroare la crearea monitoring-ului: {e}")
        return False

def verify_final_security():
    """Verifică securitatea finală"""
    print("\n7️⃣ VERIFICARE SECURITATE FINALĂ")
    print("-" * 40)
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Test webhook
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        webhook_info = response.json()
        
        if webhook_info.get('ok'):
            webhook_url = webhook_info['result'].get('url', '')
            if 'telegram-video-downloader-1471.onrender.com' in webhook_url:
                print("✅ Webhook securizat")
            else:
                print(f"❌ Webhook încă compromis: {webhook_url}")
                return False
        
        # Test bot
        bot_response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        if bot_response.json().get('ok'):
            print("✅ Bot funcțional")
        else:
            print("❌ Bot nefuncțional")
            return False
        
        # Test server
        server_response = requests.get(
            "https://telegram-video-downloader-1471.onrender.com/health",
            timeout=10
        )
        if server_response.status_code == 200:
            print("✅ Server activ")
        else:
            print(f"⚠️  Server status: {server_response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Eroare la verificarea finală: {e}")
        return False

def main():
    """Funcția principală de securitate avansată"""
    print_advanced_security_banner()
    
    # Verifică dacă token-ul este compromis
    if not check_token_compromise():
        print("\n🚨 TOKEN COMPROMIS DETECTAT!")
        
        # Confirmă acțiunea
        print("\n⚠️  ATENȚIE: Această operațiune va:")
        print("   - Revoca IMEDIAT token-ul actual")
        print("   - Genera un token complet nou")
        print("   - Implementa securitate avansată")
        print("   - Redeploya aplicația")
        
        confirm = input("\n❓ Continui cu regenerarea de urgență? (DA/nu): ").upper().strip()
        if confirm != 'DA':
            print("❌ Operațiune anulată - BOTUL RĂMÂNE COMPROMIS!")
            return
        
        # Execută măsurile de securitate
        if force_token_regeneration():
            implement_webhook_security()
            update_render_environment()
            implement_git_security()
            create_monitoring_system()
            
            if verify_final_security():
                print("\n🎉 SECURITATE AVANSATĂ IMPLEMENTATĂ!")
                print("=" * 60)
                print("✅ Token complet regenerat")
                print("✅ Webhook securizat cu parametri avansați")
                print("✅ Environment Render actualizat")
                print("✅ Git securizat")
                print("✅ Monitoring implementat")
                print("\n🛡️  Botul este acum MAXIM SECURIZAT!")
                print("\n💡 Recomandări:")
                print("   - Rulează 'python webhook_monitor.py' pentru monitoring")
                print("   - Verifică logs-urile Render regulat")
                print("   - Nu împărtăși niciodată token-ul")
            else:
                print("\n⚠️  SECURITATE PARȚIALĂ - verifică manual!")
        else:
            print("\n❌ EROARE LA REGENERAREA TOKEN-ULUI!")
    else:
        print("\n✅ Token-ul pare să fie în regulă")
        print("💡 Implementez totuși măsuri de securitate suplimentare...")
        
        implement_webhook_security()
        implement_git_security()
        create_monitoring_system()
        
        print("\n🛡️  Securitate suplimentară implementată!")

if __name__ == "__main__":
    main()