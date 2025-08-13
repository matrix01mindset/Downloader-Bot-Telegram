#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pentru îmbunătățirile anti-bot și rezolvarea problemelor de blocare
"""

import logging
import sys
import time
from typing import Dict, List, Any

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_improved_anti_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Import modulele noastre
try:
    from downloader import download_video
    from anti_bot_detection import (
        create_anti_bot_ydl_opts,
        get_platform_from_url,
        log_anti_bot_status,
        implement_rate_limiting
    )
except ImportError as e:
    logger.error(f"Eroare la importul modulelor: {e}")
    sys.exit(1)

# URL-uri de test pentru fiecare platformă cu probleme
TEST_URLS = {
    'tiktok': [
        'https://vm.tiktok.com/ZMhvqjqjq/',  # URL care a funcționat anterior
        'https://www.tiktok.com/@tiktok/video/7016451766297570565'  # URL care a fost blocat
    ],
    'instagram': [
        'https://www.instagram.com/p/CwqAgzNSzpT/',  # URL care necesita autentificare
        'https://www.instagram.com/reel/CwqAgzNSzpT/'  # Același conținut ca reel
    ],
    'facebook': [
        'https://www.facebook.com/watch/?v=1234567890',  # URL de test Facebook
        'https://fb.watch/test123'  # URL scurt Facebook
    ],
    'vimeo': [
        'https://vimeo.com/76979871',  # URL care avea probleme TLS
        'https://vimeo.com/148751763'  # Alt URL pentru test
    ],
    'twitter': [
        'https://twitter.com/i/status/1234567890',  # URL Twitter/X
        'https://x.com/i/status/1234567890'  # URL X.com
    ]
}

def test_platform_improvements(platform: str, urls: List[str]) -> Dict[str, Any]:
    """
    Testează îmbunătățirile pentru o platformă specifică
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTARE ÎMBUNĂTĂȚIRI: {platform.upper()}")
    logger.info(f"{'='*60}")
    
    results = {
        'platform': platform,
        'total_urls': len(urls),
        'successful': 0,
        'failed': 0,
        'errors': [],
        'successes': []
    }
    
    for i, url in enumerate(urls, 1):
        logger.info(f"\n🔍 Test {i}/{len(urls)}: {url}")
        
        try:
            # Implementează rate limiting
            implement_rate_limiting(platform)
            
            # Testează descărcarea cu configurațiile îmbunătățite
            start_time = time.time()
            result = download_video(url)
            duration = time.time() - start_time
            
            if result and result.get('success'):
                logger.info(f"  ✅ SUCCES! Descărcare completă în {duration:.2f}s")
                logger.info(f"     📁 Fișier: {result.get('file_path', 'N/A')}")
                logger.info(f"     📊 Mărime: {result.get('file_size', 'N/A')} bytes")
                
                results['successful'] += 1
                results['successes'].append({
                    'url': url,
                    'duration': duration,
                    'file_path': result.get('file_path'),
                    'file_size': result.get('file_size')
                })
                
                # Log success pentru anti-bot
                log_anti_bot_status(platform, True, f"Descărcare reușită în {duration:.2f}s")
                
            else:
                error_msg = result.get('error', 'Eroare necunoscută') if result else 'Rezultat None'
                logger.error(f"  ❌ EȘEC: {error_msg}")
                
                results['failed'] += 1
                results['errors'].append({
                    'url': url,
                    'error': error_msg
                })
                
                # Log failure pentru anti-bot
                log_anti_bot_status(platform, False, error_msg)
                
        except Exception as e:
            error_msg = f"Excepție: {str(e)}"
            logger.error(f"  ❌ EROARE: {error_msg}")
            
            results['failed'] += 1
            results['errors'].append({
                'url': url,
                'error': error_msg
            })
            
            # Log failure pentru anti-bot
            log_anti_bot_status(platform, False, error_msg)
    
    return results

