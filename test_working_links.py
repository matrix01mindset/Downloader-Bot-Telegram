#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test cu link-uri publice cunoscute care ar trebui să funcționeze
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
        logging.FileHandler('test_working_platforms.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import funcții din downloader
try:
    from downloader import download_video, is_supported_url, validate_url
except ImportError as e:
    logger.error(f"Eroare la importul downloader: {e}")
    sys.exit(1)

# Link-uri publice cunoscute care ar trebui să funcționeze
WORKING_TEST_LINKS = {
    'Reddit': [
        'https://www.reddit.com/r/videos/comments/1b7k8zg/this_is_a_test/',  # Link Reddit real
        'https://www.reddit.com/r/funny/comments/1234567/test_video/',  # Alt link
    ],
    'Vimeo': [
        'https://vimeo.com/34741214',  # Video public Vimeo
        'https://vimeo.com/148751763',  # Alt video public
    ],
    'Dailymotion': [
        'https://www.dailymotion.com/video/x7tgad0',  # Video public Dailymotion
        'https://www.dailymotion.com/video/x2hwqn9',  # Alt video
    ],
    'Facebook': [
        'https://www.facebook.com/watch?v=1234567890123456',  # Placeholder
    ],
    'Instagram': [
        'https://www.instagram.com/p/CwqAgzNSzpT/',  # Post public
    ],
    'TikTok': [
        'https://www.tiktok.com/@tiktok/video/7016451766297570565',  # TikTok oficial
    ],
    'Twitter/X': [
        'https://twitter.com/Twitter/status/1445078208190291973',  # Tweet oficial
    ],
    'Threads': [
        'https://www.threads.net/@zuck/post/CuXFPIeLLod',  # Post Zuckerberg
    ],
    'Pinterest': [
        'https://www.pinterest.com/pin/1234567890123456789/',  # Placeholder
    ]
}

def test_single_platform(platform_name, test_urls):
    """Testează o singură platformă cu debugging detaliat"""
    logger.info(f"\n" + "="*70)
    logger.info(f"🔧 DEBUGGING PLATFORMĂ: {platform_name}")
    logger.info("="*70)
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        logger.info(f"\n🎯 Test {i}/{len(test_urls)}: {url}")
        
        # Verifică validarea
        is_supported = is_supported_url(url)
        is_valid, validation_msg = validate_url(url)
        
        logger.info(f"  ✅ URL suportat: {is_supported}")
        logger.info(f"  ✅ URL valid: {is_valid} - {validation_msg}")
        
        if not is_supported or not is_valid:
            logger.warning(f"  ⚠️ URL-ul nu trece validarea de bază")
            results.append({
                'url': url,
                'supported': is_supported,
                'valid': is_valid,
                'error': f"Validare eșuată: {validation_msg}",
                'success': False
            })
            continue
        
        # Încearcă descărcarea cu debugging
        logger.info(f"  🎬 Începere descărcare cu debugging...")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"  📁 Director temporar: {temp_dir}")
                
                # Activează logging detaliat pentru această descărcare
                original_level = logging.getLogger().level
                logging.getLogger().setLevel(logging.DEBUG)
                
                result = download_video(url, temp_dir)
                
                # Restaurează nivelul de logging
                logging.getLogger().setLevel(original_level)
                
                if result.get('success'):
                    logger.info(f"  🎉 SUCCES COMPLET!")
                    logger.info(f"    📋 Titlu: {result.get('title', 'N/A')}")
                    
                    if 'file_path' in result and os.path.exists(result['file_path']):
                        file_size = os.path.getsize(result['file_path'])
                        logger.info(f"    📁 Fișier: {os.path.basename(result['file_path'])}")
                        logger.info(f"    📊 Mărime: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
                        
                        # Verifică dacă fișierul este valid
                        if file_size > 1000:  # Cel puțin 1KB
                            logger.info(f"    ✅ Fișier valid (mărime > 1KB)")
                        else:
                            logger.warning(f"    ⚠️ Fișier suspect de mic")
                    
                    results.append({
                        'url': url,
                        'supported': is_supported,
                        'valid': is_valid,
                        'result': result,
                        'success': True
                    })
                    
                else:
                    error_msg = result.get('error', 'Eroare necunoscută')
                    logger.error(f"  ❌ EȘEC DESCĂRCARE")
                    logger.error(f"    🔴 Eroare: {error_msg}")
                    
                    # Analizează tipul de eroare
                    if 'blocked' in error_msg.lower() or 'ip' in error_msg.lower():
                        logger.error(f"    🚫 Tip eroare: IP blocat")
                    elif 'private' in error_msg.lower() or 'authentication' in error_msg.lower():
                        logger.error(f"    🔒 Tip eroare: Conținut privat")
                    elif 'not found' in error_msg.lower() or '404' in error_msg:
                        logger.error(f"    🔍 Tip eroare: Conținut inexistent")
                    elif 'unsupported' in error_msg.lower():
                        logger.error(f"    🚧 Tip eroare: Format nesuportat")
                    else:
                        logger.error(f"    ❓ Tip eroare: Necunoscut")
                    
                    results.append({
                        'url': url,
                        'supported': is_supported,
                        'valid': is_valid,
                        'result': result,
                        'error': error_msg,
                        'success': False
                    })
                    
        except Exception as e:
            logger.error(f"  💥 EXCEPȚIE NEAȘTEPTATĂ: {str(e)}")
            import traceback
            logger.error(f"  📋 Traceback complet:\n{traceback.format_exc()}")
            
            results.append({
                'url': url,
                'supported': is_supported,
                'valid': is_valid,
                'error': str(e),
                'success': False
            })
    
    return results

def analyze_platform_issues(platform_name, results):
    """Analizează problemele unei platforme și sugerează soluții"""
    logger.info(f"\n🔍 ANALIZĂ PROBLEME {platform_name}:")
    
    total = len(results)
    successful = len([r for r in results if r.get('success', False)])
    
    if successful == total:
        logger.info(f"  🎉 Platformă complet funcțională! ({successful}/{total})")
        return []
    
    logger.info(f"  📊 Status: {successful}/{total} reușite ({successful/total*100:.1f}%)")
    
    # Analizează tipurile de erori
    error_types = {}
    solutions = []
    
    for result in results:
        if not result.get('success', False):
            error = result.get('error', 'Eroare necunoscută')
            error_lower = error.lower()
            
            if 'blocked' in error_lower or 'ip' in error_lower:
                error_types['ip_blocked'] = error_types.get('ip_blocked', 0) + 1
            elif 'private' in error_lower or 'authentication' in error_lower:
                error_types['private_content'] = error_types.get('private_content', 0) + 1
            elif 'not found' in error_lower or '404' in error_lower:
                error_types['not_found'] = error_types.get('not_found', 0) + 1
            elif 'unsupported' in error_lower:
                error_types['unsupported'] = error_types.get('unsupported', 0) + 1
            else:
                error_types['unknown'] = error_types.get('unknown', 0) + 1
    
    # Sugerează soluții bazate pe tipurile de erori
    if error_types.get('ip_blocked', 0) > 0:
        logger.warning(f"  🚫 {error_types['ip_blocked']} erori de IP blocat")
        solutions.append("Implementează proxy rotation sau VPN")
        solutions.append("Adaugă user-agent rotation")
        solutions.append("Implementează rate limiting mai agresiv")
    
    if error_types.get('private_content', 0) > 0:
        logger.warning(f"  🔒 {error_types['private_content']} erori de conținut privat")
        solutions.append("Implementează sistem de cookies")
        solutions.append("Adaugă autentificare pentru platformă")
        solutions.append("Folosește link-uri publice pentru teste")
    
    if error_types.get('not_found', 0) > 0:
        logger.warning(f"  🔍 {error_types['not_found']} erori de conținut inexistent")
        solutions.append("Verifică și actualizează link-urile de test")
        solutions.append("Implementează validare URL înainte de descărcare")
    
    if error_types.get('unsupported', 0) > 0:
        logger.warning(f"  🚧 {error_types['unsupported']} erori de format nesuportat")
        solutions.append("Actualizează yt-dlp la ultima versiune")
        solutions.append("Adaugă extractors specifici pentru platformă")
    
    if error_types.get('unknown', 0) > 0:
        logger.warning(f"  ❓ {error_types['unknown']} erori necunoscute")
        solutions.append("Activează logging detaliat pentru debugging")
        solutions.append("Analizează manual erorile specifice")
    
    if solutions:
        logger.info(f"  💡 Soluții sugerate:")
        for i, solution in enumerate(solutions[:5], 1):  # Primele 5 soluții
            logger.info(f"    {i}. {solution}")
    
    return solutions

def main():
    """Funcția principală"""
    logger.info(f"🚀 Începere debugging detaliat la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_solutions = {}
    
    try:
        # Testează fiecare platformă cu debugging detaliat
        for platform, urls in WORKING_TEST_LINKS.items():
            results = test_single_platform(platform, urls)
            solutions = analyze_platform_issues(platform, results)
            all_solutions[platform] = solutions
        
        # Raport final cu soluții
        logger.info(f"\n" + "="*70)
        logger.info("📋 RAPORT FINAL CU SOLUȚII")
        logger.info("="*70)
        
        platforms_needing_work = [p for p, s in all_solutions.items() if s]
        
        if platforms_needing_work:
            logger.info(f"\n🔧 Platforme care necesită implementări ({len(platforms_needing_work)}/{len(all_solutions)}):")
            for platform in platforms_needing_work:
                logger.info(f"  🔴 {platform}: {len(all_solutions[platform])} soluții sugerate")
        else:
            logger.info(f"\n🎉 Toate platformele funcționează perfect!")
        
        logger.info(f"\n✅ Debugging finalizat cu succes!")
        logger.info(f"📄 Log detaliat salvat în: test_working_platforms.log")
        
    except Exception as e:
        logger.error(f"❌ Eroare în timpul debugging-ului: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())