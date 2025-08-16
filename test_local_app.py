#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test local pentru aplicația Flask cu Telegram bot
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Încarcă variabilele de mediu
load_dotenv()

def test_local_webhook():
    """Testează webhook-ul local"""
    print("🧪 TESTARE WEBHOOK LOCAL")
    print("=" * 50)
    
    # Simulează un update Telegram
    test_update = {
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
            "date": 1733428800,
            "text": "/start"
        }
    }
    
    try:
        # Testează webhook-ul local
        print("📡 Testez webhook local pe http://localhost:5000/webhook...")
        response = requests.post(
            'http://localhost:5000/webhook',
            json=test_update,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook local funcționează!")
        else:
            print(f"❌ Webhook local eșuat: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Nu pot conecta la serverul local. Asigură-te că aplicația rulează pe localhost:5000")
    except Exception as e:
        print(f"❌ Eroare la testarea webhook-ului local: {e}")

def test_health_endpoint():
    """Testează endpoint-ul de health"""
    try:
        print("\n🏥 Testez endpoint-ul /health...")
        response = requests.get('http://localhost:5000/health', timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Health endpoint funcționează!")
        else:
            print(f"❌ Health endpoint eșuat: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Nu pot conecta la serverul local pentru health check")
    except Exception as e:
        print(f"❌ Eroare la testarea health endpoint-ului: {e}")

if __name__ == '__main__':
    print("🚀 Pentru a rula acest test:")
    print("1. Deschide un terminal nou")
    print("2. Rulează: python app.py")
    print("3. Apoi rulează acest script în alt terminal")
    print("\n" + "="*50)
    
    test_health_endpoint()
    test_local_webhook()
    
    print("\n🎯 Dacă testele locale funcționează, problema este specifică Render.")
    print("🎯 Dacă testele locale eșuează, problema este în codul nostru.")