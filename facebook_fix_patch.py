
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

def generate_facebook_url_variants(url):
    """Generează variante alternative ale URL-ului Facebook pentru rotare"""
    if not url or 'facebook.com' not in url:
        return [url]
    
    variants = [url]  # URL-ul original
    
    # Extrage ID-ul video din diferite formate
    video_id = None
    
    # Pattern pentru share/v/
    share_match = re.search(r'facebook\.com/share/v/([^/?]+)', url)
    if share_match:
        video_id = share_match.group(1)
    
    # Pattern pentru watch?v=
    watch_match = re.search(r'facebook\.com/watch\?v=([^&]+)', url)
    if watch_match:
        video_id = watch_match.group(1)
    
    # Pattern pentru reel/
    reel_match = re.search(r'facebook\.com/reel/([^/?]+)', url)
    if reel_match:
        video_id = reel_match.group(1)
    
    # Pattern pentru video ID în URL-uri complexe
    complex_match = re.search(r'[?&]v=([^&]+)', url)
    if complex_match:
        video_id = complex_match.group(1)
    
    if video_id:
        # Generează toate variantele posibile
        base_variants = [
            f"https://www.facebook.com/watch?v={video_id}",
            f"https://facebook.com/watch?v={video_id}", 
            f"https://www.facebook.com/share/v/{video_id}/",
            f"https://facebook.com/share/v/{video_id}/",
            f"https://www.facebook.com/reel/{video_id}",
            f"https://facebook.com/reel/{video_id}",
            f"https://m.facebook.com/watch?v={video_id}",
            f"https://mobile.facebook.com/watch?v={video_id}"
        ]
        
        # Adaugă variantele care nu sunt deja în listă
        for variant in base_variants:
            if variant not in variants:
                variants.append(variant)
    
    logger.info(f"Generated {len(variants)} Facebook URL variants for rotation")
    return variants

def try_facebook_with_rotation(url, ydl_opts, max_attempts=3):
    """Încearcă descărcarea Facebook cu rotarea URL-urilor"""
    variants = generate_facebook_url_variants(url)
    logger.info(f"🔄 Începe rotația Facebook cu {len(variants)} variante URL disponibile")
    
    attempted_formats = []
    last_error = None
    
    for attempt, variant_url in enumerate(variants[:max_attempts], 1):
        # Determină tipul de format pentru logging
        if 'watch?v=' in variant_url:
            format_type = "watch format"
        elif 'share/v/' in variant_url:
            format_type = "share format"
        elif 'reel/' in variant_url:
            format_type = "reel format"
        elif 'm.facebook.com' in variant_url:
            format_type = "mobile format"
        else:
            format_type = "unknown format"
            
        attempted_formats.append(format_type)
        logger.info(f"🔄 Încercare {attempt}/{max_attempts}: {format_type} - {variant_url[:60]}...")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Încearcă să extragă informațiile
                info = ydl.extract_info(variant_url, download=False)
                if info:
                    logger.info(f"✅ SUCCES! Facebook rotation reușită la încercarea {attempt} cu {format_type}")
                    logger.info(f"📹 Video găsit: {info.get('title', 'N/A')[:50]}...")
                    return variant_url, info, {
                        'successful_format': format_type,
                        'attempt_number': attempt,
                        'attempted_formats': attempted_formats
                    }
        except Exception as e:
            error_msg = str(e).lower()
            last_error = str(e)
            logger.warning(f"❌ {format_type} eșuat: {error_msg[:80]}...")
            
            # Dacă e o eroare critică, nu mai încerca
            if any(keyword in error_msg for keyword in ['private', 'not available', 'unavailable', 'deleted']):
                logger.info(f"🛑 Oprire rotație din cauza erorii critice: conținut privat/indisponibil")
                return None, None, {
                    'error_type': 'critical',
                    'error_message': last_error,
                    'attempted_formats': attempted_formats,
                    'stopped_at_attempt': attempt
                }
            
            continue
    
    logger.error(f"❌ Facebook rotation eșuată după {len(variants[:max_attempts])} încercări")
    logger.error(f"📋 Formate încercate: {', '.join(attempted_formats)}")
    return None, None, {
        'error_type': 'all_failed',
        'error_message': last_error,
        'attempted_formats': attempted_formats,
        'total_attempts': len(variants[:max_attempts])
    }

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
    'create_robust_facebook_opts',
    'generate_facebook_url_variants',
    'try_facebook_with_rotation'
]
