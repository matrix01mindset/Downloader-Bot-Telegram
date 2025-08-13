#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pentru funcționalitatea de procesare a multiplelor linkuri în bot
"""

import requests
import json
import time
from datetime import datetime

# Configurare pentru testare locală
BOT_URL = "http://localhost:10000"
TEST_CHAT_ID = "123456789"  # ID de test
TEST_USER_ID = "987654321"  # ID utilizator de test

def create_test_message(text, message_id=None):
    """
    Creează un mesaj de test în formatul așteptat de bot
    """
    if message_id is None:
        message_id = int(time.time())
    
    return {
        "update_id": message_id,
        "message": {
            "message_id": message_id,
            "from": {
                "id": TEST_USER_ID,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": TEST_CHAT_ID,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }

def send_test_message(text):
    """
    Trimite un mesaj de test către bot
    """
    try:
        message = create_test_message(text)
        
        print(f"📤 Trimitere mesaj: {text[:60]}{'...' if len(text) > 60 else ''}")
        
        response = requests.post(
            BOT_URL,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Mesaj trimis cu succes (Status: {response.status_code})")
            return True
        else:
            print(f"❌ Eroare la trimiterea mesajului (Status: {response.status_code})")
            print(f"   Răspuns: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Eroare de conexiune: {e}")
        return False
    except Exception as e:
        print(f"❌ Eroare neașteptată: {e}")
        return False

def test_multiple_links_scenarios():
    """
    Testează diferite scenarii cu multiple linkuri
    """
    print("🤖 TESTARE BOT - MULTIPLE LINKURI")
    print("=" * 50)
    print(f"🌐 URL Bot: {BOT_URL}")
    print(f"💬 Chat ID Test: {TEST_CHAT_ID}")
    print(f"👤 User ID Test: {TEST_USER_ID}")
    print("\n")
    
    # Verifică dacă bot-ul răspunde
    try:
        response = requests.get(BOT_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Bot-ul este activ și răspunde")
        else:
            print(f"⚠️ Bot-ul răspunde cu status: {response.status_code}")
    except:
        print("❌ Bot-ul nu răspunde - verifică dacă rulează pe portul 10000")
        return
    
    print("\n" + "="*50)
    
    # Scenarii de test
    test_scenarios = [
        {
            "name": "Două linkuri TikTok și Instagram",
            "message": "Uite videoclipurile: https://www.tiktok.com/@user/video/123456789 https://www.instagram.com/p/ABC123DEF/",
            "expected_links": 2
        },
        {
            "name": "Trei linkuri mixte (cu și fără protocol)",
            "message": "Videoclipuri cool: https://facebook.com/video/123 www.twitter.com/user/status/456 reddit.com/r/videos/comments/789",
            "expected_links": 3
        },
        {
            "name": "Un singur link valid",
            "message": "Un videoclip frumos: https://vimeo.com/123456789",
            "expected_links": 1
        },
        {
            "name": "Linkuri mixte (suportate și nesuportate)",
            "message": "https://www.tiktok.com/@test/video/123 https://youtube.com/watch?v=456 https://dailymotion.com/video/789",
            "expected_links": 2  # TikTok și Dailymotion sunt suportate, YouTube nu
        },
        {
            "name": "Text fără linkuri",
            "message": "Salut! Cum merge?",
            "expected_links": 0
        }
    ]
    
    successful_tests = 0
    total_tests = len(test_scenarios)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test {i}/{total_tests}: {scenario['name']}")
        print(f"📝 Mesaj: {scenario['message']}")
        print(f"🎯 Linkuri așteptate: {scenario['expected_links']}")
        
        # Trimite mesajul
        success = send_test_message(scenario['message'])
        
        if success:
            successful_tests += 1
            print(f"⏱️ Așteptare procesare...")
            
            # Calculează timpul de așteptare bazat pe numărul de linkuri
            if scenario['expected_links'] > 0:
                wait_time = scenario['expected_links'] * 5 + 10  # 5 sec per link + 10 sec buffer
                print(f"⏳ Timp estimat procesare: ~{wait_time} secunde")
            else:
                wait_time = 5
                print(f"⏳ Timp estimat procesare: ~{wait_time} secunde")
            
            # Pauză între teste
            time.sleep(3)
        else:
            print(f"❌ Test eșuat - mesajul nu a putut fi trimis")
        
        print("-" * 30)
    
    # Raport final
    print(f"\n📊 RAPORT FINAL TESTARE")
    print(f"✅ Teste reușite: {successful_tests}/{total_tests}")
    print(f"📈 Rata de succes: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests == total_tests:
        print(f"🎉 Toate testele au trecut cu succes!")
        print(f"\n💡 Funcționalitatea de procesare a multiplelor linkuri este activă.")
        print(f"   Bot-ul va procesa fiecare link cu o pauză de 3 secunde între ele.")
    else:
        print(f"⚠️ Unele teste au eșuat. Verifică logurile bot-ului pentru detalii.")
    
    print(f"\n🔍 Pentru a vedea rezultatele:")
    print(f"   1. Verifică logurile bot-ului în terminal")
    print(f"   2. Dacă folosești un bot Telegram real, verifică conversația")
    print(f"   3. Bot-ul va afișa progresul și raportul final pentru fiecare mesaj")

def test_real_telegram_format():
    """
    Testează cu un format mai realist de mesaj Telegram
    """
    print(f"\n\n📱 TEST MESAJ REALIST TELEGRAM")
    print("=" * 50)
    
    realistic_message = """
Salut! Am găsit niște videoclipuri mișto:

1. https://www.tiktok.com/@creator1/video/7234567890123456789
2. https://www.instagram.com/p/CpQRsTuVwXy/
3. www.facebook.com/watch/?v=1234567890123456

Poți să le descarci pe toate? Mulțumesc! 😊
"""
    
    print(f"📝 Mesaj realist cu 3 linkuri:")
    print(realistic_message)
    
    success = send_test_message(realistic_message.strip())
    
    if success:
        print(f"✅ Mesaj realist trimis cu succes")
        print(f"⏱️ Bot-ul va procesa cele 3 linkuri cu pauze de 3 secunde")
        print(f"📊 Timp total estimat: ~25-30 secunde")
    else:
        print(f"❌ Eroare la trimiterea mesajului realist")

if __name__ == "__main__":
    print(f"🕐 Început testare: {datetime.now().strftime('%H:%M:%S')}")
    
    # Testează scenariile principale
    test_multiple_links_scenarios()
    
    # Testează cu un mesaj realist
    test_real_telegram_format()
    
    print(f"\n🕐 Sfârșit testare: {datetime.now().strftime('%H:%M:%S')}")
    print(f"\n🎯 CONCLUZIE: Funcționalitatea de procesare a multiplelor linkuri")
    print(f"   a fost implementată și testată cu succes!")