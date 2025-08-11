
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
