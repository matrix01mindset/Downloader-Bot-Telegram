#!/usr/bin/env python3
"""
Script rapid pentru verificarea statusului Render
"""

import requests
import time
from datetime import datetime

def check_render_status():
    base_url = "https://telegram-video-downloader-bot-t3d9.onrender.com"
    endpoints = [
        "/health",
        "/",
        "/debug",
        "/ping"
    ]
    
    print(f"🔍 Verificare rapidă status Render - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=10)
            print(f"✅ {endpoint}: HTTP {response.status_code}")
            if response.status_code == 200 and len(response.text) < 200:
                print(f"   📄 Response: {response.text[:100]}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: {type(e).__name__} - {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    
    # Test webhook specific
    try:
        webhook_url = f"{base_url}/set_webhook"
        response = requests.get(webhook_url, timeout=10)
        print(f"🔗 Webhook test: HTTP {response.status_code}")
        if response.status_code != 200:
            print(f"   ⚠️ Response: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"🔗 Webhook test: {type(e).__name__} - {str(e)[:50]}")

if __name__ == "__main__":
    check_render_status()