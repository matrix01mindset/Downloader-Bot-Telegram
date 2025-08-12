#!/usr/bin/env python3
"""
Script pentru debugging URL-ul webhook-ului
"""

import requests
import time
from datetime import datetime

def debug_webhook_url():
    base_url = "https://telegram-video-downloader-bot-t3d9.onrender.com"
    
    print(f"🔍 Debug Webhook URL - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Creează un endpoint de test pentru a vedea ce URL se generează
    test_script = '''
import requests
from flask import request

# Simulează ce se întâmplă în funcția set_webhook
current_url = "https://telegram-video-downloader-bot-t3d9.onrender.com"
print(f"URL de bază: {current_url}")

# Verifică dacă începe cu http://
if current_url.startswith('http://'):
    current_url = current_url.replace('http://', 'https://', 1)
    print(f"URL după conversie: {current_url}")
else:
    print("URL-ul este deja HTTPS")

webhook_url = f"{current_url}/webhook"
print(f"URL final webhook: {webhook_url}")
'''
    
    print("📋 Simulare generare URL webhook:")
    # SECURITATE: Înlocuit exec() cu cod sigur
    try:
        # Simulează logica din test_script în mod sigur
        current_url = "https://telegram-video-downloader-bot.onrender.com"
        if current_url.startswith("http://"):
            current_url = current_url.replace("http://", "https://")
            print("URL convertit la HTTPS")
        else:
            print("URL-ul este deja HTTPS")
        
        webhook_url = f"{current_url}/webhook"
        print(f"URL final webhook: {webhook_url}")
    except Exception as e:
        print(f"Eroare la generarea URL-ului: {e}")
    
    print("\n" + "-" * 40)
    
    # Test direct cu Telegram API pentru a vedea răspunsul exact
    print("🔗 Test direct cu Telegram API:")
    
    # Încearcă să obții informații despre webhook-ul curent
    try:
        webhook_info_url = f"{base_url}/get_webhook_info"
        print(f"Testez: {webhook_info_url}")
        response = requests.get(webhook_info_url, timeout=10)
        print(f"Status: HTTP {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.text}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"❌ Eroare la testarea webhook info: {e}")
    
    print("\n" + "-" * 40)
    
    # Test setare webhook cu logging detaliat
    try:
        webhook_url = f"{base_url}/set_webhook"
        print(f"🔧 Testez setarea webhook: {webhook_url}")
        response = requests.get(webhook_url, timeout=15)
        print(f"Status: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 500:
            try:
                error_data = response.json()
                print(f"📋 Detalii eroare: {error_data}")
                
                # Analizează tipul de eroare
                message = error_data.get('message', '')
                if 'HTTP error 400' in message:
                    print("\n🚨 PROBLEMA: Token invalid sau webhook URL incorect")
                elif 'bad webhook' in message:
                    print("\n🚨 PROBLEMA: URL-ul webhook nu este HTTPS")
                elif 'HTTP error 429' in message:
                    print("\n⏳ PROBLEMA: Rate limiting - prea multe cereri")
                    
            except:
                print(f"📋 Raw error: {response.text}")
                
    except Exception as e:
        print(f"❌ Eroare la testarea webhook: {e}")
    
    print("\n" + "=" * 60)
    print("📊 CONCLUZIE:")
    print("- Dacă URL-ul generat este HTTPS, problema este la token")
    print("- Dacă URL-ul generat este HTTP, fix-ul nu funcționează")
    print("- Dacă primești 'bad webhook', URL-ul nu este HTTPS")
    print("- Dacă primești 'HTTP error 400', token-ul nu este valid")

if __name__ == "__main__":
    debug_webhook_url()