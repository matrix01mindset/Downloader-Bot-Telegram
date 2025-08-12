#!/usr/bin/env python3
# Script pentru corectarea URL-ului webhook-ului pe Render

import requests
import os
from dotenv import load_dotenv

# Încarcă variabilele de mediu
load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CORRECT_WEBHOOK_URL = "https://downloader-bot-telegram-nbix.onrender.com/webhook"

if not BOT_TOKEN:
    print("❌ EROARE: TELEGRAM_BOT_TOKEN nu este setat!")
    exit(1)

def get_current_webhook():
    """Obține informații despre webhook-ul curent"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                webhook_info = data['result']
                print(f"📋 Webhook curent: {webhook_info.get('url', 'Nu este setat')}")
                print(f"📊 Pending updates: {webhook_info.get('pending_update_count', 0)}")
                print(f"🔗 Last error: {webhook_info.get('last_error_message', 'Nicio eroare')}")
                return webhook_info
            else:
                print(f"❌ Eroare API: {data['description']}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare la obținerea webhook-ului: {e}")
    return None

def set_correct_webhook():
    """Setează webhook-ul cu URL-ul corect"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        data = {
            'url': CORRECT_WEBHOOK_URL,
            'max_connections': 40,
            'allowed_updates': ['message', 'callback_query']
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result['ok']:
                print(f"✅ Webhook setat cu succes la: {CORRECT_WEBHOOK_URL}")
                return True
            else:
                print(f"❌ Eroare la setarea webhook-ului: {result['description']}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare la setarea webhook-ului: {e}")
    return False

def main():
    print("🔧 Corectare URL webhook Telegram")
    print("=" * 40)
    
    print("\n📋 Verificare webhook curent...")
    current_webhook = get_current_webhook()
    
    if current_webhook:
        current_url = current_webhook.get('url', '')
        if current_url == CORRECT_WEBHOOK_URL:
            print(f"✅ Webhook-ul este deja setat corect: {CORRECT_WEBHOOK_URL}")
        else:
            print(f"\n⚠️ Webhook-ul este setat greșit: {current_url}")
            print(f"🔧 Setez webhook-ul corect: {CORRECT_WEBHOOK_URL}")
            
            if set_correct_webhook():
                print("\n✅ Webhook corectat cu succes!")
                print("\n📋 Verificare finală...")
                get_current_webhook()
            else:
                print("❌ Nu s-a putut corecta webhook-ul")
    else:
        print("\n🔧 Setez webhook-ul pentru prima dată...")
        if set_correct_webhook():
            print("✅ Webhook setat cu succes!")
        else:
            print("❌ Nu s-a putut seta webhook-ul")

if __name__ == "__main__":
    main()