#!/usr/bin/env python3
"""
Script de testare pentru funcționalitatea de descărcare
Rulează acest script pentru a testa dacă yt-dlp funcționează corect
"""

import os
import sys
from downloader import download_video, is_supported_url

def test_url_validation():
    """
    Testează validarea URL-urilor
    """
    print("🔍 Testez validarea URL-urilor...")
    
    test_urls = [
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://tiktok.com/@user/video/123", True),
        ("https://instagram.com/p/ABC123", True),
        ("https://facebook.com/watch?v=123", True),
        ("https://twitter.com/user/status/123", True),
        ("https://example.com/video", False),
        ("https://google.com", False),
    ]
    
    for url, expected in test_urls:
        result = is_supported_url(url)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {url} -> {result}")
    
    print()

def test_download():
    """
    Testează descărcarea unui video scurt de pe YouTube
    """
    print("📥 Testez descărcarea...")
    
    # URL de test - video scurt și public
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - primul video YouTube
    
    try:
        print(f"  Încerc să descarc: {test_url}")
        filepath = download_video(test_url)
        
        if filepath and os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"  ✅ Descărcare reușită!")
            print(f"  📁 Fișier: {filepath}")
            print(f"  📊 Mărime: {file_size / 1024 / 1024:.2f} MB")
            
            # Șterge fișierul de test
            try:
                os.remove(filepath)
                print(f"  🗑️ Fișier de test șters")
            except:
                print(f"  ⚠️ Nu s-a putut șterge fișierul de test")
        else:
            print(f"  ❌ Descărcarea a eșuat - fișierul nu există")
            
    except Exception as e:
        print(f"  ❌ Eroare la descărcare: {e}")
    
    print()

def check_dependencies():
    """
    Verifică dacă toate dependențele sunt instalate
    """
    print("📦 Verific dependențele...")
    
    dependencies = [
        "yt_dlp",
        "telegram",
        "flask",
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} - LIPSEȘTE!")
            print(f"     Instalează cu: pip install {dep}")
    
    print()

def check_environment():
    """
    Verifică variabilele de mediu
    """
    print("🔧 Verific variabilele de mediu...")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        # Ascunde majoritatea token-ului pentru securitate
        masked_token = token[:10] + "..." + token[-10:] if len(token) > 20 else "***"
        print(f"  ✅ TELEGRAM_BOT_TOKEN: {masked_token}")
    else:
        print(f"  ⚠️ TELEGRAM_BOT_TOKEN nu este setat")
        print(f"     Setează cu: set TELEGRAM_BOT_TOKEN=your_token (Windows)")
        print(f"     Sau: export TELEGRAM_BOT_TOKEN=your_token (Linux/Mac)")
    
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        print(f"  ✅ WEBHOOK_URL: {webhook_url}")
    else:
        print(f"  ℹ️ WEBHOOK_URL nu este setat (opțional pentru rulare locală)")
    
    print()

def main():
    """
    Rulează toate testele
    """
    print("🧪 TESTARE TELEGRAM VIDEO DOWNLOADER BOT")
    print("=" * 50)
    print()
    
    check_dependencies()
    check_environment()
    test_url_validation()
    
    # Întreabă utilizatorul dacă vrea să testeze descărcarea
    response = input("🤔 Vrei să testez descărcarea unui video? (y/n): ").lower().strip()
    if response in ['y', 'yes', 'da']:
        test_download()
    else:
        print("⏭️ Testul de descărcare a fost omis.")
        print()
    
    print("✅ Testare completă!")
    print()
    print("📝 Pași următori:")
    print("  1. Setează TELEGRAM_BOT_TOKEN dacă nu este setat")
    print("  2. Rulează 'python bot.py' pentru testare locală")
    print("  3. Sau deploy pe Render/Railway pentru hosting gratuit")
    print("  4. Setează webhook cu /set_webhook după deployment")

if __name__ == "__main__":
    main()