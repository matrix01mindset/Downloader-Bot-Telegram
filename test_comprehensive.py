#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test comprehensiv pentru bot - verifică compatibilitatea cu:
- Diacritice românești și internaționale
- Emoticoane și caractere speciale
- Descrieri foarte lungi
- Toate platformele suportate
"""

import os
import sys
import json
import time
import requests
from urllib.parse import quote

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
            
            # Verificări
            if len(caption) > 1024:
                print(f"⚠️  Caption prea lung: {len(caption)} caractere")
            else:
                print(f"✅ Caption generat cu succes: {len(caption)} caractere")
                success_count += 1
                
            # Afișează primele 200 de caractere pentru verificare
            print(f"📄 Preview: {caption[:200]}...")
            
        except Exception as e:
            print(f"❌ Eroare la generarea caption-ului: {e}")
    
    print(f"\n📊 Rezultate teste caption: {success_count}/{total_tests} reușite")
    return success_count == total_tests

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
        "encoding_compatibility": test_encoding_compatibility(),
        "local_webhook": test_local_webhook()
    }
    
    print("\n" + "=" * 60)
    print("📋 REZULTATE FINALE:")
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ TRECUT" if result else "❌ EȘUAT"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 TOATE TESTELE AU TRECUT! Bot-ul este compatibil cu toate tipurile de caractere.")
    else:
        print("\n⚠️  UNELE TESTE AU EȘUAT! Verifică erorile de mai sus.")
    
    return all_passed

if __name__ == "__main__":
    main()