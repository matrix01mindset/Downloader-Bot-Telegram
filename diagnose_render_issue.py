#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnosticare pentru probleme Render deployment
"""

import sys
import os
import traceback
import logging
from datetime import datetime

# Configurare logging pentru diagnosticare
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def diagnose_environment():
    """Diagnostichează mediul de rulare"""
    logger.info("🔍 DIAGNOSTICARE MEDIU RENDER")
    logger.info("=" * 50)
    
    # Verifică Python version
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    
    # Verifică variabile de mediu importante
    env_vars = [
        'RENDER', 'FLASK_ENV', 'PORT', 'WEBHOOK_URL', 
        'TELEGRAM_BOT_TOKEN', 'PYTHONPATH'
    ]
    
    logger.info("\n📋 VARIABILE DE MEDIU:")
    for var in env_vars:
        value = os.getenv(var)
        if var == 'TELEGRAM_BOT_TOKEN' and value:
            logger.info(f"{var}: {'*' * 20} (SET)")
        else:
            logger.info(f"{var}: {value}")
    
    # Verifică directorul curent
    logger.info(f"\n📁 Director curent: {os.getcwd()}")
    logger.info(f"📁 Conținut director:")
    try:
        files = os.listdir('.')
        for file in sorted(files)[:20]:  # Primele 20 fișiere
            logger.info(f"  - {file}")
        if len(files) > 20:
            logger.info(f"  ... și încă {len(files) - 20} fișiere")
    except Exception as e:
        logger.error(f"Eroare la listarea fișierelor: {e}")

def test_imports():
    """Testează importurile critice"""
    logger.info("\n🧪 TESTARE IMPORTURI:")
    
    critical_modules = [
        'flask', 'telegram', 'yt_dlp', 'requests', 
        'anti_bot_detection', 'production_config', 
        'render_optimized_config', 'downloader'
    ]
    
    for module in critical_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module}: OK")
        except ImportError as e:
            logger.error(f"❌ {module}: EROARE - {e}")
        except Exception as e:
            logger.error(f"⚠️ {module}: EROARE NEAȘTEPTATĂ - {e}")

def test_app_initialization():
    """Testează inițializarea aplicației"""
    logger.info("\n🚀 TESTARE INIȚIALIZARE APP:")
    
    try:
        # Testează importul app
        logger.info("Importare app...")
        import app
        logger.info("✅ App importat cu succes")
        
        # Verifică dacă Flask app este inițializat
        if hasattr(app, 'app'):
            logger.info("✅ Flask app găsit")
            logger.info(f"Flask app name: {app.app.name}")
        else:
            logger.warning("⚠️ Flask app nu a fost găsit")
            
    except Exception as e:
        logger.error(f"❌ Eroare la inițializarea app: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def check_render_specific_issues():
    """Verifică probleme specifice Render"""
    logger.info("\n🔧 VERIFICARE PROBLEME RENDER:")
    
    # Verifică dacă rulează pe Render
    is_render = os.getenv('RENDER') is not None
    logger.info(f"Rulează pe Render: {is_render}")
    
    # Verifică portul
    port = os.getenv('PORT', '10000')
    logger.info(f"Port configurat: {port}")
    
    # Verifică webhook URL
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        logger.info(f"Webhook URL: {webhook_url}")
    else:
        logger.warning("⚠️ WEBHOOK_URL nu este setat")
    
    # Verifică token Telegram
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        logger.info("✅ TELEGRAM_BOT_TOKEN este setat")
    else:
        logger.error("❌ TELEGRAM_BOT_TOKEN nu este setat")

def main():
    """Funcția principală de diagnosticare"""
    try:
        logger.info(f"🕐 Început diagnosticare: {datetime.now()}")
        
        diagnose_environment()
        test_imports()
        test_app_initialization()
        check_render_specific_issues()
        
        logger.info("\n✅ DIAGNOSTICARE COMPLETĂ")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ EROARE CRITICĂ ÎN DIAGNOSTICARE: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()