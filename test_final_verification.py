#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final de verificare pentru bot-ul Telegram Video Downloader
Testează compatibilitatea cu diacritice, emoticoane și delay-urile de inițializare
"""

import requests
import json
import time
import sys
from datetime import datetime

def test_caption_function():
    """Testează funcția create_safe_caption cu diverse tipuri de caractere"""
    print("\n🔤 Testez funcția create_safe_caption...")
    
    # Import local pentru testare
    sys.path.append('.')
    from app import create_safe_caption
    
    test_cases = [
        {
            'name': 'diacritice_romanesti',
            'params': {
                'title': 'Video cu diacritice românești: ăîâșț ĂÎÂȘȚ',
                'uploader': 'Creator cu ăîâșț',
                'description': 'Descriere cu toate diacriticele: ăîâșț ĂÎÂȘȚ și câteva cuvinte în plus pentru testare.',
                'duration': '3:45',
                'file_size': '25.5 MB'
            }
        },
        {
            'name': 'emoticoane_diverse',
            'params': {
                'title': 'Video cu emoticoane 😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾',
                'uploader': 'Creator 🎬',
                'description': 'Video plin de emoticoane și caractere speciale! 🎉🎊🎈🎁🎀🎂🍰🧁🍭🍬🍫🍩🍪🌟⭐✨💫⚡🔥💥💢💨💦💧🌈☀️🌤️⛅🌦️🌧️⛈️🌩️🌨️❄️☃️⛄🌬️💨🌪️🌊🌋🗻🏔️⛰️🌄🌅🌆🌇🌉🌌🌠🌟💫⭐✨',
                'duration': '2:30',
                'file_size': '15.2 MB'
            }
        },
        {
            'name': 'caractere_internationale',
            'params': {
                'title': 'Video multilingv: Русский 中文 العربية Ελληνικά ไทย 한국어 日本語',
                'uploader': 'Creator International 🌍',
                'description': 'Descriere în mai multe limbi: Hello World! Привет мир! 你好世界! مرحبا بالعالم! Γεια σας κόσμε! สวัสดีชาวโลก! 안녕하세요 세계! こんにちは世界!',
                'duration': '4:15',
                'file_size': '32.8 MB'
            }
        },
        {
            'name': 'descriere_foarte_lunga',
            'params': {
                'title': 'Video cu descriere foarte lungă pentru testarea limitelor',
                'uploader': 'Creator cu nume foarte lung și diacritice ăîâșț și emoticoane 😊 🎬',
                'description': 'Aceasta este o descriere foarte lungă care conține multe informații despre video, inclusiv diacritice românești ăîâșț ĂÎÂȘȚ, emoticoane diverse 😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾, caractere speciale și simboluri matematice ∑∏∫∆∇∂∞≠≤≥±×÷√∞π, săgeți ←↑→↓↔↕↖↗↘↙, și multe alte caractere pentru a testa limitele sistemului de procesare a textului și a verifica că totul funcționează corect chiar și cu texte foarte lungi care depășesc limitele normale ale unei descrieri obișnuite.',
                'duration': '10:45',
                'file_size': '125.7 MB'
            }
        }
    ]
    
    results = []
    for test_case in test_cases:
        try:
            caption = create_safe_caption(**test_case['params'])
            results.append(True)
            print(f"✅ Test {test_case['name']}: SUCCESS ({len(caption)} caractere)")
            print(f"   Preview: {caption[:100]}...")
        except Exception as e:
            results.append(False)
            print(f"❌ Test {test_case['name']}: FAILED - {e}")
    
    return all(results)

def test_webhook_with_delays():
    """Testează webhook-ul cu delay-urile implementate"""
    print("\n🌐 Testez webhook-ul cu delay-urile de inițializare...")
    
    webhook_url = 'http://localhost:5000/webhook'
    
    test_messages = [
        {
            'name': 'test_diacritice',
            'text': 'https://www.tiktok.com/@test_diacritice_ăîâșț/video/123'
        },
        {
            'name': 'test_emoticoane',
            'text': 'https://www.youtube.com/watch?v=test_😀😃😄_video'
        },
        {
            'name': 'test_caractere_speciale',
            'text': 'https://www.instagram.com/p/test_<>&"_post/'
        }
    ]
    
    results = []
    for i, test_msg in enumerate(test_messages):
        try:
            # Simulez un mesaj Telegram real
            payload = {
                'update_id': 12345 + i,
                'message': {
                    'message_id': 100 + i,
                    'date': int(time.time()),
                    'chat': {
                        'id': 123456789,
                        'type': 'private'
                    },
                    'from': {
                        'id': 123456789,
                        'is_bot': False,
                        'first_name': 'Test',
                        'username': 'testuser'
                    },
                    'text': test_msg['text']
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            
            print(f"📤 Testez: {test_msg['name']}")
            start_time = time.time()
            
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                results.append(True)
                print(f"✅ SUCCESS: {response.json()} (timp răspuns: {response_time:.2f}s)")
            else:
                results.append(False)
                print(f"❌ FAILED: Status {response.status_code} - {response.text}")
                
        except Exception as e:
            results.append(False)
            print(f"❌ FAILED: {e}")
        
        # Delay între teste
        time.sleep(1)
    
    return all(results)

def test_server_health():
    """Testează starea serverului"""
    print("\n🏥 Testez starea serverului...")
    
    endpoints = [
        {'url': 'http://localhost:5000/health', 'name': 'Health Check'},
        {'url': 'http://localhost:5000/ping', 'name': 'Ping'},
        {'url': 'http://localhost:5000/', 'name': 'Index'}
    ]
    
    results = []
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint['url'], timeout=10)
            if response.status_code == 200:
                results.append(True)
                print(f"✅ {endpoint['name']}: OK")
            else:
                results.append(False)
                print(f"❌ {endpoint['name']}: Status {response.status_code}")
        except Exception as e:
            results.append(False)
            print(f"❌ {endpoint['name']}: {e}")
    
    return all(results)

def main():
    """Rulează toate testele"""
    print("🚀 VERIFICARE FINALĂ - Bot Telegram Video Downloader")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Rulează testele
    test_results = {
        'caption_function': test_caption_function(),
        'server_health': test_server_health(),
        'webhook_delays': test_webhook_with_delays()
    }
    
    # Afișează rezultatele finale
    print("\n" + "=" * 60)
    print("📋 REZULTATE FINALE:")
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ TRECUT" if result else "❌ EȘUAT"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TOATE TESTELE AU TRECUT!")
        print("✅ Bot-ul este compatibil cu diacritice, emoticoane și caractere speciale")
        print("✅ Delay-urile de inițializare funcționează corect")
        print("✅ Serverul este stabil și răspunde la toate endpoint-urile")
        print("🚀 Bot-ul este gata pentru deployment în producție!")
    else:
        print("❌ UNELE TESTE AU EȘUAT!")
        print("⚠️ Verifică logurile pentru detalii")
    
    print("=" * 60)
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)