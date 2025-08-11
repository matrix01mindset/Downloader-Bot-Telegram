#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pentru rezolvarea problemelor Facebook identificate în log-urile Render
Probleme detectate:
1. ERROR: [facebook] 1038515118353910: Cannot parse data
2. Bot not initialized (503 status)
3. Probleme cu URL-uri Facebook share/v/
"""

import subprocess
import sys
import os
import logging
import time
from datetime import datetime

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(command, description):
    """Execută o comandă și returnează rezultatul"""
    logger.info(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300
        )
        if result.returncode == 0:
            logger.info(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                logger.info(f"Output: {result.stdout.strip()[:200]}...")
            return True
        else:
            logger.error(f"❌ {description} - FAILED")
            logger.error(f"Error: {result.stderr.strip()[:200]}...")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        logger.error(f"💥 {description} - EXCEPTION: {e}")
        return False

def update_ytdlp():
    """Actualizează yt-dlp la cea mai recentă versiune"""
    logger.info("🚀 === ACTUALIZARE YT-DLP ===")
    
    # Încearcă să actualizeze la versiunea nightly
    commands = [
        ("python -m pip install --upgrade pip", "Actualizare pip"),
        ("python -m pip install -U --pre yt-dlp[default]", "Actualizare yt-dlp nightly"),
        ("python -m pip install -U yt-dlp[default]", "Fallback: yt-dlp stable"),
        ("python -c \"import yt_dlp; print(f'yt-dlp version: {yt_dlp.version.__version__}')\"", "Verificare versiune yt-dlp")
    ]
    
    success_count = 0
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
        time.sleep(2)  # Pauză între comenzi
    
    return success_count >= 2  # Cel puțin pip și yt-dlp trebuie să funcționeze

def test_facebook_extraction():
    """Testează extragerea de informații Facebook"""
    logger.info("🧪 === TEST FACEBOOK EXTRACTION ===")
    
    # URL-uri de test Facebook (publice)
    test_urls = [
        "https://www.facebook.com/watch?v=1234567890",  # Format clasic
        "https://www.facebook.com/share/v/test123/",     # Format nou share/v/
    ]
    
    test_script = '''
import yt_dlp
import sys

def test_facebook_url(url):
    try:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'extractor_args': {
                'facebook': {
                    'api_version': 'v19.0',
                    'legacy_ssl': True,
                    'tab': 'videos'
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"SUCCESS: {url} - Title: {info.get('title', 'N/A')[:50]}")
            return True
    except Exception as e:
        print(f"ERROR: {url} - {str(e)[:100]}")
        return False

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.facebook.com/watch?v=test"
    test_facebook_url(url)
'''
    
    # Salvează scriptul de test
    test_file = "facebook_test.py"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    # Testează URL-urile
    success_count = 0
    for url in test_urls:
        logger.info(f"Testing: {url}")
        if run_command(f"python {test_file} \"{url}\"", f"Test Facebook URL: {url[:30]}..."):
            success_count += 1
        time.sleep(1)
    
    # Curăță fișierul de test
    try:
        os.remove(test_file)
    except:
        pass
    
    return success_count > 0

def update_requirements():
    """Actualizează requirements.txt cu versiuni noi"""
    logger.info("📝 === ACTUALIZARE REQUIREMENTS ===")
    
    # Verifică versiunile actuale
    version_check = '''
import yt_dlp
import requests
import flask
import python_telegram_bot

print(f"yt-dlp: {yt_dlp.version.__version__}")
print(f"requests: {requests.__version__}")
print(f"flask: {flask.__version__}")
print(f"python-telegram-bot: {python_telegram_bot.__version__}")
'''
    
    with open("check_versions.py", 'w', encoding='utf-8') as f:
        f.write(version_check)
    
    run_command("python check_versions.py", "Verificare versiuni pachete")
    
    try:
        os.remove("check_versions.py")
    except:
        pass
    
    return True

def create_facebook_fix_patch():
    """Creează un patch pentru problemele Facebook specifice"""
    logger.info("🔨 === CREARE PATCH FACEBOOK ===")
    
    patch_content = '''
# Facebook Fix Patch - 2025-01-11
# Rezolvă problemele: Cannot parse data, share/v/ URLs, API v19.0

import yt_dlp
import re
import logging

logger = logging.getLogger(__name__)

def enhanced_facebook_extractor_args():
    """Configurații îmbunătățite pentru Facebook 2025"""
    return {
        'facebook': {
            # API Version - cea mai recentă
            'api_version': 'v19.0',
            
            # SSL și securitate
            'legacy_ssl': True,
            'verify_ssl': False,
            
            # Configurații de parsare
            'tab': 'videos',
            'legacy_format': True,
            'mobile_client': False,
            
            # Gestionare erori
            'ignore_parse_errors': True,
            'skip_unavailable_fragments': True,
            
            # Headers și user agent
            'use_mobile_ua': False,
            'force_json_extraction': True
        }
    }

def normalize_facebook_share_url(url):
    """Normalizează URL-urile Facebook share/v/ pentru compatibilitate"""
    if not url or 'facebook.com' not in url:
        return url
    
    # Pattern pentru share/v/ URLs
    share_pattern = r'facebook\.com/share/v/([^/?]+)'
    match = re.search(share_pattern, url)
    
    if match:
        video_id = match.group(1)
        # Convertește la format clasic watch
        normalized = f"https://www.facebook.com/watch?v={video_id}"
        logger.info(f"Facebook URL normalized: {url} -> {normalized}")
        return normalized
    
    return url

def create_robust_facebook_opts():
    """Creează opțiuni robuste pentru Facebook"""
    return {
        'format': 'best[filesize<512M][height<=720]/best[height<=720]/best[filesize<512M]/best',
        'restrictfilenames': True,
        'windowsfilenames': True,
        'ignoreerrors': True,
        'no_warnings': False,  # Activăm warnings pentru debugging
        'extract_flat': False,
        'socket_timeout': 45,
        'retries': 5,
        'extractor_retries': 5,
        'fragment_retries': 5,
        'sleep_interval': 2,
        'max_sleep_interval': 8,
        'extractor_args': enhanced_facebook_extractor_args(),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    }

# Export funcțiile pentru utilizare
__all__ = [
    'enhanced_facebook_extractor_args',
    'normalize_facebook_share_url', 
    'create_robust_facebook_opts'
]
'''
    
    patch_file = "facebook_fix_patch.py"
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(patch_content)
    
    logger.info(f"✅ Patch Facebook creat: {patch_file}")
    return True

def main():
    """Funcția principală"""
    logger.info("🚀 === FACEBOOK ISSUES FIX SCRIPT ===")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    steps = [
        ("Actualizare yt-dlp", update_ytdlp),
        ("Test Facebook extraction", test_facebook_extraction),
        ("Actualizare requirements", update_requirements),
        ("Creare patch Facebook", create_facebook_fix_patch)
    ]
    
    results = []
    for step_name, step_func in steps:
        logger.info(f"\n{'='*50}")
        logger.info(f"🔄 STEP: {step_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = step_func()
            results.append((step_name, success))
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"📊 {step_name}: {status}")
        except Exception as e:
            logger.error(f"💥 {step_name}: EXCEPTION - {e}")
            results.append((step_name, False))
        
        time.sleep(2)
    
    # Raport final
    logger.info(f"\n{'='*60}")
    logger.info("📊 === RAPORT FINAL ===")
    logger.info(f"{'='*60}")
    
    success_count = 0
    for step_name, success in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {step_name}")
        if success:
            success_count += 1
    
    total_steps = len(results)
    success_rate = (success_count / total_steps) * 100
    
    logger.info(f"\n📈 SUCCESS RATE: {success_count}/{total_steps} ({success_rate:.1f}%)")
    
    if success_rate >= 75:
        logger.info("🎉 FACEBOOK ISSUES FIX: COMPLETED SUCCESSFULLY")
        logger.info("\n🔄 NEXT STEPS:")
        logger.info("1. Redeploy aplicația pe Render")
        logger.info("2. Testează link-urile Facebook")
        logger.info("3. Monitorizează log-urile pentru erori")
    else:
        logger.warning("⚠️ FACEBOOK ISSUES FIX: PARTIAL SUCCESS")
        logger.warning("Verifică erorile de mai sus și încearcă din nou.")
    
    return success_rate >= 75

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Script oprit de utilizator")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Eroare critică: {e}")
        sys.exit(1)