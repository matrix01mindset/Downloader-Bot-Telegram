#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 SCRIPT TESTARE BOT TELEGRAM PE RENDER
Verifică starea bot-ului deployat pe Render și identifică problemele
"""

import requests
import json
import os
from datetime import datetime

# Configurare
RENDER_URL = "https://telegram-video-downloader-bot-t3d9.onrender.com"
TEST_TIMEOUT = 30

def print_header(title):
    """Printează un header frumos"""
    print("\n" + "="*60)
    print(f"🔧 {title}")
    print("="*60)

def print_status(status, message):
    """Printează status cu emoji"""
    emoji = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
    print(f"{emoji} {message}")

def test_render_endpoints():
    """Testează toate endpoint-urile Render"""
    print_header("TESTARE ENDPOINT-URI RENDER")
    
    endpoints = {
        "Homepage": "/",
        "Health Check": "/health",
        "Debug Info": "/debug",
        "Ping": "/ping"
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            url = f"{RENDER_URL}{endpoint}"
            print(f"\n📍 Testez {name}: {url}")
            
            response = requests.get(url, timeout=TEST_TIMEOUT)
            
            if response.status_code == 200:
                print_status("success", f"{name} funcționează (200 OK)")
                try:
                    data = response.json()
                    print(f"   Răspuns: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                    results[name] = {"status": "success", "data": data}
                except:
                    print(f"   Răspuns text: {response.text[:200]}...")
                    results[name] = {"status": "success", "text": response.text[:200]}
            else:
                print_status("error", f"{name} eșuat ({response.status_code})")
                print(f"   Eroare: {response.text[:200]}")
                results[name] = {"status": "error", "code": response.status_code, "text": response.text[:200]}
                
        except requests.exceptions.Timeout:
            print_status("error", f"{name} - Timeout după {TEST_TIMEOUT}s")
            results[name] = {"status": "error", "error": "timeout"}
        except requests.exceptions.ConnectionError:
            print_status("error", f"{name} - Eroare de conexiune")
            results[name] = {"status": "error", "error": "connection_error"}
        except Exception as e:
            print_status("error", f"{name} - Eroare: {str(e)}")
            results[name] = {"status": "error", "error": str(e)}
    
    return results

def test_webhook_setup():
    """Testează configurarea webhook-ului"""
    print_header("TESTARE CONFIGURARE WEBHOOK")
    
    try:
        url = f"{RENDER_URL}/set_webhook"
        print(f"📍 Testez configurarea webhook: {url}")
        
        response = requests.get(url, timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print_status("success", "Webhook configurat cu succes")
                print(f"   URL Webhook: {data.get('message', 'N/A')}")
                return {"status": "success", "data": data}
            else:
                print_status("error", f"Webhook eșuat: {data.get('message', 'N/A')}")
                return {"status": "error", "data": data}
        else:
            print_status("error", f"Eroare HTTP {response.status_code}")
            print(f"   Răspuns: {response.text[:200]}")
            return {"status": "error", "code": response.status_code, "text": response.text[:200]}
            
    except Exception as e:
        print_status("error", f"Eroare la configurarea webhook: {str(e)}")
        return {"status": "error", "error": str(e)}

def test_telegram_api():
    """Testează conectivitatea cu API-ul Telegram"""
    print_header("TESTARE API TELEGRAM")
    
    # Încercăm să obținem token-ul din variabilele de mediu locale
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print_status("warning", "Token Telegram nu este disponibil local")
        print("   Nu pot testa direct API-ul Telegram")
        return {"status": "skipped", "reason": "no_token"}
    
    try:
        # Testează getMe
        url = f"https://api.telegram.org/bot{token}/getMe"
        print(f"📍 Testez API Telegram: getMe")
        
        response = requests.get(url, timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print_status("success", "API Telegram funcționează")
                print(f"   Bot: @{bot_info.get('username', 'N/A')} ({bot_info.get('first_name', 'N/A')})")
                print(f"   ID: {bot_info.get('id', 'N/A')}")
                return {"status": "success", "bot_info": bot_info}
            else:
                print_status("error", f"API Telegram eșuat: {data.get('description', 'N/A')}")
                return {"status": "error", "data": data}
        else:
            print_status("error", f"Eroare HTTP {response.status_code}")
            return {"status": "error", "code": response.status_code}
            
    except Exception as e:
        print_status("error", f"Eroare la testarea API Telegram: {str(e)}")
        return {"status": "error", "error": str(e)}

def generate_report(endpoint_results, webhook_result, telegram_result):
    """Generează raportul final"""
    print_header("RAPORT FINAL - DIAGNOZĂ PROBLEMĂ")
    
    print(f"📅 Data testării: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL Render: {RENDER_URL}")
    
    # Analizează rezultatele
    server_online = any(r.get('status') == 'success' for r in endpoint_results.values())
    webhook_configured = webhook_result.get('status') == 'success'
    telegram_api_ok = telegram_result.get('status') == 'success'
    
    print("\n📊 STARE COMPONENTE:")
    print_status("success" if server_online else "error", f"Server Render: {'Online' if server_online else 'Offline/Probleme'}")
    print_status("success" if webhook_configured else "error", f"Webhook: {'Configurat' if webhook_configured else 'Neconfigurat/Probleme'}")
    
    if telegram_result.get('status') == 'skipped':
        print_status("warning", "API Telegram: Nu s-a putut testa (token lipsă local)")
    else:
        print_status("success" if telegram_api_ok else "error", f"API Telegram: {'Funcțional' if telegram_api_ok else 'Probleme'}")
    
    print("\n🔍 DIAGNOZĂ:")
    
    if not server_online:
        print("❌ PROBLEMĂ PRINCIPALĂ: Serverul Render nu răspunde")
        print("   Soluții:")
        print("   1. Verifică logs-urile pe Render Dashboard")
        print("   2. Verifică că variabilele de mediu sunt setate corect")
        print("   3. Redeployează aplicația")
    elif not webhook_configured:
        print("❌ PROBLEMĂ PRINCIPALĂ: Webhook-ul nu este configurat")
        print("   Soluții:")
        print(f"   1. Vizitează: {RENDER_URL}/set_webhook")
        print("   2. Verifică că TELEGRAM_BOT_TOKEN este setat în Render")
        print("   3. Verifică logs-urile pentru erori de autentificare")
    elif telegram_result.get('status') == 'error':
        print("❌ PROBLEMĂ PRINCIPALĂ: Token Telegram invalid sau expirat")
        print("   Soluții:")
        print("   1. Verifică token-ul în BotFather")
        print("   2. Regenerează token-ul dacă este necesar")
        print("   3. Actualizează variabila TELEGRAM_BOT_TOKEN în Render")
    else:
        print("✅ TOATE COMPONENTELE PAR FUNCȚIONALE")
        print("   Dacă bot-ul nu răspunde, verifică:")
        print("   1. Că ai trimis /start bot-ului")
        print("   2. Logs-urile pentru erori de procesare")
        print("   3. Că URL-urile sunt suportate")
    
    print("\n📋 PAȘI URMĂTORI:")
    print("1. Verifică Render Dashboard pentru logs și status")
    print("2. Testează manual bot-ul în Telegram")
    print("3. Monitorizează logs-urile în timp real")
    print(f"4. Folosește {RENDER_URL}/debug pentru informații suplimentare")

def main():
    """Funcția principală"""
    print_header("DIAGNOZĂ TELEGRAM BOT PE RENDER")
    print(f"🎯 Testez bot-ul deployat la: {RENDER_URL}")
    
    # Rulează testele
    endpoint_results = test_render_endpoints()
    webhook_result = test_webhook_setup()
    telegram_result = test_telegram_api()
    
    # Generează raportul
    generate_report(endpoint_results, webhook_result, telegram_result)
    
    print("\n" + "="*60)
    print("🏁 TESTARE COMPLETĂ")
    print("="*60)

if __name__ == "__main__":
    main()