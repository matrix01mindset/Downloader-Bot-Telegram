#!/usr/bin/env python3
"""
Script pentru testarea statusului TOKEN-ului pe Render
"""

import requests
import time
from datetime import datetime

def test_token_status():
    base_url = "https://telegram-video-downloader-bot-t3d9.onrender.com"
    
    print(f"🔍 Testare status TOKEN Telegram - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Test debug endpoint pentru informații despre token
    try:
        debug_url = f"{base_url}/debug"
        response = requests.get(debug_url, timeout=10)
        print(f"✅ Debug endpoint: HTTP {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   📄 Response: {data}")
    except Exception as e:
        print(f"❌ Debug endpoint: {e}")
    
    print("\n" + "-" * 40)
    
    # Test direct webhook cu detalii complete
    try:
        webhook_url = f"{base_url}/set_webhook"
        print(f"🔗 Testare webhook: {webhook_url}")
        response = requests.get(webhook_url, timeout=15)
        print(f"   Status: HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 500:
            try:
                error_data = response.json()
                print(f"   📋 Error details: {error_data}")
            except:
                print(f"   📋 Raw error: {response.text}")
                
    except Exception as e:
        print(f"❌ Webhook test: {e}")
    
    print("\n" + "=" * 60)
    print("📊 ANALIZA:")
    print("- Dacă debug arată 'app_initialized': true, serverul funcționează")
    print("- Dacă webhook returnează 'HTTP error 400', TOKEN-ul nu este valid")
    print("- Dacă webhook returnează 'bad webhook', URL-ul nu este HTTPS")
    print("- Dacă webhook returnează success, totul funcționează!")

if __name__ == "__main__":
    test_token_status()