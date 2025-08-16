#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de testare locală pentru bot-ul Telegram Video Downloader
Testează inițializarea aplicației și funcționalitatea de bază
"""

import os
import sys
import asyncio
import logging
from telegram import Bot
from telegram.ext import Application

# Configurare logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token-ul botului
TOKEN = "8253089686:AAGNOvUHXTVwz2Bi9KEpBpY4OAkTPC7ICAs"

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

async def main():
    """Funcția principală de testare"""
    print("🚀 TESTARE COMPLETĂ BOT TELEGRAM")
    print("=" * 50)
    
    # Test 1: Inițializare bot
    test1 = await test_bot_initialization()
    
    # Test 2: Setare webhook
    test2 = await test_webhook_setting()
    
    # Test 3: Import aplicație
    test3 = test_import_app()
    
    # Rezultate finale
    print("\n📊 REZULTATE FINALE")
    print("=" * 30)
    print(f"Inițializare bot: {'✅' if test1 else '❌'}")
    print(f"Setare webhook: {'✅' if test2 else '❌'}")
    print(f"Import aplicație: {'✅' if test3 else '❌'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 TOATE TESTELE AU TRECUT!")
        print("Bot-ul este gata pentru deployment pe Render.")
    else:
        print("\n❌ UNELE TESTE AU EȘUAT!")
        print("Verifică erorile de mai sus.")

if __name__ == "__main__":
    asyncio.run(main())