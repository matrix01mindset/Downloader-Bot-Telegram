#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pentru curățarea webhook-ului și eliminarea update-urilor în așteptare
"""

import requests
import os
from dotenv import load_dotenv

# Încarcă variabilele de mediu
load_dotenv()

def clear_webhook():
    """Șterge webhook-ul și update-urile în așteptare"""
    
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN nu este setat!")
        return
    
    base_url = f"https://api.telegram.org/bot{TOKEN}"
    
    print("🧹 CURĂȚARE WEBHOOK ȘI UPDATE-URI")
    print("=" * 50)
    
    # 1. Șterge webhook-ul
    print("1️⃣ Șterg webhook-ul...")
    try:
        response = requests.post(f"{base_url}/deleteWebhook")
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Webhook șters cu succes!")
            else:
                print(f"❌ Eroare la ștergerea webhook-ului: {result.get('description')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare: {e}")
    
    # 2. Obține și șterge update-urile în așteptare
    print("\n2️⃣ Obțin update-urile în așteptare...")
    try:
        response = requests.get(f"{base_url}/getUpdates")
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                updates = result.get('result', [])
                print(f"📦 Găsite {len(updates)} update-uri în așteptare")
                
                if updates:
                    # Obține ID-ul ultimului update
                    last_update_id = max(update['update_id'] for update in updates)
                    
                    # Confirmă toate update-urile prin getUpdates cu offset
                    print(f"🗑️ Șterg update-urile până la ID {last_update_id}...")
                    response = requests.get(f"{base_url}/getUpdates", params={
                        'offset': last_update_id + 1
                    })
                    
                    if response.status_code == 200:
                        print("✅ Update-urile au fost șterse!")
                    else:
                        print(f"❌ Eroare la ștergerea update-urilor: {response.status_code}")
                else:
                    print("✅ Nu există update-uri în așteptare")
            else:
                print(f"❌ Eroare la obținerea update-urilor: {result.get('description')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare: {e}")
    
    # 3. Setează din nou webhook-ul
    print("\n3️⃣ Setez din nou webhook-ul...")
    webhook_url = "https://telegram-video-downloader-1471.onrender.com/webhook"
    
    try:
        response = requests.post(f"{base_url}/setWebhook", json={
            'url': webhook_url
        })
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Webhook setat cu succes: {webhook_url}")
            else:
                print(f"❌ Eroare la setarea webhook-ului: {result.get('description')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare: {e}")
    
    # 4. Verifică starea finală
    print("\n4️⃣ Verific starea finală...")
    try:
        response = requests.get(f"{base_url}/getWebhookInfo")
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                info = result.get('result', {})
                print(f"📋 URL: {info.get('url', 'Nu este setat')}")
                print(f"📋 Pending updates: {info.get('pending_update_count', 0)}")
                print(f"📋 Last error: {info.get('last_error_message', 'Nicio eroare')}")
            else:
                print(f"❌ Eroare: {result.get('description')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare: {e}")
    
    print("\n🎉 Curățare completă!")

if __name__ == "__main__":
    clear_webhook()