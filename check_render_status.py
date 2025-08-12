#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script rapid pentru verificarea stării Render după actualizarea token-ului
"""

import requests
import json
from datetime import datetime

RENDER_URL = "https://downloader-bot-telegram-nbix.onrender.com"

def check_endpoint(endpoint, description):
    """Verifică un endpoint specific"""
    try:
        print(f"\n🔍 Testez {description}: {RENDER_URL}{endpoint}")
        response = requests.get(f"{RENDER_URL}{endpoint}", timeout=15)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Răspuns: {json.dumps(data, indent=2)}")
                return True, data
            except:
                print(f"   Răspuns text: {response.text[:200]}")
                return True, response.text
        else:
            print(f"   Eroare: {response.status_code} - {response.text[:200]}")
            return False, response.text
            
    except Exception as e:
        print(f"   Excepție: {str(e)}")
        return False, str(e)

def main():
    print("="*60)
    print("🔍 VERIFICARE RAPIDĂ STARE RENDER")
    print("="*60)
    print(f"⏰ Timp: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🌐 URL: {RENDER_URL}")
    
    # Lista de endpoint-uri de testat
    endpoints = [
        ("/", "Endpoint principal"),
        ("/health", "Health check"),
        ("/debug", "Debug info"),
        ("/ping", "Ping test"),
        ("/set_webhook", "Configurare webhook")
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        success, data = check_endpoint(endpoint, description)
        results[endpoint] = {
            "success": success,
            "data": data
        }
    
    print("\n" + "="*60)
    print("📊 REZUMAT VERIFICARE")
    print("="*60)
    
    # Analizează rezultatele
    server_online = results["/"]["success"]
    webhook_working = results["/set_webhook"]["success"]
    
    if server_online:
        print("✅ Server Render: ONLINE")
    else:
        print("❌ Server Render: OFFLINE")
    
    if webhook_working:
        print("✅ Webhook: CONFIGURAT")
        print("\n🎉 BOT-UL ESTE FUNCȚIONAL!")
        print("📱 Testează acum în Telegram:")
        print("   1. Trimite /start")
        print("   2. Trimite un link video")
    else:
        print("❌ Webhook: NECONFIGURAT")
        
        # Verifică dacă este problema de token
        if "/set_webhook" in results and not results["/set_webhook"]["success"]:
            error_data = results["/set_webhook"]["data"]
            if "400" in str(error_data) or "HTTP error 400" in str(error_data):
                print("\n🔧 PROBLEMA: TELEGRAM_BOT_TOKEN nu este setat corect")
                print("\n📋 SOLUȚII:")
                print("   1. Verifică Render Dashboard că token-ul este setat")
                print("   2. Așteaptă 2-3 minute pentru redeployare")
                print("   3. Verifică că token-ul este valid (format: 123456789:ABC...)")
                print("   4. Testează token-ul manual: https://api.telegram.org/bot[TOKEN]/getMe")
            else:
                print(f"\n🔧 EROARE NECUNOSCUTĂ: {error_data}")
    
    print("\n" + "="*60)
    print("⏰ Verificare completă")
    print("="*60)

if __name__ == "__main__":
    main()
    input("\nApasă Enter pentru a închide...")