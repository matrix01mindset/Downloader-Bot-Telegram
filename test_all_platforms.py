#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test comprehensiv pentru toate platformele suportate
"""

import os
import sys
import logging
import tempfile
from datetime import datetime

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_platforms.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import funcții din downloader
try:
    from downloader import download_video, is_supported_url, validate_url
except ImportError as e:
    logger.error(f"Eroare la importul downloader: {e}")
    sys.exit(1)

# Link-uri de test pentru fiecare platformă
TEST_LINKS = {
    'TikTok': [
        'https://www.tiktok.com/@username/video/1234567890',
        'https://vm.tiktok.com/ZMhvqjqjq/'
    ],
    'Instagram': [
        'https://www.instagram.com/p/ABC123DEF456/',
        'https://www.instagram.com/reel/XYZ789ABC123/'
    ],
    'Facebook': [
        'https://www.facebook.com/watch?v=1234567890123456',
        'https://fb.watch/abcdefghij/',
        'https://www.facebook.com/username/videos/1234567890/'
    ],
    'Twitter/X': [
        'https://twitter.com/username/status/1234567890123456789',
        'https://x.com/username/status/9876543210987654321'
    ],
    'Threads': [
        'https://www.threads.net/@username/post/ABC123DEF456',
        'https://threads.com/@username/post/XYZ789'
    ],
    'Pinterest': [
        'https://www.pinterest.com/pin/1234567890123456789/',
        'https://pin.it/abcdefg'
    ],
    'Reddit': [
        'https://www.reddit.com/r/videos/comments/abc123/video_title/',
        'https://v.redd.it/abcdefghijk',
        'https://i.redd.it/xyz789.mp4'
    ],
    'Vimeo': [
        'https://vimeo.com/123456789',
        'https://player.vimeo.com/video/987654321'
    ],
    'Dailymotion': [
        'https://www.dailymotion.com/video/x123456',
        'https://dai.ly/x789abc'
    ]
}

def test_url_validation():
    """Testează validarea URL-urilor"""
    logger.info("\n" + "="*50)
    logger.info("TESTARE VALIDARE URL-URI")
    logger.info("="*50)
    
    results = {}
    
    for platform, urls in TEST_LINKS.items():
        logger.info(f"\n🔍 Testare {platform}:")
        platform_results = []
        
        for url in urls:
            # Test is_supported_url
            is_supported = is_supported_url(url)
            
            # Test validate_url
            is_valid, validation_msg = validate_url(url)
            
            result = {
                'url': url,
                'is_supported': is_supported,
                'is_valid': is_valid,
                'validation_msg': validation_msg
            }
            
            platform_results.append(result)
            
            status_supported = "✅" if is_supported else "❌"
            status_valid = "✅" if is_valid else "❌"
            
            logger.info(f"  {status_supported} Suportat | {status_valid} Valid | {url}")
            if not is_valid:
                logger.info(f"    Motiv: {validation_msg}")
        
        results[platform] = platform_results
    
    return results

def test_download_functionality():
    """Testează funcționalitatea de descărcare cu link-uri reale"""
    logger.info("\n" + "="*50)
    logger.info("TESTARE FUNCȚIONALITATE DESCĂRCARE")
    logger.info("="*50)
    
    # Link-uri reale de test (acestea trebuie să fie link-uri funcționale)
    REAL_TEST_LINKS = {
        'Reddit': [
            'https://www.reddit.com/r/videos/comments/15x8k9q/this_is_a_test_video/',
        ],
        # Adaugă alte link-uri reale aici când le găsești
    }
    
    results = {}
    
    for platform, urls in REAL_TEST_LINKS.items():
        logger.info(f"\n🎬 Testare descărcare {platform}:")
        platform_results = []
        
        for url in urls:
            logger.info(f"\n  Testare URL: {url}")
            
            try:
                # Creează director temporar pentru test
                with tempfile.TemporaryDirectory() as temp_dir:
                    result = download_video(url, temp_dir)
                    
                    platform_results.append({
                        'url': url,
                        'result': result
                    })
                    
                    if result.get('success'):
                        logger.info(f"  ✅ Succes: {result.get('title', 'N/A')}")
                        if 'file_path' in result:
                            file_size = os.path.getsize(result['file_path']) if os.path.exists(result['file_path']) else 0
                            logger.info(f"    Fișier: {result['file_path']} ({file_size} bytes)")
                    else:
                        logger.error(f"  ❌ Eșec: {result.get('error', 'Eroare necunoscută')}")
                        
            except Exception as e:
                logger.error(f"  ❌ Excepție: {str(e)}")
                platform_results.append({
                    'url': url,
                    'result': {'success': False, 'error': str(e)}
                })
        
        results[platform] = platform_results
    
    return results

def generate_report(validation_results, download_results):
    """Generează raport final"""
    logger.info("\n" + "="*50)
    logger.info("RAPORT FINAL")
    logger.info("="*50)
    
    # Statistici validare
    total_urls = 0
    supported_urls = 0
    valid_urls = 0
    
    for platform, results in validation_results.items():
        for result in results:
            total_urls += 1
            if result['is_supported']:
                supported_urls += 1
            if result['is_valid']:
                valid_urls += 1
    
    logger.info(f"\n📊 Statistici Validare:")
    logger.info(f"  Total URL-uri testate: {total_urls}")
    logger.info(f"  URL-uri suportate: {supported_urls}/{total_urls} ({supported_urls/total_urls*100:.1f}%)")
    logger.info(f"  URL-uri valide: {valid_urls}/{total_urls} ({valid_urls/total_urls*100:.1f}%)")
    
    # Statistici descărcare
    if download_results:
        total_downloads = 0
        successful_downloads = 0
        
        for platform, results in download_results.items():
            for result in results:
                total_downloads += 1
                if result['result'].get('success'):
                    successful_downloads += 1
        
        logger.info(f"\n🎬 Statistici Descărcare:")
        logger.info(f"  Total descărcări testate: {total_downloads}")
        logger.info(f"  Descărcări reușite: {successful_downloads}/{total_downloads} ({successful_downloads/total_downloads*100:.1f}%)")
    
    # Platforme cu probleme
    logger.info(f"\n⚠️ Platforme cu probleme:")
    for platform, results in validation_results.items():
        unsupported = [r for r in results if not r['is_supported']]
        invalid = [r for r in results if not r['is_valid']]
        
        if unsupported or invalid:
            logger.info(f"  {platform}:")
            if unsupported:
                logger.info(f"    - {len(unsupported)} URL-uri nesuportate")
            if invalid:
                logger.info(f"    - {len(invalid)} URL-uri invalide")

def main():
    """Funcția principală"""
    logger.info(f"Începere teste la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test validare URL-uri
        validation_results = test_url_validation()
        
        # Test descărcare (doar cu link-uri reale)
        download_results = test_download_functionality()
        
        # Generează raport
        generate_report(validation_results, download_results)
        
        logger.info(f"\n✅ Teste finalizate cu succes!")
        logger.info(f"📄 Log salvat în: test_platforms.log")
        
    except Exception as e:
        logger.error(f"❌ Eroare în timpul testelor: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())