#!/usr/bin/env python3
# Script pentru testarea health check-ului aplicației

import requests
import time

APP_URL = "https://downloader-bot-telegram-nbix.onrender.com"

def test_health_check():
    """Testează health check-ul aplicației"""
    try:
        print(f"🔍 Testez health check la: {APP_URL}/health")
        
        response = requests.get(f"{APP_URL}/health", timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Health check OK")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout - aplicația nu răspunde")
        return False
    except requests.exceptions.ConnectionError:
        print("🔌 Connection error - aplicația nu este disponibilă")
        return False
    except Exception as e:
        print(f"❌ Eroare: {e}")
        return False

def test_webhook_endpoint():
    """Testează endpoint-ul webhook"""
    try:
        print(f"\n🔍 Testez webhook endpoint la: {APP_URL}/webhook")
        
        # Test GET request
        response = requests.get(f"{APP_URL}/webhook", timeout=10)
        
        print(f"📊 Status Code (GET): {response.status_code}")
        print(f"📋 Response (GET): {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook GET OK")
            return True
        else:
            print(f"❌ Webhook GET failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Eroare webhook: {e}")
        return False

def test_main_page():
    """Testează pagina principală"""
    try:
        print(f"\n🔍 Testez pagina principală la: {APP_URL}")
        
        response = requests.get(APP_URL, timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Pagina principală OK")
            return True
        else:
            print(f"❌ Pagina principală failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Eroare pagina principală: {e}")
        return False

def main():
    print("🧪 Test aplicație Telegram Bot")
    print("=" * 40)
    
    # Test pagina principală
    main_ok = test_main_page()
    
    # Test health check
    health_ok = test_health_check()
    
    # Test webhook
    webhook_ok = test_webhook_endpoint()
    
    print("\n📊 Rezultate:")
    print(f"🏠 Pagina principală: {'✅ OK' if main_ok else '❌ FAIL'}")
    print(f"💚 Health check: {'✅ OK' if health_ok else '❌ FAIL'}")
    print(f"🔗 Webhook: {'✅ OK' if webhook_ok else '❌ FAIL'}")
    
    if all([main_ok, health_ok, webhook_ok]):
        print("\n🎉 Toate testele au trecut! Aplicația funcționează corect.")
    else:
        print("\n⚠️ Unele teste au eșuat. Aplicația are probleme.")

if __name__ == "__main__":
    main()