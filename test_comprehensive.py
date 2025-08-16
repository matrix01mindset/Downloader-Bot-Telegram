#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test comprehensiv pentru bot - verifică compatibilitatea cu:
- Diacritice românești și internaționale
- Emoticoane și caractere speciale
- Descrieri foarte lungi
- Toate platformele suportate
- Error handling și retry logic
- Rate limiting și webhook performance
"""

import os
import sys
import json
import time
import requests
import threading
import tempfile
from urllib.parse import quote
from unittest.mock import Mock, patch

# Test data cu diverse caractere și lungimi
TEST_CASES = {
    "diacritice_romanesti": {
        "title": "Videoclip cu ăîâșț ĂÎÂȘȚ și caractere speciale",
        "description": "Descriere cu diacritice: ăîâșț, ĂÎÂȘȚ, și alte caractere speciale: àáâãäåæçèéêë",
        "uploader": "Creatorul cu ăîâșț"
    },
    "emoticoane_unicode": {
        "title": "Video cu emoticoane 😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😤😠😡🤬🤯😳🥵🥶😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪😵🤐🥴🤢🤮🤧😷🤒🤕🤑🤠😈👿👹👺🤡💩👻💀☠️👽👾🤖🎃😺😸😹😻😼😽🙀😿😾",
        "description": "Descriere plină de emoticoane și simboluri: 🎬🎥📹📽️🎞️📺📻🎵🎶🎼🎹🥁🎷🎺🎸🪕🎻🎤🎧🎚️🎛️🎙️📢📣📯🔔🔕🎺🎷🎸🪕🎻🎤🎧🎚️🎛️🎙️📢📣📯🔔🔕",
        "uploader": "Creator 🎬 cu emoticoane 😊"
    },
    "caractere_internationale": {
        "title": "Видео с русскими буквами и 中文字符 و العربية",
        "description": "Описание на русском языке с китайскими 中文字符 и арабскими العربية символами, включая японские ひらがな カタカナ и корейские 한글",
        "uploader": "Международный создатель 🌍"
    },
    "descriere_foarte_lunga": {
        "title": "Video cu descriere extrem de lungă pentru testare",
        "description": "Aceasta este o descriere extrem de lungă care conține foarte multe cuvinte și fraze pentru a testa limitele sistemului de caption-uri. " * 50 + "Această descriere conține diacritice românești: ăîâșț, emoticoane 😀😃😄, caractere internaționale: русский, 中文, العربية, și multe alte elemente pentru a verifica că sistemul poate gestiona corect toate tipurile de conținut. " * 20,
        "uploader": "Creator cu nume foarte lung și diacritice ăîâșț și emoticoane 😊🎬"
    },
    "caractere_speciale_html": {
        "title": "Video cu caractere HTML & XML: <tag> \"quotes\" 'apostrophe' & ampersand",
        "description": "Descriere cu caractere speciale HTML/XML: <script>alert('test')</script>, &lt;tag&gt;, \"double quotes\", 'single quotes', & ampersand, % percent, # hash, @ at, $ dollar, ^ caret, * asterisk, ( ) parentheses, [ ] brackets, { } braces",
        "uploader": "Creator <special> & \"quoted\""
    }
}

def test_caption_function():
    """Testează funcția create_safe_caption cu diverse input-uri"""
    print("🧪 Testez funcția create_safe_caption...")
    
    # Import funcția din app.py
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from app import create_safe_caption
    except ImportError as e:
        print(f"❌ Eroare la importul funcției: {e}")
        return False
    
    success_count = 0
    total_tests = len(TEST_CASES)
    
    for test_name, test_data in TEST_CASES.items():
        print(f"\n📝 Test: {test_name}")
        try:
            caption = create_safe_caption(
                title=test_data["title"],
                uploader=test_data["uploader"],
                description=test_data["description"],
                duration=120,  # 2 minute
                file_size=50*1024*1024  # 50MB
            )
            
            # Verificări îmbunătățite
            caption_bytes = len(caption.encode('utf-8'))
            if caption_bytes > 1000:  # Buffer de siguranță
                print(f"⚠️  Caption prea lung: {caption_bytes} bytes")
            else:
                print(f"✅ Caption generat cu succes: {caption_bytes} bytes, {len(caption)} caractere")
                success_count += 1
                
            # Verifică că HTML este valid
            if '<b>' in caption and '</b>' not in caption:
                print(f"⚠️  HTML invalid în caption")
            elif caption.count('<b>') != caption.count('</b>'):
                print(f"⚠️  Tag-uri HTML nebalansate")
            else:
                print(f"✅ HTML valid în caption")
                
            # Afișează primele 200 de caractere pentru verificare
            print(f"📄 Preview: {caption[:200]}...")
            
        except Exception as e:
            print(f"❌ Eroare la generarea caption-ului: {e}")
    
    print(f"\n📊 Rezultate teste caption: {success_count}/{total_tests} reușite")
    return success_count == total_tests

def test_error_handler():
    """Testează funcționalitatea ErrorHandler"""
    print("\n🔧 Testez ErrorHandler...")
    
    try:
        from app import ErrorHandler
    except ImportError as e:
        print(f"❌ Eroare la importul ErrorHandler: {e}")
        return False
    
    # Test cases pentru clasificarea erorilor
    error_test_cases = [
        ("caption too long", ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG']),
        ("chat not found", ErrorHandler.ERROR_TYPES['CHAT_INACCESSIBLE']),
        ("private video", ErrorHandler.ERROR_TYPES['PRIVATE_VIDEO']),
        ("file too large", ErrorHandler.ERROR_TYPES['FILE_TOO_LARGE']),
        ("cannot parse data", ErrorHandler.ERROR_TYPES['PARSING_ERROR']),
        ("connection timeout", ErrorHandler.ERROR_TYPES['NETWORK_ERROR']),
        ("rate limit exceeded", ErrorHandler.ERROR_TYPES['PLATFORM_ERROR']),
        ("unknown error message", ErrorHandler.ERROR_TYPES['UNKNOWN_ERROR'])
    ]
    
    success_count = 0
    for error_msg, expected_type in error_test_cases:
        try:
            classified_type = ErrorHandler.classify_error(error_msg, "test")
            if classified_type == expected_type:
                print(f"✅ Eroare clasificată corect: '{error_msg}' -> {expected_type}")
                success_count += 1
            else:
                print(f"❌ Eroare clasificată incorect: '{error_msg}' -> {classified_type} (așteptat: {expected_type})")
        except Exception as e:
            print(f"❌ Excepție la clasificarea erorii '{error_msg}': {e}")
    
    # Test retry logic
    retry_tests = [
        (ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG'], 0, True),
        (ErrorHandler.ERROR_TYPES['NETWORK_ERROR'], 1, True),
        (ErrorHandler.ERROR_TYPES['PRIVATE_VIDEO'], 0, False),
        (ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG'], 3, False),
    ]
    
    for error_type, attempt, should_retry in retry_tests:
        try:
            result = ErrorHandler.should_retry(error_type, attempt)
            if result == should_retry:
                print(f"✅ Retry logic corect pentru {error_type}, attempt {attempt}: {result}")
                success_count += 1
            else:
                print(f"❌ Retry logic incorect pentru {error_type}, attempt {attempt}: {result} (așteptat: {should_retry})")
        except Exception as e:
            print(f"❌ Excepție la testarea retry logic: {e}")
    
    print(f"\n📊 Rezultate teste ErrorHandler: {success_count}/{len(error_test_cases) + len(retry_tests)} reușite")
    return success_count == (len(error_test_cases) + len(retry_tests))

def test_platform_detection():
    """Testează detectarea platformelor și configurațiile specifice"""
    print("\n🌐 Testez detectarea platformelor...")
    
    try:
        from downloader import get_platform_from_url, get_platform_specific_config, is_supported_url
    except ImportError as e:
        print(f"❌ Eroare la importul funcțiilor de platformă: {e}")
        return False
    
    # Test URLs pentru fiecare platformă
    platform_tests = [
        ("https://www.tiktok.com/@user/video/123", "tiktok"),
        ("https://vm.tiktok.com/abc123", "tiktok"),
        ("https://www.instagram.com/p/abc123/", "instagram"),
        ("https://instagr.am/p/abc123/", "instagram"),
        ("https://www.facebook.com/watch?v=123", "facebook"),
        ("https://fb.watch/abc123", "facebook"),
        ("https://twitter.com/user/status/123", "twitter"),
        ("https://x.com/user/status/123", "twitter"),
        ("https://example.com/video", "unknown")
    ]
    
    success_count = 0
    for url, expected_platform in platform_tests:
        try:
            detected_platform = get_platform_from_url(url)
            is_supported = is_supported_url(url)
            
            if detected_platform == expected_platform:
                print(f"✅ Platformă detectată corect: {url} -> {detected_platform}")
                success_count += 1
            else:
                print(f"❌ Platformă detectată incorect: {url} -> {detected_platform} (așteptat: {expected_platform})")
            
            # Testează configurația specifică
            if expected_platform != "unknown":
                config = get_platform_specific_config(detected_platform)
                if 'format' in config and 'http_headers' in config:
                    print(f"✅ Configurație validă pentru {detected_platform}")
                else:
                    print(f"❌ Configurație invalidă pentru {detected_platform}")
                    
        except Exception as e:
            print(f"❌ Excepție la testarea platformei {url}: {e}")
    
    print(f"\n📊 Rezultate teste platforme: {success_count}/{len(platform_tests)} reușite")
    return success_count == len(platform_tests)

def test_rate_limiting():
    """Testează funcționalitatea de rate limiting"""
    print("\n⏱️  Testez rate limiting...")
    
    try:
        from app import is_rate_limited
    except ImportError as e:
        print(f"❌ Eroare la importul funcției de rate limiting: {e}")
        return False
    
    test_chat_id = 12345
    success_count = 0
    
    try:
        # Prima cerere ar trebui să treacă
        if not is_rate_limited(test_chat_id):
            print("✅ Prima cerere a trecut")
            success_count += 1
        else:
            print("❌ Prima cerere a fost blocată")
        
        # A doua cerere imediată ar trebui să fie blocată
        if is_rate_limited(test_chat_id):
            print("✅ A doua cerere imediată a fost blocată")
            success_count += 1
        else:
            print("❌ A doua cerere imediată nu a fost blocată")
        
        # Test cu alt utilizator
        test_chat_id_2 = 67890
        if not is_rate_limited(test_chat_id_2):
            print("✅ Alt utilizator poate face cereri")
            success_count += 1
        else:
            print("❌ Alt utilizator a fost blocat incorect")
            
    except Exception as e:
        print(f"❌ Excepție la testarea rate limiting: {e}")
    
    print(f"\n📊 Rezultate teste rate limiting: {success_count}/3 reușite")
    return success_count == 3

def test_local_webhook():
    """Testează webhook-ul local cu diverse input-uri"""
    print("\n🌐 Testez webhook-ul local...")
    
    base_url = "http://localhost:5000"
    webhook_url = f"{base_url}/webhook"
    
    # Verifică dacă serverul local rulează
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Serverul local nu rulează. Pornește aplicația cu 'python app.py'")
            return False
    except requests.exceptions.RequestException:
        print("❌ Nu pot conecta la serverul local. Pornește aplicația cu 'python app.py'")
        return False
    
    success_count = 0
    total_tests = len(TEST_CASES)
    
    for test_name, test_data in TEST_CASES.items():
        print(f"\n📤 Test webhook: {test_name}")
        
        # Creează payload-ul pentru webhook
        payload = {
            "update_id": int(time.time()),
            "message": {
                "text": f"Test message cu {test_data['title']}",
                "chat": {"id": 123456, "type": "private"},
                "from": {
                    "id": 123456,
                    "first_name": test_data["uploader"],
                    "is_bot": False
                },
                "message_id": int(time.time()),
                "date": int(time.time())
            }
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Webhook răspuns cu succes: {response.json()}")
                success_count += 1
            else:
                print(f"❌ Webhook eroare: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Eroare la testarea webhook-ului: {e}")
        
        # Pauză între teste
        time.sleep(1)
    
    print(f"\n📊 Rezultate teste webhook: {success_count}/{total_tests} reușite")
    return success_count == total_tests

def test_encoding_compatibility():
    """Testează compatibilitatea encoding-ului"""
    print("\n🔤 Testez compatibilitatea encoding-ului...")
    
    test_strings = [
        "Română: ăîâșț ĂÎÂȘȚ",
        "Русский: привет мир",
        "中文: 你好世界",
        "العربية: مرحبا بالعالم",
        "Emoticoane: 😀😃😄😁😆😅😂🤣",
        "Simboluri: ♠♣♥♦♪♫♬",
        "Matematică: ∑∏∫∆∇∂∞",
        "Săgeți: ←↑→↓↔↕↖↗↘↙"
    ]
    
    success_count = 0
    
    for test_string in test_strings:
        try:
            # Test encoding/decoding
            encoded = test_string.encode('utf-8')
            decoded = encoded.decode('utf-8')
            
            # Test JSON serialization
            json_str = json.dumps({"text": test_string}, ensure_ascii=False)
            json_obj = json.loads(json_str)
            
            if test_string == decoded == json_obj["text"]:
                print(f"✅ {test_string[:30]}...")
                success_count += 1
            else:
                print(f"❌ Encoding failed pentru: {test_string[:30]}...")
                
        except Exception as e:
            print(f"❌ Eroare encoding pentru '{test_string[:30]}...': {e}")
    
    print(f"\n📊 Rezultate teste encoding: {success_count}/{len(test_strings)} reușite")
    return success_count == len(test_strings)

def main():
    """Rulează toate testele"""
    print("🚀 Începe testarea comprehensivă a bot-ului...")
    print("=" * 60)
    
    results = {
        "caption_function": test_caption_function(),
        "error_handler": test_error_handler(),
        "platform_detection": test_platform_detection(),
        "rate_limiting": test_rate_limiting(),
        "encoding_compatibility": test_encoding_compatibility(),
        "local_webhook": test_local_webhook()
    }
    
    print("\n" + "=" * 60)
    print("📋 REZULTATE FINALE:")
    
    all_passed = True
    total_tests = len(results)
    passed_tests = 0
    
    for test_name, result in results.items():
        status = "✅ TRECUT" if result else "❌ EȘUAT"
        print(f"  {test_name}: {status}")
        if result:
            passed_tests += 1
        else:
            all_passed = False
    
    print(f"\n📊 SCOR FINAL: {passed_tests}/{total_tests} teste trecute")
    
    if all_passed:
        print("\n🎉 TOATE TESTELE AU TRECUT! Bot-ul este gata pentru deployment pe Render.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TESTE AU EȘUAT! Verifică erorile de mai sus.")
    
    # Recomandări bazate pe rezultate
    if passed_tests >= total_tests * 0.8:  # 80% sau mai mult
        print("\n💡 RECOMANDARE: Bot-ul este în stare bună pentru deployment.")
    elif passed_tests >= total_tests * 0.6:  # 60-80%
        print("\n💡 RECOMANDARE: Bot-ul are probleme minore, dar poate fi deployed cu monitorizare.")
    else:
        print("\n💡 RECOMANDARE: Bot-ul are probleme majore, nu este recomandat deployment-ul.")
    
    return all_passed

if __name__ == "__main__":
    main()