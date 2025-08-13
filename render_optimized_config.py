#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuração otimizada para ambiente Render
Optimizações específicas para servidor Render com foco em estabilidade e performance
"""

import os
import logging
from typing import Dict, List, Any

# Configurações específicas para ambiente Render
RENDER_OPTIMIZED_CONFIG = {
    # Configurações de rede otimizadas para Render
    'network': {
        'timeout': 45,  # Timeout maior para conexões lentas
        'retries': 5,   # Mais tentativas
        'backoff_factor': 2.0,
        'max_redirects': 10,
        'verify_ssl': True,
        'pool_connections': 10,
        'pool_maxsize': 20
    },
    
    # Headers otimizados para bypass anti-bot
    'headers': {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    },
    
    # Configurații yt-dlp otimizate pentru Render
    'ytdl_opts': {
        'format': 'best[height<=720]/best',  # Qualitate moderată pentru velocidade
        'outtmpl': '/tmp/%(title)s.%(ext)s',  # Usar /tmp no Render
        'writesubtitles': False,
        'writeautomaticsub': False,
        'ignoreerrors': True,
        'no_warnings': True,
        'extractaudio': False,
        'audioformat': 'mp3',
        'audioquality': '192',
    },
    
    # Configurații Flask pentru Render
    'flask_config': {
        'DEBUG': False,
        'TESTING': False,
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'render-production-key'),
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
        'SEND_FILE_MAX_AGE_DEFAULT': 31536000,  # 1 an cache
        'JSONIFY_PRETTYPRINT_REGULAR': False,
        'JSON_SORT_KEYS': False
    },
    
    # Configurații de socket pentru yt-dlp
    'socket_config': {
        'socket_timeout': 45,
        'retries': 5,
        'fragment_retries': 5,
        'skip_unavailable_fragments': True,
        'keep_fragments': False,
        'buffersize': 1024 * 16,  # 16KB buffer
        'http_chunk_size': 1024 * 1024,  # 1MB chunks
        'concurrent_fragment_downloads': 1,  # Evitar sobrecarga
        'throttledratelimit': None,
        'noplaylist': True,
        'cookiefile': None,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'prefer_insecure': False,
        'call_home': False,
        'verbose': False,
        'dump_single_json': False,
        'simulate': False,
        'skip_download': False,
        'cachedir': '/tmp/yt-dlp-cache',
        'rm_cachedir': True
    },
    
    # Configurações específicas por platformă pentru Render
    'platforms': {
        'youtube': {
            'enabled': True,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs', 'webpage']
                }
            },
            'format_selector': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'max_filesize': 45 * 1024 * 1024,  # 45MB
            'rate_limit': '2M'  # 2MB/s rate limit
        },
        
        'tiktok': {
            'enabled': True,
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api.tiktokv.com',
                    'webpage_url': True
                }
            },
            'format_selector': 'best[height<=720]/best',
            'max_filesize': 45 * 1024 * 1024,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Referer': 'https://www.tiktok.com/'
            }
        },
        
        'instagram': {
            'enabled': True,
            'extractor_args': {
                'instagram': {
                    'api_hostname': 'i.instagram.com'
                }
            },
            'format_selector': 'best[height<=720]/best',
            'max_filesize': 45 * 1024 * 1024,
            'headers': {
                'User-Agent': 'Instagram 219.0.0.12.117 Android',
                'X-IG-App-ID': '936619743392459'
            }
        },
        
        'facebook': {
            'enabled': True,
            'extractor_args': {
                'facebook': {
                    'api_hostname': 'graph.facebook.com'
                }
            },
            'format_selector': 'best[height<=720]/best',
            'max_filesize': 45 * 1024 * 1024,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        },
        
        'twitter': {
            'enabled': True,
            'extractor_args': {
                'twitter': {
                    'api_hostname': 'api.twitter.com'
                }
            },
            'format_selector': 'best[height<=720]/best',
            'max_filesize': 45 * 1024 * 1024,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
            }
        },
        
        'vimeo': {
            'enabled': True,
            'format_selector': 'best[height<=720]/best',
            'max_filesize': 45 * 1024 * 1024
        },
        
        'dailymotion': {
            'enabled': True,
            'format_selector': 'best[height<=720]/best',
            'max_filesize': 45 * 1024 * 1024
        }
    },
    
    # Configurações de proxy para Render (usar proxies gratuitos)
    'proxy_config': {
        'enabled': True,
        'rotation_enabled': True,
        'free_proxies': [
            'http://proxy-server.com:8080',
            'http://free-proxy.cz:8080',
            'http://proxy.rudnkh.me:8080'
        ],
        'proxy_timeout': 30,
        'max_retries_per_proxy': 2
    },
    
    # Rate limiting pentru Render
    'rate_limiting': {
        'enabled': True,
        'requests_per_minute': {
            'youtube': 10,
            'tiktok': 8,
            'instagram': 6,
            'facebook': 6,
            'twitter': 8,
            'vimeo': 10,
            'dailymotion': 10
        },
        'cooldown_seconds': 3
    },
    
    # Configurações de logging para Render
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_enabled': False,  # Não usar fișiere pe Render
        'console_enabled': True
    },
    
    # Configurações de memória para Render
    'memory': {
        'max_cache_size': 50 * 1024 * 1024,  # 50MB cache
        'cleanup_interval': 300,  # 5 minute
        'temp_dir': '/tmp',
        'auto_cleanup': True
    },
    
    # Configurações de segurança pentru Render
    'security': {
        'max_file_size': 45 * 1024 * 1024,  # 45MB
        'allowed_extensions': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mp3', '.m4a'],
        'scan_downloads': True,
        'quarantine_suspicious': True
    }
}

# Funcții de configurare pentru Render
def get_render_ytdl_opts(platform: str = None) -> Dict[str, Any]:
    """Returnează opțiuni yt-dlp optimizate pentru Render"""
    base_opts = RENDER_OPTIMIZED_CONFIG['ytdl_opts'].copy()
    
    if platform and platform in RENDER_OPTIMIZED_CONFIG['platforms']:
        platform_config = RENDER_OPTIMIZED_CONFIG['platforms'][platform]
        
        # Adaugă configurări specifice platformei
        if 'extractor_args' in platform_config:
            base_opts['extractor_args'] = platform_config['extractor_args']
        
        if 'format_selector' in platform_config:
            base_opts['format'] = platform_config['format_selector']
        
        if 'headers' in platform_config:
            base_opts['http_headers'] = platform_config['headers']
        
        if 'max_filesize' in platform_config:
            base_opts['max_filesize'] = platform_config['max_filesize']
    
    return base_opts

def get_render_headers(platform: str = None) -> Dict[str, str]:
    """Returnează headers optimizate pentru Render"""
    base_headers = RENDER_OPTIMIZED_CONFIG['headers'].copy()
    
    if platform and platform in RENDER_OPTIMIZED_CONFIG['platforms']:
        platform_headers = RENDER_OPTIMIZED_CONFIG['platforms'][platform].get('headers', {})
        base_headers.update(platform_headers)
    
    return base_headers

def setup_render_logging():
    """Configurează logging pentru mediul Render"""
    log_config = RENDER_OPTIMIZED_CONFIG['logging']
    
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format=log_config['format'],
        handlers=[
            logging.StreamHandler()  # Doar console pe Render
        ]
    )
    
    # Reduce logging pentru biblioteci externe
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('yt_dlp').setLevel(logging.WARNING)

def is_render_environment() -> bool:
    """Verifică dacă rulează în mediul Render"""
    return (
        os.getenv('RENDER') == 'true' or
        os.getenv('RENDER_SERVICE_ID') is not None or
        'render.com' in os.getenv('RENDER_EXTERNAL_URL', '')
    )

def get_render_temp_dir() -> str:
    """Returnează directorul temporar pentru Render"""
    if is_render_environment():
        return '/tmp'
    return os.path.join(os.getcwd(), 'temp_downloads')

def cleanup_render_temp_files():
    """Curăță fișierele temporare în mediul Render"""
    import glob
    import time
    
    temp_dir = get_render_temp_dir()
    if not os.path.exists(temp_dir):
        return
    
    # Șterge fișiere mai vechi de 10 minute
    current_time = time.time()
    for file_path in glob.glob(os.path.join(temp_dir, '*')):
        try:
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > 600:  # 10 minute
                    os.remove(file_path)
                    logging.info(f"Șters fișier temporar vechi: {file_path}")
        except Exception as e:
            logging.warning(f"Eroare la ștergerea fișierului {file_path}: {e}")

# Configurare automată pentru Render
if is_render_environment():
    setup_render_logging()
    logging.info("Configurație Render activată")
    
    # Cleanup periodic
    import threading
    import time
    
    def periodic_cleanup():
        while True:
            time.sleep(300)  # 5 minute
            cleanup_render_temp_files()
    
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()