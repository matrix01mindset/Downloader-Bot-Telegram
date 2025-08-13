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
            # Mobile Safari - cel mai eficient pentru TikTok
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            # Android Chrome Mobile
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
            # Desktop fallback cu mobile viewport
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'extractor_args': {
            'tiktok': {
                'webpage_download_timeout': 45,
                'api_hostname': 'api.tiktokv.com',
                'device_id': None,  # Auto-generate
                'app_version': '29.1.3',
                # Configurații pentru evitarea blocării IP
                'use_mobile_ua': True,
                'bypass_geo_restriction': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': ['US', 'SG', 'JP', 'CA', 'GB'],  # Multiple țări pentru bypass
            'nocheckcertificate': True,
            'socket_timeout': 45,  # Timeout mai mare pentru TikTok
            'retries': 8,  # Mai multe încercări
            'fragment_retries': 8,
            'extractor_retries': 5,
            'sleep_interval': 3,  # Pauză mai mare între încercări
            'max_sleep_interval': 15,
            'http_chunk_size': 10485760,
            # Configurații avansate pentru evitarea blocării
            'prefer_insecure': False,
            'call_home': False,
            'no_check_certificate': True
        }
    },
    'instagram': {
        'user_agents': [
            # Instagram mobile app user agents
            'Instagram 302.0.0.23.103 Android (33/13; 420dpi; 1080x2400; samsung; SM-G998B; t2s; qcom; ro_RO; 512200115)',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ],
        'extractor_args': {
            'instagram': {
                'api_version': 'v1',
                'include_stories': False,
                # Configurații pentru evitarea autentificării
                'use_mobile_ua': True,
                'bypass_login': True,
                'extract_flat': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': ['US', 'CA', 'GB'],
            'nocheckcertificate': True,
            'socket_timeout': 45,  # Timeout mai mare
            'retries': 6,  # Mai multe încercări
            'fragment_retries': 6,
            'extractor_retries': 4,
            'sleep_interval': 5,  # Pauză mai mare pentru Instagram
            'max_sleep_interval': 20,
            'http_chunk_size': 10485760
        }
    },
    'facebook': {
        'user_agents': [
            # Facebook mobile app user agents
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBDV/iPhone15,3;FBMD/iPhone;FBSN/iOS;FBSV/17.2.1;FBSS/3;FBID/phone;FBLC/en_US;FBOP/5]',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/442.0.0.39.118;]',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'extractor_args': {
            'facebook': {
                # Configurații pentru evitarea blocării
                'use_mobile_ua': True,
                'bypass_geo_restriction': True,
                'extract_flat': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': ['US', 'CA', 'GB'],
            'nocheckcertificate': True,
            'socket_timeout': 45,
            'retries': 8,  # Mai multe încercări pentru Facebook
            'fragment_retries': 8,
            'extractor_retries': 5,
            'sleep_interval': 7,  # Pauză mai mare
            'max_sleep_interval': 25,
            'http_chunk_size': 10485760
        }
    },
    'twitter': {
        'user_agents': [
            # Twitter/X mobile app user agents
            'TwitterAndroid/10.21.0-release.0 (30210000-r-0) ONEPLUS+A6000/9 (OnePlus;ONEPLUS+A6000;OnePlus;OnePlus6;0;;1;2018)',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ],
        'extractor_args': {
            'twitter': {
                # Configurații pentru evitarea autentificării
                'use_mobile_ua': True,
                'bypass_login': True,
                'extract_flat': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': ['US', 'CA', 'GB'],
            'nocheckcertificate': True,
            'socket_timeout': 45,
            'retries': 6,
            'fragment_retries': 6,
            'extractor_retries': 4,
            'sleep_interval': 4,
            'max_sleep_interval': 15,
            'http_chunk_size': 10485760
        }
    },
    'vimeo': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ],
        'extractor_args': {
            'vimeo': {
                'player_url': None,  # Auto-detect
                'referer': 'https://vimeo.com/',
                'use_original_url': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': ['US', 'CA', 'GB', 'DE', 'FR'],
            'nocheckcertificate': True,
            'socket_timeout': 60,
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 6,
            'sleep_interval': 2,
            'max_sleep_interval': 8,
            'http_chunk_size': 10485760,
            # Configurații speciale pentru Vimeo TLS fingerprinting
            'prefer_insecure': True,  # Folosește HTTP când este posibil
            'call_home': False,
            'source_address': None,  # Permite auto-detect IP
            'force_ipv4': True  # Forțează IPv4
        }
    },
    'dailymotion': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ],
        'extractor_args': {
            'dailymotion': {
                'family_filter': False,
                'geo_bypass': True
            }
        },
        'ydl_opts': {
            'geo_bypass': True,
            'geo_bypass_country': ['US', 'FR', 'CA', 'GB'],
            'nocheckcertificate': True,
            'socket_timeout': 45,
            'retries': 6,
            'fragment_retries': 6,
            'extractor_retries': 4,
            'sleep_interval': 2,
            'max_sleep_interval': 10,
            'http_chunk_size': 10485760
        }
    }
}

