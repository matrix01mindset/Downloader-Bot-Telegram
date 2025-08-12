#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pentru testarea directă a webhook-ului cu un update simulat
"""

import requests
import json
from datetime import datetime

def test_webhook_direct():
    """Testează webhook-ul cu un update simulat"""
    
    # URL-ul webhook-ului
    webhook_url = "https://telegram-video-downloader-1471.onrender.com/webhook"
    
    # Update simulat de la Telegram
    fake_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1625097600,
            "text": "/start"
        }
    }
    
    print("🧪 TESTARE DIRECTĂ WEBHOOK")
    print("=" * 50)
    print(f"📡 URL: {webhook_url}")
    print(f"📦 Update simulat: /start")
    print()
    
    try:
        # Trimite POST request cu update-ul simulat
        response = requests.post(
            webhook_url,
            json=fake_update,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'TelegramBot (like TwitterBot)'
            },
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Webhook funcționează corect!")
            try:
                response_json = response.json()
                print(f"📄 Răspuns JSON: {json.dumps(response_json, indent=2)}")
            except:
                print(f"📄 Răspuns text: {response.text}")
        else:
            print(f"❌ Webhook eșuat: {response.status_code}")
            print(f"📄 Răspuns: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Eroare de conexiune: {e}")
    except Exception as e:
        print(f"❌ Eroare neașteptată: {e}")

if __name__ == "__main__":
    test_webhook_direct()