def test_anti_bot_configurations():
    """
    Testează configurațiile anti-bot pentru toate platformele
    """
    logger.info("\n🚀 Începere teste îmbunătățiri anti-bot")
    logger.info(f"⏰ Timp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    for platform, urls in TEST_URLS.items():
        try:
            # Testează configurațiile anti-bot pentru platformă
            logger.info(f"\n🧪 Testare configurații anti-bot pentru {platform}...")
            
            # Creează opțiuni anti-bot
            test_url = urls[0] if urls else f"https://{platform}.com/test"
            ydl_opts = create_anti_bot_ydl_opts(test_url)
            
            if ydl_opts:
                logger.info(f"  ✅ Configurații anti-bot create pentru {platform}")
                logger.info(f"     🔧 User-Agent: {ydl_opts.get('http_headers', {}).get('User-Agent', 'N/A')[:50]}...")
                logger.info(f"     🌐 Geo bypass: {ydl_opts.get('geo_bypass', False)}")
                logger.info(f"     🔄 Retries: {ydl_opts.get('retries', 'N/A')}")
                logger.info(f"     ⏱️ Socket timeout: {ydl_opts.get('socket_timeout', 'N/A')}s")
            else:
                logger.warning(f"  ⚠️ Nu s-au putut crea configurații anti-bot pentru {platform}")
            
            # Testează descărcările
            results = test_platform_improvements(platform, urls)
            all_results.append(results)
            
        except Exception as e:
            logger.error(f"Eroare la testarea {platform}: {e}")
            all_results.append({
                'platform': platform,
                'total_urls': len(urls),
                'successful': 0,
                'failed': len(urls),
                'errors': [{'error': str(e)}],
                'successes': []
            })
    
    return all_results

def generate_improvement_report(results: List[Dict[str, Any]]):
    """
    Generează raport cu îmbunătățirile
    """
    logger.info(f"\n{'='*60}")
    logger.info("📊 RAPORT ÎMBUNĂTĂȚIRI ANTI-BOT")
    logger.info(f"{'='*60}")
    
    total_urls = sum(r['total_urls'] for r in results)
    total_successful = sum(r['successful'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    
    success_rate = (total_successful / total_urls * 100) if total_urls > 0 else 0
    
    logger.info(f"📈 Statistici generale:")
    logger.info(f"   📊 Total URL-uri testate: {total_urls}")
    logger.info(f"   ✅ Descărcări reușite: {total_successful}")
    logger.info(f"   ❌ Descărcări eșuate: {total_failed}")
    logger.info(f"   📈 Rata de succes: {success_rate:.1f}%")
    
    logger.info(f"\n📋 Rezultate per platformă:")
    for result in results:
        platform = result['platform']
        success_rate_platform = (result['successful'] / result['total_urls'] * 100) if result['total_urls'] > 0 else 0
        
        logger.info(f"\n  🔧 {platform.upper()}:")
        logger.info(f"     📊 URL-uri: {result['total_urls']}")
        logger.info(f"     ✅ Reușite: {result['successful']}")
        logger.info(f"     ❌ Eșuate: {result['failed']}")
        logger.info(f"     📈 Rata de succes: {success_rate_platform:.1f}%")
        
        # Afișează erorile pentru platformele cu probleme
        if result['errors']:
            logger.info(f"     ⚠️ Probleme identificate:")
            for error in result['errors'][:3]:  # Primele 3 erori
                logger.info(f"       - {error.get('url', 'N/A')}: {error.get('error', 'N/A')[:100]}...")
    
    # Recomandări
    logger.info(f"\n💡 Recomandări:")
    
    if success_rate < 50:
        logger.info("   🔴 Rata de succes scăzută - necesare îmbunătățiri suplimentare")
        logger.info("   💡 Consideră folosirea de proxy-uri premium")
        logger.info("   💡 Implementează cookies pentru Instagram/Facebook")
    elif success_rate < 80:
        logger.info("   🟡 Rata de succes moderată - îmbunătățiri parțiale")
        logger.info("   💡 Optimizează configurațiile pentru platformele problematice")
    else:
        logger.info("   🟢 Rata de succes bună - îmbunătățirile funcționează")
        logger.info("   💡 Monitorizează în continuare pentru stabilitate")
    
    logger.info(f"\n📄 Log detaliat salvat în: test_improved_anti_bot.log")

def main():
    """
    Funcția principală de test
    """
    try:
        logger.info("🔧 Testare îmbunătățiri anti-bot pentru rezolvarea problemelor de blocare")
        
        # Rulează testele
        results = test_anti_bot_configurations()
        
        # Generează raportul
        generate_improvement_report(results)
        
        logger.info("\n✅ Teste finalizate cu succes!")
        
    except Exception as e:
        logger.error(f"Eroare în testare: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)