# Lista de proxy-uri gratuite pentru testare (doar pentru dezvoltare)
FREE_PROXIES = [
    # Acestea sunt doar pentru testare - în producție folosește proxy-uri premium
    'socks5://127.0.0.1:1080',
    'http://proxy.example.com:8080',
    # Adaugă proxy-uri reale aici
]

# Rate limiting pentru fiecare platformă
RATE_LIMITS = {
    'youtube': 1.0,      # 1 secundă între cereri
    'tiktok': 3.0,       # 3 secunde pentru TikTok (mai strict)
    'instagram': 5.0,    # 5 secunde pentru Instagram
    'facebook': 7.0,     # 7 secunde pentru Facebook
    'twitter': 4.0,      # 4 secunde pentru Twitter
    'vimeo': 2.0,        # 2 secunde pentru Vimeo
    'dailymotion': 2.0,  # 2 secunde pentru Dailymotion
    'default': 2.0       # Default pentru alte platforme
}

# Tracking pentru rate limiting
last_request_time = {}

def get_platform_from_url(url: str) -> str:
    """
    Detectează platforma din URL
    """
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'facebook'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    elif 'dailymotion.com' in url_lower:
        return 'dailymotion'
    else:
        return 'unknown'

def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Obține configurația proxy din variabilele de mediu sau proxy rotation
    """
    # Încearcă să obțină proxy din variabilele de mediu
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
    socks_proxy = os.getenv('SOCKS_PROXY') or os.getenv('socks_proxy')
    
    if http_proxy or https_proxy or socks_proxy:
        proxy_config = {}
        if http_proxy:
            proxy_config['http'] = http_proxy
        if https_proxy:
            proxy_config['https'] = https_proxy
        if socks_proxy:
            proxy_config['socks'] = socks_proxy
        return proxy_config
    
    # Proxy rotation pentru testare (doar dacă este activat)
    use_proxy_rotation = os.getenv('USE_PROXY_ROTATION', 'false').lower() == 'true'
    if use_proxy_rotation and FREE_PROXIES:
        selected_proxy = random.choice(FREE_PROXIES)
        logger.info(f"Folosesc proxy rotation: {selected_proxy}")
        
        if selected_proxy.startswith('socks'):
            return {'socks': selected_proxy}
        else:
            return {'http': selected_proxy, 'https': selected_proxy}
    
    return None

def implement_rate_limiting(platform: str) -> None:
    """
    Implementează rate limiting pentru platformă
    """
    global last_request_time
    
    current_time = time.time()
    rate_limit = RATE_LIMITS.get(platform, RATE_LIMITS['default'])
    
    if platform in last_request_time:
        time_since_last = current_time - last_request_time[platform]
        if time_since_last < rate_limit:
            sleep_time = rate_limit - time_since_last
            logger.info(f"Rate limiting pentru {platform}: aștept {sleep_time:.2f}s")
            time.sleep(sleep_time)
    
    last_request_time[platform] = time.time()

def create_anti_bot_ydl_opts(url: str) -> Dict[str, Any]:
    """
    Creează opțiuni yt-dlp optimizate pentru evitarea detecției bot
    """
    platform = get_platform_from_url(url)
    
    if platform == 'unknown':
        logger.warning(f"Platformă necunoscută pentru URL: {url}")
        platform = 'youtube'  # Fallback la YouTube
    
    config = ANTI_BOT_CONFIGS.get(platform, ANTI_BOT_CONFIGS['youtube'])
    
    # Selectează un user agent aleatoriu
    user_agent = random.choice(config['user_agents'])
    
    # Configurații de bază
    ydl_opts = {
        'format': 'best[height<=720]/best',  # Limitează calitatea pentru viteză
        'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writethumbnail': False,
        'writeinfojson': False,
        'writedescription': False,
        'writecomments': False,
        'writeannotations': False,
        'ignoreerrors': True,
        'no_warnings': True,
        'quiet': True,
        'http_headers': {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    }
    
    # Adaugă configurațiile specifice platformei
    if 'ydl_opts' in config:
        ydl_opts.update(config['ydl_opts'])
    
    # Adaugă extractor_args dacă există
    if 'extractor_args' in config:
        ydl_opts['extractor_args'] = config['extractor_args']
    
    # Adaugă configurația proxy dacă este disponibilă
    proxy_config = get_proxy_config()
    if proxy_config:
        ydl_opts['proxy'] = proxy_config.get('http') or proxy_config.get('https') or proxy_config.get('socks')
        logger.info(f"Folosesc proxy pentru {platform}: {ydl_opts['proxy']}")
    
    logger.info(f"Configurații anti-bot create pentru {platform}")
    logger.debug(f"User-Agent: {user_agent}")
    
    return ydl_opts

def enhance_ydl_opts_for_production(ydl_opts: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """
    Îmbunătățește opțiunile yt-dlp pentru producție cu configurații avansate anti-bot
    """
    enhanced_opts = ydl_opts.copy()
    
    # Configurații avansate pentru producție
    production_enhancements = {
        # Previne trimiterea de date către yt-dlp
        'call_home': False,
        'check_formats': None,
        
        # Optimizări pentru playlist-uri
        'extract_flat': False,
        'lazy_playlist': True,
        'playlist_items': '1',  # Doar primul item din playlist
        
        # Evită rate limiting
        'sleep_interval_requests': 1,
        'sleep_interval_subtitles': 1,
        
        # Îmbunătățiri pentru stabilitate
        'abort_on_unavailable_fragment': False,
        'keep_fragments': False,
        'buffersize': 1024 * 1024,  # 1MB buffer
        
        # Bypass geo-restrictions
        'geo_verification_proxy': None,
        
        # Previne fingerprinting
        'http_chunk_size': 10485760,  # 10MB chunks
        'prefer_free_formats': True,
        'youtube_include_dash_manifest': False,
    }
    
    # Configurații specifice platformei
    if platform == 'tiktok':
        production_enhancements.update({
            'extractor_retries': 8,
            'sleep_interval': 5,  # Mai mult timp între încercări
            'socket_timeout': 60,
        })
    elif platform == 'instagram':
        production_enhancements.update({
            'extractor_retries': 6,
            'sleep_interval': 8,  # Mult timp pentru Instagram
            'socket_timeout': 45,
        })
    elif platform == 'facebook':
        production_enhancements.update({
            'extractor_retries': 10,
            'sleep_interval': 10,  # Foarte mult timp pentru Facebook
            'socket_timeout': 60,
        })
    elif platform == 'vimeo':
        production_enhancements.update({
            'prefer_insecure': True,
            'force_ipv4': True,
            'source_address': None,
        })
    
    enhanced_opts.update(production_enhancements)
    
    logger.info(f"Opțiuni îmbunătățite pentru producție: {platform}")
    return enhanced_opts

def log_anti_bot_status(platform: str, success: bool, message: str = "") -> None:
    """
    Loghează statusul sistemului anti-bot
    """
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"ANTI-BOT [{platform.upper()}] {status}: {message}")
    
    # În producție, poți adăuga aici metrici sau alerting
    if not success:
        logger.warning(f"Platformă blocată detectată: {platform} - {message}")

def get_anti_bot_summary() -> Dict[str, Any]:
    """
    Returnează un sumar al configurațiilor anti-bot disponibile
    """
    return {
        'platforms_supported': list(ANTI_BOT_CONFIGS.keys()),
        'total_user_agents': sum(len(config['user_agents']) for config in ANTI_BOT_CONFIGS.values()),
        'proxy_enabled': get_proxy_config() is not None,
        'rate_limiting_enabled': True,
        'production_ready': True
    }