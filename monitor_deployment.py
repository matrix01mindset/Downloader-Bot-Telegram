#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de monitorizare deployment Render
Monitorizează când serviciul se finalizează și webhook-ul devine funcțional
"""

import requests
import time
import json
from datetime import datetime

# Configurare
RENDER_URL = "https://telegram-video-downloader-bot-t3d9.onrender.com"
CHECK_INTERVAL = 15  # secunde între verificări
MAX_WAIT_TIME = 600  # 10 minute maxim

def print_status(message, status="INFO"):
    """Afișează mesaj cu timestamp și status"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "WAIT": "⏳",
        "DEPLOY": "🚀"
    }
    symbol = symbols.get(status, "📍")
    print(f"[{timestamp}] {symbol} {message}")

def check_server_status():
    """Verifică dacă serverul răspunde"""
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_webhook_status():
    """Verifică dacă webhook-ul funcționează"""
    try:
        response = requests.get(f"{RENDER_URL}/set_webhook", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return True, "Webhook configurat cu succes"
            return False, f"Webhook error: {data.get('message', 'Unknown')}"
        elif response.status_code == 500:
            # Verifică dacă este încă problema de token
            try:
                error_data = response.json()
                if "HTTP error 400" in str(error_data):
                    return False, "Token încă nu este activ"
                return False, f"Server error: {error_data}"
            except:
                return False, "Server error 500"
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def main():
    """Funcția principală de monitorizare"""
    print("="*70)
    print("🚀 MONITORIZARE DEPLOYMENT RENDER")
    print("="*70)
    print_status(f"Monitorizez: {RENDER_URL}", "DEPLOY")
    print_status(f"Interval verificare: {CHECK_INTERVAL} secunde", "INFO")
    print_status(f"Timeout maxim: {MAX_WAIT_TIME // 60} minute", "INFO")
    print("="*70)
    
    start_time = time.time()
    attempt = 0
    
    while True:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        print_status(f"Verificarea #{attempt} (după {elapsed}s)", "INFO")
        
        # Verifică dacă a trecut timpul maxim
        if elapsed > MAX_WAIT_TIME:
            print_status("Timeout atins! Deployment-ul durează prea mult.", "ERROR")
            print("\n" + "="*70)
            print("⏰ TIMEOUT - VERIFICĂ MANUAL")
            print("="*70)
            print("🔧 Acțiuni recomandate:")
            print("   1. Verifică Render Dashboard pentru erori")
            print("   2. Verifică logs-urile serviciului")
            print("   3. Verifică că token-ul este corect")
            print("   4. Consideră un redeploy manual")
            break
        
        # Verifică starea serverului
        server_ok, server_data = check_server_status()
        
        if not server_ok:
            print_status(f"Server offline: {server_data}", "WARNING")
            print_status("Deployment încă în curs...", "DEPLOY")
        else:
            print_status("Server online!", "SUCCESS")
            
            # Verifică webhook-ul
            webhook_ok, webhook_msg = check_webhook_status()
            
            if webhook_ok:
                print_status("Webhook funcțional!", "SUCCESS")
                print("\n" + "="*70)
                print("🎉 DEPLOYMENT COMPLET - BOT FUNCȚIONAL!")
                print("="*70)
                print("✅ Server: Online")
                print("✅ Webhook: Configurat")
                print("✅ Token: Activ")
                print("\n📱 BOT-UL ESTE GATA DE UTILIZARE!")
                print("\n🧪 Testează acum:")
                print("   1. Deschide Telegram")
                print("   2. Trimite /start către bot")
                print("   3. Trimite un link video (TikTok/YouTube/Instagram)")
                print("   4. Așteaptă descărcarea")
                print("\n" + "="*70)
                break
            else:
                print_status(f"Webhook: {webhook_msg}", "WARNING")
                if "Token încă nu este activ" in webhook_msg:
                    print_status("Deployment încă în curs...", "DEPLOY")
                else:
                    print_status(f"Problemă neașteptată: {webhook_msg}", "ERROR")
        
        # Așteaptă înainte de următoarea verificare
        print_status(f"Următoarea verificare în {CHECK_INTERVAL}s...", "WAIT")
        time.sleep(CHECK_INTERVAL)
    
    print(f"\n⏰ Monitorizare finalizată după {int(time.time() - start_time)} secunde")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Monitorizare oprită de utilizator")
    except Exception as e:
        print(f"\n💥 Eroare: {str(e)}")
    
    input("\nApasă Enter pentru a închide...")