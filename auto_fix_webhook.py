#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script automat pentru repararea webhook-ului bot-ului Telegram
Rulează acest script după ce ai setat TELEGRAM_BOT_TOKEN pe Render
"""

import requests
import time
import json
from datetime import datetime

# Configurare
RENDER_URL = "https://telegram-video-downloader-bot-t3d9.onrender.com"
MAX_RETRIES = 10
WAIT_TIME = 30  # secunde între încercări

def print_status(message, status="INFO"):
    """Afișează mesaj cu timestamp și status"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "WAIT": "⏳"
    }
    symbol = symbols.get(status, "📍")
    print(f"[{timestamp}] {symbol} {message}")

def check_token_status():
    """Verifică dacă token-ul este setat pe Render"""
    try:
        response = requests.get(f"{RENDER_URL}/debug", timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Verifică dacă există informații despre token
            if "TELEGRAM_BOT_TOKEN" in str(data):
                return True, "Token detectat în debug"
            return False, "Token nu este vizibil în debug"
        return False, f"Debug endpoint returnează {response.status_code}"
    except Exception as e:
        return False, f"Eroare la verificarea token-ului: {str(e)}"

def configure_webhook():
    """Configurează webhook-ul"""
    try:
        response = requests.get(f"{RENDER_URL}/set_webhook", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return True, "Webhook configurat cu succes"
            return False, f"Webhook failed: {data.get('message', 'Unknown error')}"
        return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Eroare la configurarea webhook-ului: {str(e)}"

def test_bot_health():
    """Testează starea generală a bot-ului"""
    endpoints = ["/", "/health", "/ping"]
    results = {}
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{RENDER_URL}{endpoint}", timeout=10)
            results[endpoint] = {
                "status": response.status_code,
                "success": response.status_code == 200
            }
        except Exception as e:
            results[endpoint] = {
                "status": "ERROR",
                "success": False,
                "error": str(e)
            }
    
    return results

def main():
    """Funcția principală de reparare automată"""
    print("="*60)
    print("🔧 SCRIPT AUTOMAT DE REPARARE WEBHOOK")
    print("="*60)
    print_status(f"Începe repararea pentru: {RENDER_URL}")
    
    # Verifică starea inițială
    print_status("Verifică starea serverului...")
    health_results = test_bot_health()
    
    server_ok = all(result["success"] for result in health_results.values())
    if not server_ok:
        print_status("Server-ul nu răspunde corect!", "ERROR")
        for endpoint, result in health_results.items():
            if not result["success"]:
                print_status(f"  {endpoint}: {result.get('status', 'ERROR')}", "ERROR")
        return False
    
    print_status("Server-ul funcționează corect", "SUCCESS")
    
    # Bucla de așteptare pentru token
    print_status("Verifică dacă TELEGRAM_BOT_TOKEN este setat...")
    
    for attempt in range(1, MAX_RETRIES + 1):
        print_status(f"Încercarea {attempt}/{MAX_RETRIES}")
        
        # Verifică token-ul
        token_ok, token_msg = check_token_status()
        print_status(f"Token status: {token_msg}")
        
        if token_ok:
            print_status("Token detectat! Configurez webhook-ul...", "SUCCESS")
            
            # Configurează webhook-ul
            webhook_ok, webhook_msg = configure_webhook()
            print_status(f"Webhook: {webhook_msg}")
            
            if webhook_ok:
                print_status("🎉 REPARARE COMPLETĂ! Bot-ul este funcțional!", "SUCCESS")
                print("\n" + "="*60)
                print("✅ SUCCES - BOT-UL FUNCȚIONEAZĂ")
                print("="*60)
                print("📱 Testează acum bot-ul în Telegram:")
                print("   1. Trimite /start")
                print("   2. Trimite un link TikTok/YouTube/Instagram")
                print("   3. Așteaptă descărcarea video-ului")
                print("="*60)
                return True
            else:
                print_status(f"Webhook failed: {webhook_msg}", "ERROR")
        
        if attempt < MAX_RETRIES:
            print_status(f"Aștept {WAIT_TIME} secunde înainte de următoarea încercare...", "WAIT")
            time.sleep(WAIT_TIME)
    
    # Dacă ajunge aici, nu a reușit
    print_status("❌ REPARAREA A EȘUAT!", "ERROR")
    print("\n" + "="*60)
    print("❌ EROARE - VERIFICĂ MANUAL")
    print("="*60)
    print("🔧 PAȘI MANUALI:")
    print("   1. Mergi pe https://dashboard.render.com")
    print("   2. Selectează serviciul telegram-video-downloader-bot-t3d9")
    print("   3. Verifică că TELEGRAM_BOT_TOKEN este setat corect")
    print("   4. Redeploy serviciul dacă este necesar")
    print("   5. Rulează din nou acest script")
    print("="*60)
    return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Script finalizat cu succes!")
        else:
            print("\n❌ Script finalizat cu erori!")
    except KeyboardInterrupt:
        print("\n⏹️ Script oprit de utilizator")
    except Exception as e:
        print(f"\n💥 Eroare neașteptată: {str(e)}")
    
    input("\nApasă Enter pentru a închide...")