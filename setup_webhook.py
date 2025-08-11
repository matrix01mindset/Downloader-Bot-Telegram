
#!/usr/bin/env python3
# Script pentru configurarea webhook-ului Telegram

import requests
import sys

BOT_TOKEN = "8253089686:AAGbSnyOKFYt36_cjZdG5AaecRPCytvBDmI"
WEBHOOK_URL = "https://telegram-video-downloader-bot.onrender.com/webhook"

def set_webhook():
    """Setează webhook-ul Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        data = {
            'url': WEBHOOK_URL,
            'max_connections': 40,
            'allowed_updates': ['message', 'callback_query']
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Webhook setat cu succes: {WEBHOOK_URL}")
                return True
            else:
                print(f"❌ Eroare API: {result.get('description', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"❌ Eroare: {e}")
        return False

def get_webhook_info():
    """Verifică informațiile webhook-ului"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                info = result.get('result', {})
                print(f"
📊 INFORMAȚII WEBHOOK:")
                print(f"URL: {info.get('url', 'Nu este setat')}")
                print(f"Pending updates: {info.get('pending_update_count', 0)}")
                print(f"Ultima eroare: {info.get('last_error_message', 'Nicio eroare')}")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Eroare: {e}")
        return False

def main():
    print("🔗 CONFIGURARE WEBHOOK TELEGRAM")
    print("================================
")
    
    print(f"Bot Token: {BOT_TOKEN[:15]}...")
    print(f"Webhook URL: {WEBHOOK_URL}
")
    
    # Verifică webhook-ul curent
    print("📋 Verificare webhook curent...")
    get_webhook_info()
    
    # Setează noul webhook
    print("
📋 Setare webhook nou...")
    if set_webhook():
        print("
📋 Verificare finală...")
        get_webhook_info()
        print("
✅ Webhook configurat cu succes!")
        print("🤖 Botul este gata să primească mesaje!")
    else:
        print("
❌ Webhook nu a putut fi setat")
        print("🔍 Verifică că serviciul Render este activ")

if __name__ == "__main__":
    main()
