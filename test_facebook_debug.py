#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Debug Test Script
Testează și diagnostichează problemele cu descărcarea Facebook
"""

import os
import sys
import logging
import tempfile
import yt_dlp
from datetime import datetime

# Configurare logging pentru debugging detaliat
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'facebook_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

# Import modulele locale
try:
    from facebook_fix_patch import (
        enhanced_facebook_extractor_args,
        normalize_facebook_share_url,
        create_robust_facebook_opts,
        generate_facebook_url_variants,
        try_facebook_with_rotation
    )
    logger.info("✅ Facebook fix patch loaded successfully")
except ImportError as e:
    logger.error(f"❌ Nu s-a putut încărca facebook_fix_patch: {e}")
    sys.exit(1)

def test_url_normalization(test_urls):
    """Testează normalizarea URL-urilor"""
    print("\n" + "="*60)
    print("🔧 TEST 1: NORMALIZAREA URL-URILOR")
    print("="*60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. URL Original: {url}")
        normalized = normalize_facebook_share_url(url)
        print(f"   URL Normalizat: {normalized}")
        
        variants = generate_facebook_url_variants(normalized)
        print(f"   Variante generate: {len(variants)}")
        for j, variant in enumerate(variants[:3], 1):  # Afișează doar primele 3
            print(f"     {j}. {variant}")
        if len(variants) > 3:
            print(f"     ... și încă {len(variants) - 3} variante")

def test_info_extraction(test_urls):
    """Testează extragerea informațiilor fără descărcare"""
    print("\n" + "="*60)
    print("📋 TEST 2: EXTRAGEREA INFORMAȚIILOR")
    print("="*60)
    
    # Configurații de test
    test_configs = [
        {
            'name': 'Config Standard',
            'opts': {
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'skip_download': True,
                'extractor_args': enhanced_facebook_extractor_args()
            }
        },
        {
            'name': 'Config Robust',
            'opts': create_robust_facebook_opts()
        }
    ]
    
    for config in test_configs:
        print(f"\n🔧 Testez cu {config['name']}:")
        config['opts']['skip_download'] = True  # Forțează skip download pentru test
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n  {i}. URL: {url[:60]}...")
            
            try:
                with yt_dlp.YoutubeDL(config['opts']) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        print(f"     ✅ SUCCES: {info.get('title', 'N/A')[:50]}")
                        print(f"     📹 Durată: {info.get('duration', 'N/A')} sec")
                        print(f"     👤 Uploader: {info.get('uploader', 'N/A')}")
                        print(f"     🔗 Formats: {len(info.get('formats', []))} disponibile")
                    else:
                        print(f"     ❌ Nu s-au putut extrage informații")
            except Exception as e:
                error_msg = str(e)
                print(f"     ❌ EROARE: {error_msg[:100]}...")
                if 'Cannot parse data' in error_msg:
                    print(f"     🔍 Detectat: Cannot parse data error")
                elif 'private' in error_msg.lower():
                    print(f"     🔒 Detectat: Conținut privat")
                elif 'not available' in error_msg.lower():
                    print(f"     📵 Detectat: Conținut indisponibil")

def test_rotation_system(test_urls):
    """Testează sistemul de rotație"""
    print("\n" + "="*60)
    print("🔄 TEST 3: SISTEMUL DE ROTAȚIE")
    print("="*60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Testez rotația pentru: {url[:60]}...")
        
        # Configurație pentru rotație
        rotation_opts = create_robust_facebook_opts()
        rotation_opts['skip_download'] = True
        
        try:
            success_url, info, rotation_info = try_facebook_with_rotation(
                url, rotation_opts, max_attempts=4
            )
            
            if success_url and info:
                print(f"   ✅ ROTAȚIE REUȘITĂ!")
                print(f"   🎯 Format reușit: {rotation_info.get('successful_format', 'N/A')}")
                print(f"   🔢 Încercare: {rotation_info.get('attempt_number', 'N/A')}")
                print(f"   📹 Video: {info.get('title', 'N/A')[:50]}")
            else:
                print(f"   ❌ ROTAȚIE EȘUATĂ")
                if rotation_info:
                    print(f"   🔍 Tip eroare: {rotation_info.get('error_type', 'N/A')}")
                    print(f"   📋 Formate încercate: {rotation_info.get('attempted_formats', [])}")
                    if rotation_info.get('error_message'):
                        print(f"   💬 Ultima eroare: {rotation_info['error_message'][:80]}...")
        except Exception as e:
            print(f"   ❌ EROARE ÎN ROTAȚIE: {str(e)[:100]}...")

def test_download_simulation(test_urls):
    """Simulează descărcarea (fără salvare efectivă)"""
    print("\n" + "="*60)
    print("💾 TEST 4: SIMULARE DESCĂRCARE")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Director temporar: {temp_dir}")
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n{i}. Simulez descărcarea: {url[:60]}...")
            
            # Configurație pentru simulare
            download_opts = create_robust_facebook_opts()
            download_opts.update({
                'outtmpl': os.path.join(temp_dir, '%(title).50s.%(ext)s'),
                'skip_download': False,
                'test': True,  # Simulare - nu descarcă efectiv
                'quiet': False
            })
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([url])
                    print(f"   ✅ SIMULARE REUȘITĂ")
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ SIMULARE EȘUATĂ: {error_msg[:80]}...")
                
                # Încearcă cu rotația
                print(f"   🔄 Încerc cu rotația...")
                try:
                    rotation_opts = download_opts.copy()
                    rotation_opts['skip_download'] = True
                    
                    success_url, info, rotation_info = try_facebook_with_rotation(
                        url, rotation_opts, max_attempts=3
                    )
                    
                    if success_url:
                        print(f"   ✅ ROTAȚIE GĂSIT URL FUNCȚIONAL: {rotation_info.get('successful_format', 'N/A')}")
                    else:
                        print(f"   ❌ ROTAȚIA A EȘUAT COMPLET")
                except Exception as rotation_error:
                    print(f"   ❌ EROARE ÎN ROTAȚIE: {str(rotation_error)[:60]}...")

def main():
    """Funcția principală de test"""
    print("🚀 FACEBOOK DEBUG TEST SCRIPT")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version}")
    print(f"📦 yt-dlp: {yt_dlp.version.__version__}")
    
    # URL-uri de test (înlocuiește cu URL-uri reale pentru testare)
    test_urls = [
        # Adaugă aici URL-uri Facebook pentru testare
        "https://www.facebook.com/share/v/EXAMPLE1/",  # Înlocuiește cu URL real
        "https://www.facebook.com/watch?v=EXAMPLE2",   # Înlocuiește cu URL real
        "https://www.facebook.com/reel/EXAMPLE3",      # Înlocuiește cu URL real
    ]
    
    print(f"\n🔗 URL-uri de test: {len(test_urls)}")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    if not any('EXAMPLE' not in url for url in test_urls):
        print("\n⚠️  ATENȚIE: Înlocuiește URL-urile EXAMPLE cu URL-uri Facebook reale!")
        print("   Editează fișierul și adaugă URL-uri de test în lista test_urls.")
        return
    
    try:
        # Rulează testele
        test_url_normalization(test_urls)
        test_info_extraction(test_urls)
        test_rotation_system(test_urls)
        test_download_simulation(test_urls)
        
        print("\n" + "="*60)
        print("✅ TESTE COMPLETE!")
        print("📋 Verifică log-urile pentru detalii complete.")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test oprit de utilizator")
    except Exception as e:
        print(f"\n\n❌ EROARE CRITICĂ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()