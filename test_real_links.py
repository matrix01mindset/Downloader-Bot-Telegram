#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test cu link-uri reale pentru toate platformele
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
        logging.FileHandler('test_real_platforms.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import funcții din downloader
try:
    from downloader import download_video, is_supported_url, validate_url
except ImportError as e:
    logger.error(f"Eroare la importul downloader: {e}")
    sys.exit(1)

# Link-uri reale de test (acestea sunt link-uri publice funcționale)
REAL_TEST_LINKS = {
    'TikTok': [
        'https://www.tiktok.com/@tiktok/video/7016451766297570565',  # Official TikTok account
        'https://vm.tiktok.com/ZMhvqjqjq/'  # Short link (poate să nu funcționeze)
    ],
    'Instagram': [
        'https://www.instagram.com/p/CwqAgzNSzpT/',  # Public post
        'https://www.instagram.com/reel/CwqAgzNSzpT/'  # Public reel
    ],
    'Facebook': [
        'https://www.facebook.com/watch?v=1234567890123456',  # Placeholder
        'https://fb.watch/abcdefghij/'  # Placeholder
    ],
    'Twitter/X': [
        'https://twitter.com/Twitter/status/1445078208190291973',  # Official Twitter
        'https://x.com/elonmusk/status/1445078208190291973'  # Public tweet
    ],
    'Threads': [
        'https://www.threads.net/@zuck/post/CuXFPIeLLod',  # Mark Zuckerberg public post
    ],
    'Pinterest': [
        'https://www.pinterest.com/pin/1234567890123456789/',  # Placeholder
        'https://pin.it/abcdefg'  # Placeholder
    ],
    'Reddit': [
        'https://www.reddit.com/r/videos/comments/15x8k9q/this_is_a_test_video/',  # Placeholder
        'https://v.redd.it/abcdefghijk',  # Placeholder
    ],
    'Vimeo': [
        'https://vimeo.com/148751763',  # Public Vimeo video
        'https://vimeo.com/76979871'   # Another public video
    ],
    'Dailymotion': [
        'https://www.dailymotion.com/video/x2hwqn9',  # Public video
        'https://dai.ly/x2hwqn9'  # Short link
    ]
}

def test_platform_individually(platform, urls):
    """Testează o platformă individual"""
    logger.info(f"\n" + "="*60)
    logger.info(f"TESTARE PLATFORMĂ: {platform}")
    logger.info("="*60)
    
    results = []
    
    for i, url in enumerate(urls, 1):
        logger.info(f"\n🔍 Test {i}/{len(urls)}: {url}")
        
        # Verifică suportul URL
        is_supported = is_supported_url(url)
        is_valid, validation_msg = validate_url(url)
        
        logger.info(f"  📋 Suportat: {'✅' if is_supported else '❌'}")
        logger.info(f"  📋 Valid: {'✅' if is_valid else '❌'} - {validation_msg}")
        
        if not is_supported or not is_valid:
            results.append({
                'url': url,
                'supported': is_supported,
                'valid': is_valid,
                'validation_msg': validation_msg,
                'download_result': None
            })
            continue
        
        # Încearcă descărcarea
        logger.info(f"  🎬 Încercare descărcare...")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                download_result = download_video(url, temp_dir)
                
                if download_result.get('success'):
                    logger.info(f"  ✅ SUCCES!")
                    logger.info(f"    📁 Titlu: {download_result.get('title', 'N/A')}")
                    
                    if 'file_path' in download_result and os.path.exists(download_result['file_path']):
                        file_size = os.path.getsize(download_result['file_path'])
                        logger.info(f"    📁 Fișier: {download_result['file_path']}")
                        logger.info(f"    📁 Mărime: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
                    
                    results.append({
                        'url': url,
                        'supported': is_supported,
                        'valid': is_valid,
                        'validation_msg': validation_msg,
                        'download_result': download_result,
                        'success': True
                    })
                else:
                    logger.error(f"  ❌ EȘEC: {download_result.get('error', 'Eroare necunoscută')}")
                    results.append({
                        'url': url,
                        'supported': is_supported,
                        'valid': is_valid,
                        'validation_msg': validation_msg,
                        'download_result': download_result,
                        'success': False
                    })
                    
        except Exception as e:
            logger.error(f"  ❌ EXCEPȚIE: {str(e)}")
            import traceback
            logger.error(f"  📋 Traceback: {traceback.format_exc()}")
            
            results.append({
                'url': url,
                'supported': is_supported,
                'valid': is_valid,
                'validation_msg': validation_msg,
                'download_result': {'success': False, 'error': str(e)},
                'success': False
            })
    
    return results

def generate_platform_report(platform, results):
    """Generează raport pentru o platformă"""
    logger.info(f"\n📊 RAPORT {platform}:")
    
    total = len(results)
    successful = len([r for r in results if r.get('success', False)])
    supported = len([r for r in results if r.get('supported', False)])
    valid = len([r for r in results if r.get('valid', False)])
    
    logger.info(f"  📈 Total URL-uri: {total}")
    logger.info(f"  📈 Suportate: {supported}/{total} ({supported/total*100:.1f}%)")
    logger.info(f"  📈 Valide: {valid}/{total} ({valid/total*100:.1f}%)")
    logger.info(f"  📈 Descărcări reușite: {successful}/{total} ({successful/total*100:.1f}%)")
    
    # Probleme identificate
    problems = []
    for result in results:
        if not result.get('supported'):
            problems.append(f"URL nesuportat: {result['url']}")
        elif not result.get('valid'):
            problems.append(f"URL invalid: {result['url']} - {result['validation_msg']}")
        elif not result.get('success', False):
            error = result.get('download_result', {}).get('error', 'Eroare necunoscută')
            problems.append(f"Descărcare eșuată: {result['url']} - {error}")
    
    if problems:
        logger.info(f"  ⚠️ Probleme identificate:")
        for problem in problems:
            logger.info(f"    - {problem}")
    else:
        logger.info(f"  ✅ Nicio problemă identificată!")
    
    return {
        'platform': platform,
        'total': total,
        'successful': successful,
        'supported': supported,
        'valid': valid,
        'problems': problems
    }

def main():
    """Funcția principală"""
    logger.info(f"🚀 Începere teste detaliate la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_reports = []
    
    try:
        # Testează fiecare platformă individual
        for platform, urls in REAL_TEST_LINKS.items():
            results = test_platform_individually(platform, urls)
            report = generate_platform_report(platform, results)
            all_reports.append(report)
        
        # Raport final general
        logger.info(f"\n" + "="*60)
        logger.info("RAPORT FINAL GENERAL")
        logger.info("="*60)
        
        total_platforms = len(all_reports)
        working_platforms = len([r for r in all_reports if r['successful'] > 0])
        fully_working = len([r for r in all_reports if r['successful'] == r['total']])
        
        logger.info(f"\n📊 Statistici Generale:")
        logger.info(f"  🔧 Total platforme testate: {total_platforms}")
        logger.info(f"  ✅ Platforme funcționale (parțial): {working_platforms}/{total_platforms}")
        logger.info(f"  🎯 Platforme complet funcționale: {fully_working}/{total_platforms}")
        
        logger.info(f"\n🎯 Status pe platforme:")
        for report in all_reports:
            status = "🟢" if report['successful'] == report['total'] else "🟡" if report['successful'] > 0 else "🔴"
            logger.info(f"  {status} {report['platform']}: {report['successful']}/{report['total']} reușite")
        
        # Platforme cu probleme
        problematic = [r for r in all_reports if r['successful'] < r['total']]
        if problematic:
            logger.info(f"\n⚠️ Platforme care necesită atenție:")
            for report in problematic:
                logger.info(f"  🔧 {report['platform']}:")
                for problem in report['problems'][:3]:  # Primele 3 probleme
                    logger.info(f"    - {problem}")
                if len(report['problems']) > 3:
                    logger.info(f"    - ... și încă {len(report['problems'])-3} probleme")
        
        logger.info(f"\n✅ Teste finalizate cu succes!")
        logger.info(f"📄 Log detaliat salvat în: test_real_platforms.log")
        
    except Exception as e:
        logger.error(f"❌ Eroare în timpul testelor: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())