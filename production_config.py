#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuratii pentru productie - evitarea sistemelor de blocare
Bazat pe documentația yt-dlp și best practices pentru deployment
"""

import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Configurații pentru proxy-uri (opțional)
PROXY_CONFIGS = {
    'residential_proxies': [
        # Adaugă proxy-uri rezidențiale aici dacă sunt disponibile
        # Format: 'http://username:password@proxy-server:port'
    ],
    'datacenter_proxies': [
        # Adaugă proxy-uri datacenter aici dacă sunt disponibile
    ],
    'free_proxies': [
        # Proxy-uri gratuite (nu recomandate pentru producție)
    ]
}

# Configurații pentru cookies (pentru platforme care necesită autentificare)
COOKIE_CONFIGS = {
    'youtube': {
        'cookie_file': os.environ.get('YOUTUBE_COOKIES_FILE'),
        'required': False,  # YouTube funcționează fără cookies cu clientul mweb
        'description': 'Cookies pentru YouTube (opțional pentru evitarea PO Token)'
    },
    'instagram': {
        'cookie_file': os.environ.get('INSTAGRAM_COOKIES_FILE'),
        'required': False,  # Instagram public content nu necesită cookies
        'description': 'Cookies pentru Instagram (pentru conținut privat)'
    },
    'facebook': {
        'cookie_file': os.environ.get('FACEBOOK_COOKIES_FILE'),
        'required': False,  # Facebook public videos nu necesită cookies
        'description': 'Cookies pentru Facebook (pentru conținut privat)'
    },
    'twitter': {
        'cookie_file': os.environ.get('TWITTER_COOKIES_FILE'),
        'required': False,  # Twitter public content nu necesită cookies
        'description': 'Cookies pentru Twitter/X (pentru conținut privat)'
    }
}

# Configurații pentru rate limiting în producție
PRODUCTION_RATE_LIMITS = {
    'youtube': {
        'requests_per_minute': 30,
        'burst_limit': 5,
        'cooldown_period': 60,  # secunde
        'backoff_multiplier': 1.5
    },
    'tiktok': {
        'requests_per_minute': 20,
        'burst_limit': 3,
        'cooldown_period': 90,
        'backoff_multiplier': 2.0
    },
    'instagram': {
        'requests_per_minute': 15,
        'burst_limit': 2,
        'cooldown_period': 120,
        'backoff_multiplier': 2.5
    },
    'facebook': {
        'requests_per_minute': 10,
        'burst_limit': 2,
        'cooldown_period': 180,
        'backoff_multiplier': 3.0
    },
    'twitter': {
        'requests_per_minute': 25,
        'burst_limit': 4,
        'cooldown_period': 75,
        'backoff_multiplier': 1.8
    }
}

# Configurații pentru monitoring și alerting
MONITORING_CONFIG = {
    'enable_metrics': True,
    'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
    'alert_on_high_failure_rate': True,
    'failure_rate_threshold': 0.7,  # 70% failure rate
    'alert_webhook': os.environ.get('ALERT_WEBHOOK_URL'),
    'metrics_endpoint': '/metrics',
    'health_endpoint': '/health'
}

# Configurații pentru cache și optimizare
CACHE_CONFIG = {
    'enable_cache': True,
    'cache_ttl': 3600,  # 1 oră
    'max_cache_size': 100,  # MB
    'cache_cleanup_interval': 1800,  # 30 minute
    'cache_directory': os.environ.get('CACHE_DIR', '/tmp/yt_dlp_cache')
}

# Configurații pentru retry și resilience
RESILIENCE_CONFIG = {
    'max_retries': 3,
    'retry_delay_base': 2,  # secunde
    'retry_delay_max': 60,  # secunde
    'circuit_breaker_threshold': 5,  # eșecuri consecutive
    'circuit_breaker_timeout': 300,  # 5 minute
    'enable_fallback_extractors': True
}

# Configurații pentru securitate
SECURITY_CONFIG = {
    'enable_ssl_verification': True,
    'max_file_size': 50 * 1024 * 1024,  # 50MB
    'allowed_domains': [
        'youtube.com', 'youtu.be', 'tiktok.com', 'vm.tiktok.com',
        'instagram.com', 'facebook.com', 'fb.watch', 'fb.me',
        'twitter.com', 'x.com', 'vimeo.com', 'dailymotion.com',
        'pinterest.com', 'pin.it', 'threads.net', 'reddit.com',
        'redd.it', 'v.redd.it'
    ],
    'blocked_file_types': ['.exe', '.bat', '.sh', '.scr', '.com'],
    'scan_downloads': False,  # Activează doar dacă ai antivirus API
    'quarantine_suspicious': True
}

def get_proxy_for_platform(platform: str) -> Optional[str]:
    """Returnează proxy optim pentru platformă"""
    # Verifică variabilele de mediu pentru proxy-uri specifice
    platform_proxy = os.environ.get(f'{platform.upper()}_PROXY')
    if platform_proxy:
        return platform_proxy
    
    # Proxy general
    general_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
    if general_proxy:
        return general_proxy
    
    # Proxy-uri configurate
    if PROXY_CONFIGS['residential_proxies']:
        import random
        return random.choice(PROXY_CONFIGS['residential_proxies'])
    
    return None

def get_cookies_for_platform(platform: str) -> Optional[str]:
    """Returnează calea către fișierul de cookies pentru platformă"""
    config = COOKIE_CONFIGS.get(platform, {})
    cookie_file = config.get('cookie_file')
    
    if cookie_file and os.path.exists(cookie_file):
        logger.info(f"🍪 Folosind cookies pentru {platform}: {cookie_file}")
        return cookie_file
    
    if config.get('required'):
        logger.warning(f"⚠️ Cookies necesare pentru {platform} dar nu sunt disponibile")
    
    return None

def get_rate_limit_config(platform: str) -> Dict[str, Any]:
    """Returnează configurația de rate limiting pentru platformă"""
    return PRODUCTION_RATE_LIMITS.get(platform, {
        'requests_per_minute': 20,
        'burst_limit': 3,
        'cooldown_period': 60,
        'backoff_multiplier': 2.0
    })

def is_production_environment() -> bool:
    """Verifică dacă rulează în mediul de producție"""
    return os.environ.get('ENVIRONMENT', '').lower() in ['production', 'prod']

def get_user_agent_pool(platform: str) -> List[str]:
    """Returnează pool de user agents pentru platformă"""
    # User agents actualizați pentru 2024
    user_agents = {
        'youtube': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'
        ],
        'tiktok': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0',
            'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'
        ],
        'instagram': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ],
        'facebook': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ],
        'twitter': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ]
    }
    
    return user_agents.get(platform, [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    ])

def validate_url_security(url: str) -> bool:
    """Validează securitatea URL-ului"""
    url_lower = url.lower()
    
    # Verifică domenii permise
    allowed = any(domain in url_lower for domain in SECURITY_CONFIG['allowed_domains'])
    if not allowed:
        logger.warning(f"🚫 Domeniu nepermis: {url}")
        return False
    
    # Verifică scheme permise
    if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
        logger.warning(f"🚫 Schemă nepermisă: {url}")
        return False
    
    return True

def get_production_ydl_opts_enhancement() -> Dict[str, Any]:
    """Returnează îmbunătățiri specifice pentru producție"""
    opts = {
        'socket_timeout': 30,
        'retries': RESILIENCE_CONFIG['max_retries'],
        'fragment_retries': RESILIENCE_CONFIG['max_retries'],
        'extractor_retries': RESILIENCE_CONFIG['max_retries'],
        'sleep_interval': RESILIENCE_CONFIG['retry_delay_base'],
        'max_sleep_interval': RESILIENCE_CONFIG['retry_delay_max'],
        'nocheckcertificate': not SECURITY_CONFIG['enable_ssl_verification'],
        'max_filesize': SECURITY_CONFIG['max_file_size']
    }
    
    # Adaugă cache dacă este activat
    if CACHE_CONFIG['enable_cache']:
        opts['cachedir'] = CACHE_CONFIG['cache_directory']
    
    return opts

def log_production_metrics(platform: str, success: bool, duration: float, file_size: int = 0):
    """Loghează metrici pentru monitoring în producție"""
    if not MONITORING_CONFIG['enable_metrics']:
        return
    
    metrics = {
        'platform': platform,
        'success': success,
        'duration_seconds': duration,
        'file_size_bytes': file_size,
        'timestamp': time.time()
    }
    
    # În producție, aceste metrici ar fi trimise către un sistem de monitoring
    logger.info(f"📊 Metrics: {metrics}")

# Export configurații principale
__all__ = [
    'get_proxy_for_platform',
    'get_cookies_for_platform', 
    'get_rate_limit_config',
    'is_production_environment',
    'get_user_agent_pool',
    'validate_url_security',
    'get_production_ydl_opts_enhancement',
    'log_production_metrics',
    'MONITORING_CONFIG',
    'SECURITY_CONFIG',
    'RESILIENCE_CONFIG'
]