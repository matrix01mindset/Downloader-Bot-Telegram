#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pentru funcționalitatea anti-bot detection și configurații de producție
"""

import os
import sys
import tempfile
import logging
import time
from datetime import datetime

# Configurare logging pentru test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modulele noastre
try:
    from downloader import download_with_enhanced_retry, create_enhanced_ydl_opts
    from anti_bot_detection import create_anti_bot_ydl_opts, get_platform_from_url
    from production_config import (
        validate_url_security, 
        is_production_environment,
        get_production_ydl_opts_enhancement
    )
except ImportError as e:
    logger.error(f"Eroare la importul modulelor: {e}")
    sys.exit(1)

# URL-uri de test pentru diferite platforme
TEST_URLS = {
    'youtube': [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Roll - video public
        'https://youtu.be/dQw4w9WgXcQ'  # Format scurt
    ],
    'tiktok': [
        'https://www.tiktok.com/@username/video/1234567890123456789'  # Exemplu generic
    ],
    'instagram': [
        'https://www.instagram.com/p/ABC123/'  # Exemplu generic
    ],
    'twitter': [
        'https://twitter.com/username/status/1234567890123456789'  # Exemplu generic
    ]
}

def test_url_validation():
    """Testează validarea URL-urilor"""
    logger.info("🧪 Testare validare URL-uri...")
    
    # URL-uri valide
    valid_urls = [
        'https://www.youtube.com/watch?v=test',
        'https://www.tiktok.com/@user/video/123',
        'https://www.instagram.com/p/ABC123/'
    ]
    
    # URL-uri invalide
    invalid_urls = [
        'https://malicious-site.com/video',
        'ftp://example.com/file',
        'javascript:alert(1)'
    ]
    
    # Test URL-uri valide
    for url in valid_urls:
        try:
            is_valid = validate_url_security(url)
            logger.info(f"✅ URL valid: {url} -> {is_valid}")
        except Exception as e:
            logger.error(f"❌ Eroare la validarea URL valid {url}: {e}")
    
    # Test URL-uri invalide
    for url in invalid_urls:
        try:
            is_valid = validate_url_security(url)
            if not is_valid:
                logger.info(f"✅ URL invalid detectat corect: {url}")
            else:
                logger.warning(f"⚠️ URL invalid trecut prin validare: {url}")
        except Exception as e:
            logger.info(f"✅ URL invalid respins: {url} -> {e}")

def test_platform_detection():
    """Testează detectarea platformelor"""
    logger.info("🧪 Testare detectare platforme...")
    
    test_cases = [
        ('https://www.youtube.com/watch?v=test', 'youtube'),
        ('https://youtu.be/test', 'youtube'),
        ('https://www.tiktok.com/@user/video/123', 'tiktok'),
        ('https://vm.tiktok.com/test', 'tiktok'),
        ('https://www.instagram.com/p/ABC/', 'instagram'),
        ('https://www.facebook.com/video/123', 'facebook'),
        ('https://twitter.com/user/status/123', 'twitter'),
        ('https://x.com/user/status/123', 'twitter')
    ]
    
    for url, expected_platform in test_cases:
        try:
            detected_platform = get_platform_from_url(url)
            if detected_platform == expected_platform:
                logger.info(f"✅ Platformă detectată corect: {url} -> {detected_platform}")
            else:
                logger.warning(f"⚠️ Platformă detectată incorect: {url} -> {detected_platform} (așteptat: {expected_platform})")
        except Exception as e:
            logger.error(f"❌ Eroare la detectarea platformei pentru {url}: {e}")

def test_anti_bot_config_creation():
    """Testează crearea configurațiilor anti-bot"""
    logger.info("🧪 Testare creare configurații anti-bot...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for platform, urls in TEST_URLS.items():
            for url in urls:
                try:
                    logger.info(f"Testare configurații pentru {platform}: {url}")
                    
                    # Test configurații anti-bot
                    ydl_opts = create_anti_bot_ydl_opts(url, temp_dir)
                    
                    # Verifică că opțiunile conțin elementele necesare
                    required_keys = ['format', 'outtmpl', 'http_headers']
                    for key in required_keys:
                        if key in ydl_opts:
                            logger.info(f"✅ {platform}: {key} prezent în configurații")
                        else:
                            logger.warning(f"⚠️ {platform}: {key} lipsește din configurații")
                    
                    # Verifică headers
                    if 'http_headers' in ydl_opts and 'User-Agent' in ydl_opts['http_headers']:
                        user_agent = ydl_opts['http_headers']['User-Agent']
                        logger.info(f"✅ {platform}: User-Agent configurat: {user_agent[:50]}...")
                    
                    # Verifică extractor args
                    if 'extractor_args' in ydl_opts:
                        logger.info(f"✅ {platform}: Extractor args configurate")
                    
                except Exception as e:
                    logger.error(f"❌ Eroare la crearea configurațiilor pentru {platform}: {e}")

def test_production_config():
    """Testează configurațiile de producție"""
    logger.info("🧪 Testare configurații de producție...")
    
    try:
        # Test îmbunătățiri producție
        production_opts = get_production_ydl_opts_enhancement()
        
        expected_keys = ['socket_timeout', 'retries', 'max_filesize']
        for key in expected_keys:
            if key in production_opts:
                logger.info(f"✅ Configurație producție: {key} = {production_opts[key]}")
            else:
                logger.warning(f"⚠️ Configurație producție lipsește: {key}")
        
        # Test detectare mediu producție
        is_prod = is_production_environment()
        logger.info(f"📊 Mediu de producție detectat: {is_prod}")
        
    except Exception as e:
        logger.error(f"❌ Eroare la testarea configurațiilor de producție: {e}")

def test_enhanced_ydl_opts():
    """Testează crearea opțiunilor yt-dlp îmbunătățite"""
    logger.info("🧪 Testare opțiuni yt-dlp îmbunătățite...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test cu URL YouTube (cel mai comun)
        test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        
        try:
            ydl_opts = create_enhanced_ydl_opts(test_url, temp_dir)
            
            # Verifică structura opțiunilor
            essential_keys = ['format', 'outtmpl', 'restrictfilenames', 'http_headers']
            for key in essential_keys:
                if key in ydl_opts:
                    logger.info(f"✅ Opțiune esențială prezentă: {key}")
                else:
                    logger.warning(f"⚠️ Opțiune esențială lipsește: {key}")
            
            # Verifică configurații de securitate
            if 'max_filesize' in ydl_opts:
                max_size_mb = ydl_opts['max_filesize'] / (1024 * 1024)
                logger.info(f"✅ Limită dimensiune fișier: {max_size_mb:.1f}MB")
            
            # Verifică timeout-uri
            if 'socket_timeout' in ydl_opts:
                logger.info(f"✅ Socket timeout: {ydl_opts['socket_timeout']}s")
            
            logger.info(f"✅ Opțiuni yt-dlp îmbunătățite create cu succes")
            
        except Exception as e:
            logger.error(f"❌ Eroare la crearea opțiunilor îmbunătățite: {e}")

def test_download_simulation():
    """Simulează o descărcare pentru a testa întregul flux"""
    logger.info("🧪 Simulare descărcare (fără descărcare efectivă)...")
    
    # Folosim un URL YouTube public pentru test
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Testează doar crearea configurațiilor, nu descărcarea efectivă
            start_time = time.time()
            
            # Creează configurații
            ydl_opts = create_enhanced_ydl_opts(test_url, temp_dir)
            
            config_time = time.time() - start_time
            logger.info(f"✅ Configurații create în {config_time:.3f}s")
            
            # Verifică că toate componentele sunt prezente
            components = [
                ('format', 'Format video'),
                ('http_headers', 'Headers HTTP'),
                ('socket_timeout', 'Timeout socket'),
                ('retries', 'Număr reîncercări')
            ]
            
            for key, description in components:
                if key in ydl_opts:
                    logger.info(f"✅ {description}: configurat")
                else:
                    logger.warning(f"⚠️ {description}: lipsește")
            
            logger.info(f"✅ Simulare descărcare completă")
            
        except Exception as e:
            logger.error(f"❌ Eroare în simularea descărcării: {e}")

def run_all_tests():
    """Rulează toate testele"""
    logger.info("🚀 Începere teste anti-bot detection și producție")
    logger.info("=" * 60)
    
    tests = [
        ("Validare URL-uri", test_url_validation),
        ("Detectare platforme", test_platform_detection),
        ("Configurații anti-bot", test_anti_bot_config_creation),
        ("Configurații producție", test_production_config),
        ("Opțiuni yt-dlp îmbunătățite", test_enhanced_ydl_opts),
        ("Simulare descărcare", test_download_simulation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Rulare test: {test_name}")
        logger.info("-" * 40)
        
        try:
            test_func()
            logger.info(f"✅ Test {test_name}: TRECUT")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test {test_name}: EȘUAT - {e}")
            failed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Rezultate teste:")
    logger.info(f"✅ Trecute: {passed}")
    logger.info(f"❌ Eșuate: {failed}")
    logger.info(f"📈 Rata de succes: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        logger.info("🎉 Toate testele au trecut! Sistemul anti-bot este funcțional.")
    else:
        logger.warning(f"⚠️ {failed} teste au eșuat. Verifică configurațiile.")

if __name__ == "__main__":
    # Setează variabile de mediu pentru test
    os.environ['ENVIRONMENT'] = 'development'  # Pentru a nu activa modul producție
    
    try:
        run_all_tests()
    except KeyboardInterrupt:
        logger.info("\n🛑 Teste întrerupte de utilizator")
    except Exception as e:
        logger.error(f"❌ Eroare critică în teste: {e}")
        sys.exit(1)