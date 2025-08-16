#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificare post-deployment pentru Render
Verifică că toate endpoint-urile funcționează corect
"""

import requests
import time
import json
import sys

def test_endpoint(url, endpoint_name, expected_status=200, timeout=10):
    """Testează un endpoint și returnează rezultatul"""
    try:
        print(f"🔍 Testez {endpoint_name}...")
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == expected_status:
            print(f"✅ {endpoint_name}: OK ({response.status_code})")
            return True, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        else:
            print(f"❌ {endpoint_name}: FAILED ({response.status_code})")
            return False, response.text
            
    except requests.exceptions.Timeout:
        print(f"⏰ {endpoint_name}: TIMEOUT")
        return False, "Timeout"
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name}: ERROR - {e}")
        return False, str(e)

def test_webhook_endpoint(base_url):
    """Testează endpoint-ul webhook cu un payload de test"""
    webhook_url = f"{base_url}/webhook"
    
    test_payload = {
        "update_id": 12345,
        "message": {
            "text": "/start",
            "chat": {"id": 123456, "type": "private"},
            "from": {"id": 123456, "first_name": "TestUser", "is_bot": False},
            "message_id": 1,
            "date": int(time.time())
        }
    }
    
    try:
        print("🔍 Testez webhook...")
        response = requests.post(
            webhook_url,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Webhook: OK (200)")
            return True, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        else:
            print(f"❌ Webhook: FAILED ({response.status_code})")
            return False, response.text
            
    except Exception as e:
        print(f"❌ Webhook: ERROR - {e}")
        return False, str(e)

def main():
    """Funcția principală de verificare"""
    if len(sys.argv) != 2:
        print("Utilizare: python verify_deployment.py <URL_APLICATIE>")
        print("Exemplu: python verify_deployment.py https://my-bot.onrender.com")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    
    print("🚀 Verificare deployment pe Render...")
    print(f"🔗 URL aplicație: {base_url}")
    print("=" * 60)
    
    # Lista de endpoint-uri de testat
    endpoints = [
        ('/', 'Root endpoint'),
        ('/health', 'Health check'),
        ('/ping', 'Ping endpoint'),
        ('/metrics', 'Metrics endpoint'),
        ('/set_webhook', 'Set webhook')
    ]
    
    results = {}
    
    # Testează fiecare endpoint
    for endpoint, name in endpoints:
        url = f"{base_url}{endpoint}"
        success, response = test_endpoint(url, name)
        results[name] = success
        
        # Afișează informații suplimentare pentru anumite endpoint-uri
        if success and endpoint == '/metrics':
            try:
                if isinstance(response, dict) and 'metrics' in response:
                    metrics = response['metrics']
                    print(f"  📊 Downloads: {metrics.get('downloads_total', 0)}")
                    print(f"  📊 Success rate: {metrics.get('success_rate', 0)}%")
                    print(f"  📊 Uptime: {metrics.get('uptime_hours', 0)}h")
            except:
                pass
        
        time.sleep(1)  # Pauză între teste
    
    # Testează webhook-ul
    webhook_success, webhook_response = test_webhook_endpoint(base_url)
    results['Webhook'] = webhook_success
    
    print("\n" + "=" * 60)
    print("📋 REZULTATE VERIFICARE:")
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    for test_name, success in results.items():
        status = "✅ TRECUT" if success else "❌ EȘUAT"
        print(f"  {test_name}: {status}")
    
    print(f"\n📊 SCOR FINAL: {passed_tests}/{total_tests} teste trecute")
    
    if passed_tests == total_tests:
        print("\n🎉 DEPLOYMENT VERIFICAT CU SUCCES!")
        print("💡 Bot-ul este gata de utilizare.")
        
        print(f"\n🔗 LINK-URI UTILE:")
        print(f"  • Health check: {base_url}/health")
        print(f"  • Metrici: {base_url}/metrics")
        print(f"  • Set webhook: {base_url}/set_webhook")
        
    elif passed_tests >= total_tests * 0.8:
        print("\n⚠️  DEPLOYMENT PARȚIAL REUȘIT")
        print("💡 Majoritatea funcționalităților funcționează.")
        
    else:
        print("\n❌ DEPLOYMENT EȘUAT")
        print("💡 Verifică logs-urile în Render și configurațiile.")
        sys.exit(1)
    
    # Recomandări finale
    print(f"\n💡 RECOMANDĂRI:")
    print(f"  • Monitorizează {base_url}/metrics pentru performanță")
    print(f"  • Verifică logs-urile în Render Dashboard")
    print(f"  • Testează bot-ul în Telegram cu link-uri reale")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    main()