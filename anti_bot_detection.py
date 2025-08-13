#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modul avansat pentru evitarea sistemelor de blocare a botilor
Bazat pe documentația oficială yt-dlp și best practices pentru producție
"""

import random
import time
import logging
import os
import tempfile
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Configurații avansate pentru evitarea detecției bot
ANTI_BOT_CONFIGS = {
    'youtube': {
        'user_agents': [
            # Mobile clients - cel mai eficient pentru evitarea PO Token
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ],
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'tv_embedded'],  # Clienți care nu necesită PO Token
                'player_skip': ['webpage', 'configs'],  # Skip pentru evitarea PO Token
                'skip': [],  # Nu skip HLS
                'innertube_host': 'www.youtube.com',
                'innertube_key': None,  # Auto-detect
                'comment_sort': 'top',
                'max_comments': [0],  # Nu extrage comentarii
                'lang': ['en'],
                'region': 'US'
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            'extractor_retries': 3,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'http_chunk_size': 10485760
        }
    },
    'tiktok': {
        'user_agents': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ],
        'extractor_args': {
            'tiktok': {
                'webpage_download_timeout': 30,
                'api_hostname': 'api.tiktokv.com',
                'device_id': None,  # Auto-generate
                'app_version': '29.1.3'
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            'extractor_retries': 3,
            'sleep_interval': 2,
            'max_sleep_interval': 10,
            'http_chunk_size': 10485760
        }
    },
    'instagram': {
        'user_agents': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'extractor_args': {
            'instagram': {
                'api_version': 'v19.0',
                'include_stories': False,
                'include_highlights': False
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'extractor_retries': 2,
            'sleep_interval': 3,
            'max_sleep_interval': 15,
            'http_chunk_size': 10485760
        }
    },
    'facebook': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ],
        'extractor_args': {
            'facebook': {
                'api_version': 'v18.0',
                'legacy_ssl': True,
                'tab': 'videos',
                'android_client': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            'extractor_retries': 3,
            'sleep_interval': 5,
            'max_sleep_interval': 20,
            'http_chunk_size': 10485760
        }
    },
    'twitter': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ],
        'extractor_args': {
            'twitter': {
                'api_version': '2.0',
                'legacy_api': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'extractor_retries': 2,
            'sleep_interval': 2,
            'max_sleep_interval': 10,
            'http_chunk_size': 10485760
        }
    }
}

# Headers avansate pentru evitarea detecției
ADVANCED_HEADERS = {
    'desktop': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    },
    'mobile': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua-mobile': '?1'
    }
}

def get_platform_from_url(url: str) -> str:
    """Detectează platforma din URL"""
    url_lower = url.lower()
    
    if any(domain in url_lower for domain in ['youtube.com', 'youtu.be']):
        return 'youtube'
    elif any(domain in url_lower for domain in ['tiktok.com', 'vm.tiktok.com']):
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif any(domain in url_lower for domain in ['facebook.com', 'fb.watch', 'fb.me']):
        return 'facebook'
    elif any(domain in url_lower for domain in ['twitter.com', 'x.com']):
        return 'twitter'
    
    return 'generic'

def create_anti_bot_headers(platform: str, user_agent: str) -> Dict[str, str]:
    """Creează headers optimizate pentru evitarea detecției bot"""
    is_mobile = 'Mobile' in user_agent or 'iPhone' in user_agent or 'Android' in user_agent
    base_headers = ADVANCED_HEADERS['mobile' if is_mobile else 'desktop'].copy()
    
    base_headers['User-Agent'] = user_agent
    
    # Headers specifice platformei
    if platform == 'youtube':
        base_headers.update({
            'X-YouTube-Client-Name': '2',
            'X-YouTube-Client-Version': '2.20231214.01.00'
        })
    elif platform == 'tiktok':
        base_headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.tiktok.com/'
        })
    elif platform == 'instagram':
        base_headers.update({
            'X-Instagram-AJAX': '1',
            'X-Requested-With': 'XMLHttpRequest'
        })
    elif platform == 'facebook':
        base_headers.update({
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    return base_headers

def create_anti_bot_ydl_opts(url: str, temp_dir: str) -> Dict[str, Any]:
    """Creează opțiuni yt-dlp optimizate pentru evitarea detecției bot"""
    platform = get_platform_from_url(url)
    config = ANTI_BOT_CONFIGS.get(platform, ANTI_BOT_CONFIGS.get('youtube', {}))
    
    # Selectează user agent aleatoriu
    user_agent = random.choice(config.get('user_agents', [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]))
    
    # Creează headers anti-bot
    headers = create_anti_bot_headers(platform, user_agent)
    
    # Opțiuni de bază
    ydl_opts = {
        'format': 'best[filesize<45M][height<=720]/best[height<=720]/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'noplaylist': True,
        'extract_flat': False,
        'writethumbnail': False,
        'writeinfojson': False,
        'no_warnings': False,
        'ignoreerrors': False,
        'prefer_free_formats': False,
        'max_filesize': 50 * 1024 * 1024,  # 50MB
        'max_duration': 600,  # 10 minutes
        'http_headers': headers
    }
    
    # Adaugă configurații specifice platformei
    if config.get('ydl_opts'):
        ydl_opts.update(config['ydl_opts'])
    
    # Adaugă extractor args
    if config.get('extractor_args'):
        ydl_opts['extractor_args'] = config['extractor_args']
    
    return ydl_opts

def implement_rate_limiting(platform: str, last_request_time: Optional[float] = None) -> None:
    """Implementează rate limiting pentru evitarea detecției"""
    rate_limits = {
        'youtube': 2.0,    # 2 secunde între requests
        'tiktok': 3.0,     # 3 secunde
        'instagram': 4.0,  # 4 secunde
        'facebook': 5.0,   # 5 secunde
        'twitter': 3.0     # 3 secunde
    }
    
    min_delay = rate_limits.get(platform, 2.0)
    
    if last_request_time:
        elapsed = time.time() - last_request_time
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed + random.uniform(0.5, 1.5)  # Jitter
            logger.info(f"⏱️ Rate limiting: așteptare {sleep_time:.1f}s pentru {platform}")
            time.sleep(sleep_time)

def create_cache_dir() -> str:
    """Creează director cache pentru yt-dlp"""
    cache_dir = os.path.join(tempfile.gettempdir(), 'yt_dlp_cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def get_proxy_config() -> Optional[Dict[str, str]]:
    """Configurează proxy dacă este disponibil în variabilele de mediu"""
    proxy_url = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
    if proxy_url:
        return {
            'proxy': proxy_url,
            'source_address': None  # Lasă yt-dlp să aleagă
        }
    return None

def enhance_ydl_opts_for_production(ydl_opts: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Îmbunătățește opțiunile yt-dlp pentru producție"""
    # Adaugă cache directory
    ydl_opts['cachedir'] = create_cache_dir()
    
    # Adaugă proxy dacă este disponibil
    proxy_config = get_proxy_config()
    if proxy_config:
        ydl_opts.update(proxy_config)
        logger.info(f"🌐 Folosind proxy pentru {platform}")
    
    # Configurații suplimentare pentru producție
    production_opts = {
        'writesubtitles': False,
        'writeautomaticsub': False,
        'subtitleslangs': [],
        'keepvideo': False,
        'embed_subs': False,
        'embed_thumbnail': False,
        'add_metadata': False,
        'writeinfojson': False,
        'writedescription': False,
        'writeannotations': False,
        'writecomments': False,
        'getcomments': False
    }
    
    ydl_opts.update(production_opts)
    
    return ydl_opts

def log_anti_bot_status(platform: str, success: bool, attempt: int, error: str = None) -> None:
    """Loghează statusul anti-bot detection"""
    if success:
        logger.info(f"✅ Anti-bot bypass reușit pentru {platform} la încercarea {attempt}")
    else:
        logger.warning(f"❌ Anti-bot bypass eșuat pentru {platform} la încercarea {attempt}: {error}")

# Export funcții principale
__all__ = [
    'create_anti_bot_ydl_opts',
    'implement_rate_limiting', 
    'enhance_ydl_opts_for_production',
    'log_anti_bot_status',
    'get_platform_from_url'
]