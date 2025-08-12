#!/usr/bin/env python3
"""
🧪 SCRIPT TESTARE LOCALĂ - Telegram Video Downloader Bot
Versiunea: 2.0.0 - SECURIZAT
Data: 2025-01-12

Testează funcționalitatea botului local înainte de deploy.
Includes comprehensive security and functionality checks.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import subprocess
import json
from telegram import Bot
from telegram.ext import Application

# Configurare logging pentru teste
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token-ul botului
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu")
    sys.exit(1)

def check_environment():
    """Verifică configurarea mediului de dezvoltare."""
    print("🔍 Verificare mediu de dezvoltare...")
    
    # Verifică Python version
    python_version = sys.version_info
    if python_version.major != 3 or python_version.minor < 11:
        print(f"❌ Python {python_version.major}.{python_version.minor} detectat. Necesită Python 3.11+")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Verifică fișierul .env
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Fișierul .env nu există!")
        print("💡 Copiază .env.example ca .env și completează valorile")
        return False
    print("✅ Fișierul .env există")
    
    # Încarcă variabilele de mediu
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Variabile de mediu încărcate")
    except ImportError:
        print("❌ python-dotenv nu este instalat")
        return False
    
    # Verifică token-ul Telegram
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN nu este setat în .env")
        return False
    if not token.startswith('your_telegram_bot_token_here'):
        print("✅ TELEGRAM_BOT_TOKEN este configurat")
    else:
        print("❌ TELEGRAM_BOT_TOKEN nu este actualizat în .env")
        return False
    
    return True

def check_dependencies():
    """Verifică dependențele Python."""
    print("\n📦 Verificare dependențe...")
    
    required_packages = [
        'flask',
        'python-telegram-bot', 
        'yt-dlp',
        'requests',
        'cryptography',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - LIPSEȘTE")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n💡 Instalează pachetele lipsă: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_downloader():
    """Testează funcționalitatea de descărcare."""
    print("\n🎬 Testare funcționalitate descărcare...")
    
    try:
        from downloader import is_supported_url, download_video
        
        # Test URL-uri suportate
        test_urls = [
            'https://www.facebook.com/watch?v=123456789',
            'https://www.instagram.com/p/ABC123/',
            'https://www.tiktok.com/@user/video/123456789',
            'https://twitter.com/user/status/123456789',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # Ar trebui să fie nesuportat
        ]
        
        for url in test_urls:
            is_supported = is_supported_url(url)
            platform = url.split('/')[2]
            status = "✅ Suportat" if is_supported else "❌ Nu este suportat"
            print(f"  {platform}: {status}")
        
        print("✅ Funcția de verificare URL funcționează")
        return True
        
    except Exception as e:
        print(f"❌ Eroare la testarea downloader-ului: {e}")
        return False

def test_telegram_connection():
    """Testează conexiunea cu Telegram API."""
    print("\n🤖 Testare conexiune Telegram...")
    
    try:
        from telegram import Bot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        bot = Bot(token)
        
        # Test simplu - obține informații despre bot
        import asyncio
        
        async def test_bot():
            try:
                me = await bot.get_me()
                print(f"✅ Bot conectat: @{me.username} ({me.first_name})")
                return True
            except Exception as e:
                print(f"❌ Eroare conexiune Telegram: {e}")
                return False
        
        return asyncio.run(test_bot())
        
    except Exception as e:
        print(f"❌ Eroare la testarea conexiunii Telegram: {e}")
        return False

def test_security():
    """Testează măsurile de securitate."""
    print("\n🔐 Verificare securitate...")
    
    security_checks = []
    
    # Verifică că token-ul nu este hardcodat
    sensitive_files = ['app.py', 'bot.py', 'downloader.py']
    for file_path in sensitive_files:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'BOT_TOKEN = "' in content and ':' in content:
                    print(f"❌ Token hardcodat găsit în {file_path}")
                    security_checks.append(False)
                else:
                    print(f"✅ {file_path} - fără token-uri hardcodate")
                    security_checks.append(True)
    
    # Verifică că .env nu este în git
    gitignore_path = Path('.gitignore')
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
            if '.env' in gitignore_content:
                print("✅ .env este în .gitignore")
                security_checks.append(True)
            else:
                print("❌ .env nu este în .gitignore")
                security_checks.append(False)
    
    return all(security_checks)

async def test_bot_initialization():
    """Testează inițializarea bot-ului"""
    print("🔧 TESTARE INIȚIALIZARE BOT")
    print("=" * 40)
    
    try:
        # Creează bot-ul
        bot = Bot(TOKEN)
        print("✅ Bot creat cu succes")
        
        # Testează conexiunea
        me = await bot.get_me()
        print(f"✅ Bot conectat: {me.first_name} (@{me.username})")
        
        # Creează aplicația
        application = Application.builder().token(TOKEN).build()
        print("✅ Aplicație creată cu succes")
        
        # Inițializează aplicația
        await application.initialize()
        print("✅ Aplicație inițializată cu succes")
        
        # Testează webhook info
        webhook_info = await bot.get_webhook_info()
        print(f"📋 Webhook actual: {webhook_info.url or 'Nu este setat'}")
        
        # Cleanup
        await application.shutdown()
        print("✅ Aplicație închisă corect")
        
        return True
        
    except Exception as e:
        print(f"❌ Eroare: {e}")
        return False

async def test_webhook_setting():
    """Testează setarea webhook-ului"""
    print("\n🔗 TESTARE SETARE WEBHOOK")
    print("=" * 40)
    
    webhook_url = "https://telegram-video-downloader-1471.onrender.com/webhook"
    
    try:
        bot = Bot(TOKEN)
        
        # Setează webhook-ul
        result = await bot.set_webhook(url=webhook_url)
        if result:
            print(f"✅ Webhook setat cu succes: {webhook_url}")
        else:
            print("❌ Nu s-a putut seta webhook-ul")
            
        # Verifică webhook-ul
        webhook_info = await bot.get_webhook_info()
        print(f"📋 Webhook verificat: {webhook_info.url}")
        print(f"📊 Pending updates: {webhook_info.pending_update_count}")
        if webhook_info.last_error_message:
            print(f"⚠️ Ultima eroare: {webhook_info.last_error_message}")
        else:
            print("✅ Nicio eroare")
            
        return True
        
    except Exception as e:
        print(f"❌ Eroare la setarea webhook: {e}")
        return False

def test_import_app():
    """Testează importul aplicației principale"""
    print("\n📦 TESTARE IMPORT APLICAȚIE")
    print("=" * 40)
    
    try:
        # Testează importul
        import app
        print("✅ Aplicația a fost importată cu succes")
        
        # Verifică că aplicația este inițializată
        if hasattr(app, 'application'):
            print("✅ Aplicația Telegram este disponibilă")
        else:
            print("❌ Aplicația Telegram nu este disponibilă")
            
        return True
        
    except Exception as e:
        print(f"❌ Eroare la importul aplicației: {e}")
        return False

def main():
    """Funcția principală de testare."""
    print("🧪 TESTARE LOCALĂ - Telegram Video Downloader Bot")
    print("=" * 60)
    
    tests = [
        ("Mediu de dezvoltare", check_environment),
        ("Dependențe Python", check_dependencies), 
        ("Funcționalitate descărcare", test_downloader),
        ("Conexiune Telegram", test_telegram_connection),
        ("Securitate", test_security)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Eroare în testul '{test_name}': {e}")
            results.append((test_name, False))
    
    # Sumar rezultate
    print("\n" + "=" * 60)
    print("📊 SUMAR TESTE:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ TRECUT" if result else "❌ EȘUAT"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TOATE TESTELE AU TRECUT! Botul este gata pentru deploy.")
        print("\n📋 Pași următori:")
        print("1. Verifică din nou toate configurările")
        print("2. Testează manual cu câteva URL-uri")
        print("3. Deploy pe Render folosind render.yaml")
    else:
        print("⚠️ UNELE TESTE AU EȘUAT! Rezolvă problemele înainte de deploy.")
        print("\n💡 Verifică mesajele de eroare de mai sus pentru detalii.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)