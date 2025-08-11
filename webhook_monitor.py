
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
