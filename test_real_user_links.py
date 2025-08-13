#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final cu link-urile reale ale utilizatorului
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
        logging.FileHandler('test_real_user_links.log', encoding='utf-8'),
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

def load_user_links():
    """Încarcă link-urile utilizatorului din fișier"""
    links_file = 'test_links.txt'
    
    if not os.path.exists(links_file):
        logger.error(f"❌ Fișierul {links_file} nu există!")
        return []
    
    try:
        with open(links_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filtrează link-urile valide
        links = []
        for line in lines:
            line = line.strip()
            if line and line.startswith(('http://', 'https://')):
                links.append(line)
        
        logger.info(f"📋 Încărcat {len(links)} link-uri din {links_file}")
        return links
        
    except Exception as e:
        logger.error(f"❌ Eroare la încărcarea link-urilor: {e}")
        return []

def identify_platform(url):
    """Identifică platforma din URL"""
    url_lower = url.lower()
    
    if 'instagram.com' in url_lower:
        return 'Instagram'
    elif 'tiktok.com' in url_lower:
        return 'TikTok'
    elif 'reddit.com' in url_lower:
        return 'Reddit'
    elif 'x.com' in url_lower or 'twitter.com' in url_lower:
        return 'Twitter/X'
    elif 'facebook.com' in url_lower:
        return 'Facebook'
    elif 'threads.com' in url_lower or 'threads.net' in url_lower:
        return 'Threads'
    elif 'vimeo.com' in url_lower:
        return 'Vimeo'
    elif 'dailymotion.com' in url_lower:
        return 'Dailymotion'
    elif 'pinterest.com' in url_lower:
        return 'Pinterest'
    else:
        return 'Necunoscut'

def test_single_link(url, index, total):
    """Testează un singur link"""
    platform = identify_platform(url)
    
    logger.info(f"\n" + "="*80)
    logger.info(f"🎯 TEST {index}/{total}: {platform}")
    logger.info(f"🔗 URL: {url}")
    logger.info(f"="*80)
    
    result = {
        'url': url,
        'platform': platform,
        'index': index,
        'validation_success': False,
        'download_success': False,
        'error': '',
        'file_path': '',
        'file_size': 0,
        'title': '',
        'duration': 0
    }
    
    try:
        # 1. Test validare
        logger.info(f"🔍 Validare URL...")
        is_supported = is_supported_url(url)
        is_valid, validation_msg = validate_url(url)
        
        logger.info(f"   is_supported_url: {is_supported}")
        logger.info(f"   validate_url: {is_valid} - {validation_msg}")
        
        result['validation_success'] = is_valid and is_supported
        
        if not result['validation_success']:
            result['error'] = f"Validare eșuată: {validation_msg}"
            logger.warning(f"⚠️ {result['error']}")
            return result
        
        # 2. Test descărcare
        logger.info(f"📥 Începere descărcare...")
        start_time = time.time()
        
        download_result = download_video(url)
        
        end_time = time.time()
        result['duration'] = end_time - start_time
        
        if download_result.get('success'):
            result['download_success'] = True
            result['file_path'] = download_result.get('file_path', '')
            result['file_size'] = download_result.get('file_size', 0)
            result['title'] = download_result.get('title', '')[:100]  # Limitează titlul
            
            logger.info(f"✅ DESCĂRCARE REUȘITĂ în {result['duration']:.2f}s")
            logger.info(f"📁 Fișier: {result['file_path']}")
            logger.info(f"📏 Mărime: {result['file_size']} bytes")
            logger.info(f"🎬 Titlu: {result['title']}")
            
            # Verifică dacă fișierul există fizic
            if result['file_path'] and os.path.exists(result['file_path']):
                actual_size = os.path.getsize(result['file_path'])
                logger.info(f"✅ Fișier confirmat pe disk: {actual_size} bytes")
                result['file_size'] = actual_size
            else:
                logger.warning(f"⚠️ Fișierul nu există pe disk: {result['file_path']}")
        else:
            result['download_success'] = False
            result['error'] = download_result.get('error', 'Eroare necunoscută')[:200]
            logger.error(f"❌ DESCĂRCARE EȘUATĂ în {result['duration']:.2f}s")
            logger.error(f"💬 Eroare: {result['error']}")
        
    except Exception as e:
        result['error'] = f"Excepție: {str(e)}"[:200]
        logger.error(f"❌ EXCEPȚIE: {result['error']}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return result

def generate_comprehensive_report(test_results):
    """Generează raport comprehensiv"""
    logger.info(f"\n" + "="*100)
    logger.info(f"📊 === RAPORT FINAL TESTARE LINK-URI REALE UTILIZATOR ===")
    logger.info(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"="*100)
    
    # Statistici generale
    total_tests = len(test_results)
    successful_validations = sum(1 for r in test_results if r['validation_success'])
    successful_downloads = sum(1 for r in test_results if r['download_success'])
    
    logger.info(f"\n📈 STATISTICI GENERALE:")
    logger.info(f"   📝 Total link-uri testate: {total_tests}")
    logger.info(f"   ✅ Validări reușite: {successful_validations}/{total_tests} ({(successful_validations/total_tests*100):.1f}%)")
    logger.info(f"   📥 Descărcări reușite: {successful_downloads}/{total_tests} ({(successful_downloads/total_tests*100):.1f}%)")
    
    # Statistici per platformă
    platforms = {}
    for result in test_results:
        platform = result['platform']
        if platform not in platforms:
            platforms[platform] = {'total': 0, 'validation_success': 0, 'download_success': 0, 'errors': []}
        
        platforms[platform]['total'] += 1
        if result['validation_success']:
            platforms[platform]['validation_success'] += 1
        if result['download_success']:
            platforms[platform]['download_success'] += 1
        if result['error']:
            platforms[platform]['errors'].append(result['error'])
    
    logger.info(f"\n🎯 STATISTICI PER PLATFORMĂ:")
    for platform, stats in platforms.items():
        val_rate = (stats['validation_success']/stats['total']*100) if stats['total'] > 0 else 0
        down_rate = (stats['download_success']/stats['total']*100) if stats['total'] > 0 else 0
        
        logger.info(f"\n   🔸 {platform}:")
        logger.info(f"      📊 Total: {stats['total']} link-uri")
        logger.info(f"      📝 Validare: {stats['validation_success']}/{stats['total']} ({val_rate:.1f}%)")
        logger.info(f"      📥 Descărcare: {stats['download_success']}/{stats['total']} ({down_rate:.1f}%)")
        
        if stats['errors']:
            logger.info(f"      ❌ Erori comune:")
            # Afișează doar primele 2 erori pentru a nu aglomera
            for error in stats['errors'][:2]:
                logger.info(f"         • {error[:100]}...")
    
    # Detalii descărcări reușite
    successful_results = [r for r in test_results if r['download_success']]
    if successful_results:
        logger.info(f"\n✅ DESCĂRCĂRI REUȘITE ({len(successful_results)}):")
        total_size = 0
        total_duration = 0
        
        for result in successful_results:
            logger.info(f"   🎬 {result['platform']}: {result['title'][:50]}...")
            logger.info(f"      📏 {result['file_size']} bytes, ⏱️ {result['duration']:.1f}s")
            total_size += result['file_size']
            total_duration += result['duration']
        
        logger.info(f"\n   📊 TOTALE:")
        logger.info(f"      📏 Mărime totală: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        logger.info(f"      ⏱️ Timp total descărcare: {total_duration:.1f}s")
        logger.info(f"      📈 Viteză medie: {(total_size/total_duration/1024):.1f} KB/s" if total_duration > 0 else "")
    
    # Recomandări finale
    logger.info(f"\n💡 RECOMANDĂRI FINALE:")
    
    success_rate = (successful_downloads/total_tests*100) if total_tests > 0 else 0
    
    if success_rate >= 80:
        logger.info(f"   🟢 EXCELENT: Rata de succes foarte bună ({success_rate:.1f}%)")
        logger.info(f"   🚀 Sistemul este gata pentru producție!")
        logger.info(f"   📋 Următorii pași:")
        logger.info(f"      1. Integrează cu bot-ul Telegram")
        logger.info(f"      2. Monitorizează performanța în timp real")
        logger.info(f"      3. Adaugă logging pentru utilizatori")
    elif success_rate >= 60:
        logger.info(f"   🟡 BINE: Rata de succes acceptabilă ({success_rate:.1f}%)")
        logger.info(f"   🔧 Îmbunătățiri sugerate:")
        logger.info(f"      1. Optimizează platformele cu rate scăzute")
        logger.info(f"      2. Adaugă mai multe strategii de fallback")
        logger.info(f"      3. Testează cu mai multe link-uri")
    elif success_rate >= 30:
        logger.info(f"   🟠 MODERAT: Rata de succes moderată ({success_rate:.1f}%)")
        logger.info(f"   🔧 Acțiuni necesare:")
        logger.info(f"      1. Analizează erorile comune")
        logger.info(f"      2. Actualizează yt-dlp la ultima versiune")
        logger.info(f"      3. Verifică configurațiile de rețea")
    else:
        logger.info(f"   🔴 CRITIC: Rata de succes scăzută ({success_rate:.1f}%)")
        logger.info(f"   🚨 Acțiuni urgente:")
        logger.info(f"      1. Verifică conexiunea la internet")
        logger.info(f"      2. Reinstalează yt-dlp")
        logger.info(f"      3. Verifică dacă link-urile sunt valide")
        logger.info(f"      4. Testează cu VPN/proxy diferit")
    
    logger.info(f"\n" + "="*100)
    logger.info(f"📋 Raport detaliat salvat în: test_real_user_links.log")
    logger.info(f"="*100)
    
    return success_rate

def main():
    """Funcția principală"""
    logger.info(f"🚀 Începere testare link-uri reale utilizator la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Încarcă link-urile utilizatorului
        user_links = load_user_links()
        
        if not user_links:
            logger.error("❌ Nu s-au găsit link-uri valide pentru testare!")
            return 1
        
        logger.info(f"📋 Se vor testa {len(user_links)} link-uri reale")
        
        # Testează fiecare link
        test_results = []
        
        for i, url in enumerate(user_links, 1):
            result = test_single_link(url, i, len(user_links))
            test_results.append(result)
            
            # Pauză între teste pentru a evita rate limiting
            if i < len(user_links):
                logger.info(f"\n⏱️ Pauză 3s înainte de următorul test...")
                time.sleep(3)
        
        # Generează raportul final
        success_rate = generate_comprehensive_report(test_results)
        
        # Returnează codul de ieșire bazat pe rata de succes
        if success_rate >= 60:
            return 0  # Succes
        elif success_rate >= 30:
            return 1  # Avertisment
        else:
            return 2  # Eroare critică
        
    except Exception as e:
        logger.error(f"❌ Eroare în timpul testării: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 3

if __name__ == "__main__":
    sys.exit(main())