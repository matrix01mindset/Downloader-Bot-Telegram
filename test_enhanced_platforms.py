#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final pentru toate platformele după aplicarea patch-ului îmbunătățit
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_enhanced_platforms.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import funcții din downloader.py
try:
    from downloader import validate_url, is_supported_url, download_video
    logger.info("✅ Import reușit din downloader.py")
except ImportError as e:
    logger.error(f"❌ Eroare import din downloader.py: {e}")
    sys.exit(1)

# Link-uri de test reale și publice pentru toate platformele
TEST_LINKS = {
    'reddit': [
        'https://www.reddit.com/r/funny/comments/15xvs7h/this_is_why_you_should_always_check_your_car/',
        'https://v.redd.it/abc123def456',  # Exemplu generic
        'https://www.reddit.com/r/videos/comments/abc123/test_video/'
    ],
    'vimeo': [
        'https://vimeo.com/148751763',  # Video public cunoscut
        'https://vimeo.com/76979871',   # Alt video public
        'https://player.vimeo.com/video/148751763'
    ],
    'dailymotion': [
        'https://www.dailymotion.com/video/x7tgad0',  # Video public
        'https://dai.ly/x7tgad0',  # Link scurt
        'https://www.dailymotion.com/video/x2jvvep'   # Alt video public
    ],
    'facebook': [
        'https://www.facebook.com/watch?v=1234567890',  # Exemplu generic
        'https://fb.watch/abc123def/',
        'https://m.facebook.com/watch?v=1234567890'
    ],
    'instagram': [
        'https://www.instagram.com/p/ABC123DEF456/',  # Exemplu generic
        'https://www.instagram.com/reel/ABC123DEF456/',
        'https://instagram.com/p/ABC123DEF456/'
    ],
    'tiktok': [
        'https://www.tiktok.com/@user/video/1234567890123456789',  # Exemplu generic
        'https://vm.tiktok.com/ABC123/',
        'https://tiktok.com/@user/video/1234567890123456789'
    ],
    'twitter': [
        'https://twitter.com/user/status/1234567890123456789',  # Exemplu generic
        'https://x.com/user/status/1234567890123456789',
        'https://mobile.twitter.com/user/status/1234567890123456789'
    ],
    'threads': [
        'https://www.threads.net/@user/post/ABC123DEF456',  # Exemplu generic
        'https://threads.net/t/ABC123DEF456'
    ],
    'pinterest': [
        'https://www.pinterest.com/pin/1234567890123456789/',  # Exemplu generic
        'https://pin.it/ABC123DEF',
        'https://pinterest.com/pin/1234567890123456789/'
    ]
}

def test_platform_validation(platform_name, test_urls):
    """Testează validarea URL-urilor pentru o platformă"""
    logger.info(f"\n🔍 === TESTARE VALIDARE {platform_name.upper()} ===")
    
    validation_results = []
    
    for i, url in enumerate(test_urls, 1):
        try:
            logger.info(f"📝 Test {i}/{len(test_urls)}: {url}")
            
            # Test is_supported_url
            is_supported = is_supported_url(url)
            logger.info(f"   is_supported_url: {is_supported}")
            
            # Test validate_url
            is_valid, validation_msg = validate_url(url)
            logger.info(f"   validate_url: {is_valid} - {validation_msg}")
            
            validation_results.append({
                'url': url,
                'is_supported': is_supported,
                'is_valid': is_valid,
                'validation_msg': validation_msg
            })
            
        except Exception as e:
            logger.error(f"   ❌ Eroare validare: {str(e)}")
            validation_results.append({
                'url': url,
                'is_supported': False,
                'is_valid': False,
                'validation_msg': f'Eroare: {str(e)}'
            })
    
    return validation_results

def test_platform_download(platform_name, test_urls, max_tests=1):
    """Testează descărcarea pentru o platformă"""
    logger.info(f"\n⬇️ === TESTARE DESCĂRCARE {platform_name.upper()} ===")
    
    download_results = []
    
    # Testează doar primul URL sau numărul specificat
    urls_to_test = test_urls[:max_tests]
    
    for i, url in enumerate(urls_to_test, 1):
        try:
            logger.info(f"📥 Test descărcare {i}/{len(urls_to_test)}: {url}")
            
            start_time = time.time()
            result = download_video(url)
            end_time = time.time()
            
            duration = end_time - start_time
            
            if result.get('success'):
                logger.info(f"   ✅ SUCCES în {duration:.2f}s")
                logger.info(f"   📁 Fișier: {result.get('file_path', 'N/A')}")
                logger.info(f"   📏 Mărime: {result.get('file_size', 0)} bytes")
                logger.info(f"   🎬 Titlu: {result.get('title', 'N/A')[:50]}...")
                
                # Verifică dacă fișierul există
                file_path = result.get('file_path')
                if file_path and os.path.exists(file_path):
                    actual_size = os.path.getsize(file_path)
                    logger.info(f"   ✅ Fișier confirmat: {actual_size} bytes")
                else:
                    logger.warning(f"   ⚠️ Fișierul nu există: {file_path}")
            else:
                logger.error(f"   ❌ EȘEC în {duration:.2f}s")
                logger.error(f"   💬 Eroare: {result.get('error', 'Eroare necunoscută')}")
            
            download_results.append({
                'url': url,
                'success': result.get('success', False),
                'error': result.get('error', ''),
                'duration': duration,
                'file_size': result.get('file_size', 0),
                'title': result.get('title', ''),
                'platform': result.get('platform', platform_name)
            })
            
        except Exception as e:
            logger.error(f"   ❌ Excepție descărcare: {str(e)}")
            download_results.append({
                'url': url,
                'success': False,
                'error': f'Excepție: {str(e)}',
                'duration': 0,
                'file_size': 0,
                'title': '',
                'platform': platform_name
            })
        
        # Pauză între teste
        if i < len(urls_to_test):
            logger.info("   ⏱️ Pauză 3s între teste...")
            time.sleep(3)
    
    return download_results

