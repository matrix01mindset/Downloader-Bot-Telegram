#!/usr/bin/env python3
"""
Script pentru testarea și setarea webhook-ului Telegram Bot pe Render
"""

import requests
import os
from dotenv import load_dotenv

# Încarcă variabilele de mediu
load_dotenv()

# Configurare - token încărcat din variabile de mediu pentru securitate
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ EROARE: TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu!")
    print("Setează variabila de mediu sau creează un fișier .env")
    exit(1)
# URL-ul aplicației Render deployate
RENDER_URL = "https://telegram-video-downloader-1471.onrender.com"
RENDER_APP_NAME = "telegram-video-downloader-1471"
WEBHOOK_URL = f"{RENDER_URL}/webhook"

def verify_render_app():
    """Verifică că aplicația Render deployată este funcțională"""
    print(f"🔍 Verific aplicația Render: {RENDER_URL}")
    
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=15)
        if response.status_code == 200:
            print(f"✅ Aplicația este online și funcțională!")
            print(f"   Răspuns: {response.json()}")
            return True
        else:
            print(f"❌ Aplicația nu răspunde corect: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Eroare la conectarea la aplicație: {e}")
        return False

def test_render_app():
    """Testează dacă aplicația Render găsită este funcțională"""
    if not RENDER_URL:
        return False
        
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Aplicația Render este online: {RENDER_URL}")
            print(f"Răspuns: {response.json()}")
            return True
        else:
            print(f"❌ Aplicația Render nu răspunde corect: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Eroare la conectarea la Render: {e}")
        return False

def get_webhook_info():
    """Verifică informațiile webhook-ului curent"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                webhook_info = data['result']
                print(f"\n📋 Informații webhook curent:")
                print(f"URL: {webhook_info.get('url', 'Nu este setat')}")
                print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
                print(f"Last error: {webhook_info.get('last_error_message', 'Nicio eroare')}")
                return webhook_info
            else:
                print(f"❌ Eroare API Telegram: {data}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare la verificarea webhook-ului: {e}")
    return None

def set_webhook():
    """Setează webhook-ul pentru bot cu URL-ul corect"""
    try:
        # Setează webhook-ul direct prin API Telegram cu URL-ul corect
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        data = {'url': WEBHOOK_URL}
        response = requests.post(telegram_url, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Webhook setat cu succes prin API Telegram!")
                print(f"   URL: {WEBHOOK_URL}")
                print(f"   Răspuns: {result.get('description', 'Success')}")
                return True
            else:
                print(f"❌ Eroare API Telegram: {result.get('description', 'Eroare necunoscută')}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Eroare la setarea webhook-ului: {e}")
    
    return False

def test_bot():
    """Testează bot-ul trimițând o comandă de test"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot_info = data['result']
                print(f"\n🤖 Informații bot:")
                print(f"Nume: {bot_info['first_name']}")
                print(f"Username: @{bot_info['username']}")
                print(f"ID: {bot_info['id']}")
                return True
            else:
                print(f"❌ Eroare API: {data}")
        else:
            print(f"❌ Eroare HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Eroare la testarea bot-ului: {e}")
    return False

def main():
    print("🔧 TESTARE ȘI SETARE WEBHOOK TELEGRAM BOT")
    print("=" * 50)
    
    print(f"\n📍 Configurare:")
    print(f"Bot Token: {BOT_TOKEN[:10]}...")
    print(f"Render URL: {RENDER_URL}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    
    print("\n1️⃣ Testez bot-ul...")
    if not test_bot():
        print("❌ Bot-ul nu funcționează. Verifică token-ul.")
        return
    
    print("\n2️⃣ Verific aplicația Render deployată...")
    if not verify_render_app():
        print("❌ Aplicația Render nu este accesibilă.")
        print("\n💡 Sugestii:")
        print("1. Verifică că deployment-ul s-a finalizat cu succes")
        print("2. Verifică că serviciul este 'Live' (verde) în dashboard")
        print("3. Așteaptă câteva minute pentru inițializare")
        return
    
    print("\n3️⃣ Verific webhook-ul curent...")
    get_webhook_info()
    
    print("\n4️⃣ Setez webhook-ul nou...")
    if set_webhook():
        print("✅ Webhook setat cu succes!")
    else:
        print("❌ Nu s-a putut seta webhook-ul.")
        return
    
    print("\n5️⃣ Verific webhook-ul după setare...")
    get_webhook_info()
    
    print("\n🎉 Configurare completă!")
    print("\n📱 Acum testează bot-ul în Telegram:")
    print("1. Caută bot-ul după username: @matrixdownload_bot")
    print("2. Trimite /start")
    print("3. Trimite un link YouTube pentru test")
    print(f"\n🔗 URL aplicație: {RENDER_URL}")
    print(f"🔗 Health check: {RENDER_URL}/health")
    print(f"🔗 Set webhook: {RENDER_URL}/set_webhook")

if __name__ == "__main__":
    main()