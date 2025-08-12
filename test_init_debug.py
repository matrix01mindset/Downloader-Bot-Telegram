#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pentru debugging inițializarea aplicației Telegram
"""

import os
import asyncio
import logging
from telegram import Bot
from telegram.ext import Application

# Configurare logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token bot - încărcat din variabile de mediu pentru securitate
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ EROARE: TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu!")
    print("Setează variabila de mediu sau creează un fișier .env")
    exit(1)

def test_initialization_methods():
    """Testează diferite metode de inițializare"""
    print("🔧 TESTARE METODE DE INIȚIALIZARE")
    print("=" * 50)
    
    # Metoda 1: Inițializare simplă
    print("\n1️⃣ Testez inițializarea simplă...")
    try:
        bot = Bot(TOKEN)
        application = Application.builder().token(TOKEN).build()
        
        # Verifică starea înainte de inițializare
        print(f"   Stare înainte: {hasattr(application, '_initialized')}")
        
        # Inițializare
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.initialize())
            print("   ✅ Inițializare reușită")
            
            # Verifică starea după inițializare
            print(f"   Stare după: {hasattr(application, '_initialized')}")
            
            # Test procesare update
            from telegram import Update
            test_update_data = {
                'update_id': 123,
                'message': {
                    'message_id': 1,
                    'date': 1234567890,
                    'chat': {'id': 123, 'type': 'private'},
                    'from': {'id': 123, 'is_bot': False, 'first_name': 'Test'},
                    'text': '/start'
                }
            }
            
            update = Update.de_json(test_update_data, bot)
            loop.run_until_complete(application.process_update(update))
            print("   ✅ Procesare update reușită")
            
        except Exception as e:
            print(f"   ❌ Eroare: {e}")
        finally:
            loop.close()
            
    except Exception as e:
        print(f"   ❌ Eroare la inițializare: {e}")
    
    # Metoda 2: Cu handler-e
    print("\n2️⃣ Testez cu handler-e adăugate...")
    try:
        bot = Bot(TOKEN)
        application = Application.builder().token(TOKEN).build()
        
        # Adaugă un handler simplu
        from telegram.ext import CommandHandler
        
        async def test_start(update, context):
            await update.message.reply_text("Test OK")
        
        application.add_handler(CommandHandler("start", test_start))
        print("   Handler adăugat")
        
        # Inițializare
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.initialize())
            print("   ✅ Inițializare cu handler reușită")
            
            # Test procesare
            test_update_data = {
                'update_id': 124,
                'message': {
                    'message_id': 2,
                    'date': 1234567890,
                    'chat': {'id': 123, 'type': 'private'},
                    'from': {'id': 123, 'is_bot': False, 'first_name': 'Test'},
                    'text': '/start'
                }
            }
            
            update = Update.de_json(test_update_data, bot)
            loop.run_until_complete(application.process_update(update))
            print("   ✅ Procesare cu handler reușită")
            
        except Exception as e:
            print(f"   ❌ Eroare: {e}")
        finally:
            loop.close()
            
    except Exception as e:
        print(f"   ❌ Eroare la testul cu handler: {e}")
    
    # Metoda 3: Simulare app.py
    print("\n3️⃣ Testez simularea app.py...")
    try:
        # Simulează exact ce face app.py
        bot = Bot(TOKEN)
        application = Application.builder().token(TOKEN).build()
        
        # Variabilă globală
        _application_initialized = False
        
        def ensure_application_initialized():
            global _application_initialized
            if not _application_initialized:
                try:
                    # Verifică dacă există deja un event loop
                    try:
                        current_loop = asyncio.get_running_loop()
                        # Dacă există un loop care rulează, folosim thread separat
                        import threading
                        import concurrent.futures
                        
                        def init_in_thread():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(application.initialize())
                                return True
                            finally:
                                loop.close()
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(init_in_thread)
                            future.result(timeout=30)
                            
                    except RuntimeError:
                        # Nu există loop care rulează
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(application.initialize())
                        finally:
                            loop.close()
                    
                    _application_initialized = True
                    print("   ✅ Aplicația a fost inițializată cu succes")
                    
                except Exception as e:
                    print(f"   ❌ Eroare la inițializarea aplicației: {e}")
        
        # Adaugă handler
        async def test_start(update, context):
            await update.message.reply_text("Test OK din simulare")
        
        # Inițializează înainte de handler
        ensure_application_initialized()
        application.add_handler(CommandHandler("start", test_start))
        
        # Test webhook
        test_update_data = {
            'update_id': 125,
            'message': {
                'message_id': 3,
                'date': 1234567890,
                'chat': {'id': 123, 'type': 'private'},
                'from': {'id': 123, 'is_bot': False, 'first_name': 'Test'},
                'text': '/start'
            }
        }
        
        update = Update.de_json(test_update_data, bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.process_update(update))
            print("   ✅ Simulare app.py reușită")
        finally:
            loop.close()
            
    except Exception as e:
        print(f"   ❌ Eroare la simularea app.py: {e}")
    
    print("\n🎉 TESTARE COMPLETĂ")

if __name__ == "__main__":
    test_initialization_methods()