def generate_final_report(all_validation_results, all_download_results):
    """Generează raportul final cu statistici complete"""
    logger.info(f"\n" + "="*80)
    logger.info(f"📊 === RAPORT FINAL TESTARE PLATFORME ÎMBUNĂTĂȚITE ===")
    logger.info(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"="*80)
    
    # Statistici validare
    total_validation_tests = sum(len(results) for results in all_validation_results.values())
    successful_validations = sum(
        sum(1 for result in results if result['is_valid']) 
        for results in all_validation_results.values()
    )
    
    logger.info(f"\n🔍 STATISTICI VALIDARE:")
    logger.info(f"   📝 Total teste validare: {total_validation_tests}")
    logger.info(f"   ✅ Validări reușite: {successful_validations}")
    logger.info(f"   📊 Rata de succes validare: {(successful_validations/total_validation_tests*100):.1f}%")
    
    # Statistici descărcare
    total_download_tests = sum(len(results) for results in all_download_results.values())
    successful_downloads = sum(
        sum(1 for result in results if result['success']) 
        for results in all_download_results.values()
    )
    
    logger.info(f"\n⬇️ STATISTICI DESCĂRCARE:")
    logger.info(f"   📥 Total teste descărcare: {total_download_tests}")
    logger.info(f"   ✅ Descărcări reușite: {successful_downloads}")
    logger.info(f"   📊 Rata de succes descărcare: {(successful_downloads/total_download_tests*100):.1f}%")
    
    # Detalii per platformă
    logger.info(f"\n🎯 DETALII PER PLATFORMĂ:")
    
    for platform in TEST_LINKS.keys():
        validation_results = all_validation_results.get(platform, [])
        download_results = all_download_results.get(platform, [])
        
        val_success = sum(1 for r in validation_results if r['is_valid'])
        val_total = len(validation_results)
        
        down_success = sum(1 for r in download_results if r['success'])
        down_total = len(download_results)
        
        logger.info(f"\n   🔸 {platform.upper()}:")
        val_percentage = (val_success/val_total*100) if val_total > 0 else 0
        down_percentage = (down_success/down_total*100) if down_total > 0 else 0
        logger.info(f"      📝 Validare: {val_success}/{val_total} ({val_percentage:.1f}%)")
        logger.info(f"      📥 Descărcare: {down_success}/{down_total} ({down_percentage:.1f}%)")
        
        # Afișează erorile pentru descărcări eșuate
        failed_downloads = [r for r in download_results if not r['success']]
        if failed_downloads:
            logger.info(f"      ❌ Erori descărcare:")
            for failed in failed_downloads:
                error_msg = failed['error'][:100] + '...' if len(failed['error']) > 100 else failed['error']
                logger.info(f"         • {error_msg}")
    
    # Recomandări finale
    logger.info(f"\n💡 RECOMANDĂRI FINALE:")
    
    if successful_downloads == 0:
        logger.info(f"   🔴 CRITIC: Nicio descărcare nu a reușit!")
        logger.info(f"   🔧 Acțiuni necesare:")
        logger.info(f"      1. Verifică conexiunea la internet")
        logger.info(f"      2. Verifică dacă yt-dlp este actualizat")
        logger.info(f"      3. Testează cu link-uri reale și publice")
        logger.info(f"      4. Verifică configurațiile proxy/VPN")
    elif successful_downloads < total_download_tests // 2:
        logger.info(f"   🟡 ATENȚIE: Rata de succes scăzută ({(successful_downloads/total_download_tests*100):.1f}%)")
        logger.info(f"   🔧 Îmbunătățiri sugerate:")
        logger.info(f"      1. Optimizează configurațiile pentru platformele eșuate")
        logger.info(f"      2. Adaugă mai multe strategii de fallback")
        logger.info(f"      3. Implementează rotația de proxy-uri")
    else:
        logger.info(f"   🟢 BINE: Rata de succes acceptabilă ({(successful_downloads/total_download_tests*100):.1f}%)")
        logger.info(f"   🚀 Continuă cu:")
        logger.info(f"      1. Testarea cu link-uri reale din fișierul utilizatorului")
        logger.info(f"      2. Integrarea cu bot-ul Telegram")
        logger.info(f"      3. Monitorizarea performanței în producție")
    
    logger.info(f"\n" + "="*80)
    logger.info(f"📋 Raport salvat în: test_enhanced_platforms.log")
    logger.info(f"="*80)

def main():
    """Funcția principală de testare"""
    logger.info(f"🚀 Începere testare platforme îmbunătățite la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_validation_results = {}
    all_download_results = {}
    
    try:
        # Testează fiecare platformă
        for platform_name, test_urls in TEST_LINKS.items():
            logger.info(f"\n" + "="*60)
            logger.info(f"🎯 TESTARE PLATFORMĂ: {platform_name.upper()}")
            logger.info(f"="*60)
            
            # Test validare
            validation_results = test_platform_validation(platform_name, test_urls)
            all_validation_results[platform_name] = validation_results
            
            # Test descărcare (doar primul URL pentru a economisi timp)
            download_results = test_platform_download(platform_name, test_urls, max_tests=1)
            all_download_results[platform_name] = download_results
            
            # Pauză între platforme
            logger.info(f"\n⏱️ Pauză 5s înainte de următoarea platformă...")
            time.sleep(5)
        
        # Generează raportul final
        generate_final_report(all_validation_results, all_download_results)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Eroare în timpul testării: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())