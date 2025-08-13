import yt_dlp
import os
import tempfile
import time
import glob
import re
import unicodedata
import random
import json
import logging
import subprocess
import sys
import shutil
import requests
from datetime import datetime, timedelta
from anti_bot_detection import (
    create_anti_bot_ydl_opts,
    implement_rate_limiting,
    enhance_ydl_opts_for_production,
    log_anti_bot_status,
    get_platform_from_url as get_platform_anti_bot
)
from production_config import (
    get_proxy_for_platform,
    get_cookies_for_platform,
    get_rate_limit_config,
    is_production_environment,
    validate_url_security,
    get_production_ydl_opts_enhancement,
    log_production_metrics
)
from render_optimized_config import (
    get_render_ytdl_opts,
    get_render_headers,
    is_render_environment,
    get_render_temp_dir,
    cleanup_render_temp_files,
    RENDER_OPTIMIZED_CONFIG
)

# Configurare logging centralizat
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce logging-ul pentru yt-dlp și alte biblioteci externe
logging.getLogger('yt_dlp').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Funcție pentru upgrade automat la versiunea nightly de yt-dlp
def upgrade_to_nightly_ytdlp():
    """Upgrade yt-dlp la versiunea nightly pentru fix-uri Facebook recente"""
    try:
        logger.info("Verificare și upgrade la yt-dlp nightly pentru fix-uri Facebook...")
        # Încercare upgrade la nightly folosind --pre flag (metoda recomandată)
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-U', '--pre', 'yt-dlp[default]'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info("yt-dlp upgraded cu succes la versiunea nightly")
            return True
        else:
            logger.warning(f"Upgrade la nightly eșuat, încercare versiune stabilă: {result.stderr}")
            # Fallback la versiunea stabilă cu extras
            result2 = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp[default]'
            ], capture_output=True, text=True, timeout=90)
            
            if result2.returncode == 0:
                logger.info("yt-dlp upgraded cu succes la versiunea stabilă cu extras")
                return True
            else:
                logger.warning(f"Upgrade yt-dlp eșuat complet: {result2.stderr}")
                return False
    except Exception as e:
        logger.error(f"Eroare la upgrade yt-dlp: {e}")
        return False

# Încercare upgrade la nightly la startup (doar o dată)
try:
    if not hasattr(upgrade_to_nightly_ytdlp, '_executed'):
        upgrade_to_nightly_ytdlp()
        upgrade_to_nightly_ytdlp._executed = True
except Exception as e:
    logger.warning(f"Nu s-a putut face upgrade la nightly: {e}")

# Import Facebook fix patch
try:
    from facebook_fix_patch import (
        enhanced_facebook_extractor_args,
        normalize_facebook_share_url,
        create_robust_facebook_opts,
        generate_facebook_url_variants,
        try_facebook_with_rotation
    )
    logger.info("✅ Facebook fix patch loaded successfully")
except ImportError:
    logger.warning("⚠️ Facebook fix patch not found, using fallback methods")
    
    def enhanced_facebook_extractor_args():
        return {
            'facebook': {
                'api_version': 'v19.0',
                'legacy_ssl': True,
                'tab': 'videos',
                'ignore_parse_errors': True
            }
        }
    
    def normalize_facebook_share_url(url):
        import re
        if 'facebook.com/share/v/' in url:
            match = re.search(r'facebook\.com/share/v/([^/?]+)', url)
            if match:
                video_id = match.group(1)
                return f"https://www.facebook.com/watch?v={video_id}"
        return url
    
    def create_robust_facebook_opts():
        return {
            'format': 'best[filesize<45M][height<=720]/best[height<=720]/best',
            'extractor_args': enhanced_facebook_extractor_args()
        }
    
    def generate_facebook_url_variants(url):
        """Fallback function for URL variants generation"""
        import re
        variants = [url]
        
        # Extract video ID from various Facebook URL formats
        video_id = None
        patterns = [
            r'/watch\?v=([^&]+)',
            r'/share/v/([^/?]+)',
            r'/reel/([^/?]+)',
            r'/videos/([^/?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        if video_id:
            base_variants = [
                f"https://www.facebook.com/watch?v={video_id}",
                f"https://www.facebook.com/share/v/{video_id}/",
                f"https://www.facebook.com/reel/{video_id}",
                f"https://m.facebook.com/watch?v={video_id}"
            ]
            variants.extend([v for v in base_variants if v not in variants])
        
        return variants
    
    def try_facebook_with_rotation(url, ydl_opts, max_attempts=4):
        """Fallback function for URL rotation"""
        variants = generate_facebook_url_variants(url)
        attempted_formats = []
        last_error = None
        
        for i, variant_url in enumerate(variants[:max_attempts]):
            # Determină tipul de format
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
            
            try:
                logger.info(f"🔄 Attempt {i+1}/{max_attempts}: {format_type}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(variant_url, download=False)
                    if info:
                        logger.info(f"✅ Success with {format_type}")
                        return variant_url, info, {
                            'successful_format': format_type,
                            'attempt_number': i+1,
                            'attempted_formats': attempted_formats
                        }
            except Exception as e:
                error_msg = str(e).lower()
                last_error = str(e)
                logger.warning(f"❌ {format_type} failed: {error_msg[:50]}...")
                
                if any(keyword in error_msg for keyword in ['private', 'not available', 'unavailable', 'deleted']):
                    logger.info("Stopping rotation due to critical error")
                    return None, None, {
                        'error_type': 'critical',
                        'error_message': last_error,
                        'attempted_formats': attempted_formats,
                        'stopped_at_attempt': i+1
                    }
                continue
        
        return None, None, {
            'error_type': 'all_failed',
            'error_message': last_error,
            'attempted_formats': attempted_formats,
            'total_attempts': len(variants[:max_attempts])
        }

# Configurații pentru clienții YouTube recomandați de yt-dlp (2024)
# Bazat pe https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies
YOUTUBE_CLIENT_CONFIGS = {
    'mweb': {
        'player_client': 'mweb',
        'description': 'Mobile web client - recomandat pentru evitarea PO Token',
        'requires_po_token': False,  # Nu necesită PO Token conform documentației
        'supports_hls': True,
        'priority': 1  # Prioritate maximă
    },
    'tv_embedded': {
        'player_client': 'tv_embedded', 
        'description': 'TV embedded client - nu necesită PO Token',
        'requires_po_token': False,
        'supports_hls': True,
        'priority': 2
    },
    'web_safari': {
        'player_client': 'web_safari',
        'description': 'Safari web client - oferă HLS fără PO Token',
        'requires_po_token': False,
        'supports_hls': True,
        'priority': 3
    },
    'android_vr': {
        'player_client': 'android_vr',
        'description': 'Android VR client - nu necesită PO Token',
        'requires_po_token': False,
        'supports_hls': False,
        'priority': 4
    },
    # Clienți suplimentari pentru cazuri extreme
    'mediaconnect': {
        'player_client': 'mediaconnect',
        'description': 'Media Connect client - pentru cazuri speciale',
        'requires_po_token': False,
        'supports_hls': False,
        'priority': 5
    }
}


def validate_and_create_temp_dir():
    """Creează director temporar sigur cu validare împotriva path traversal"""
    try:
        # Creează directorul temporar
        temp_dir = tempfile.mkdtemp(prefix="video_download_")
        
        # Validare strictă împotriva path traversal
        real_path = os.path.realpath(temp_dir)
        temp_base = os.path.realpath(tempfile.gettempdir())
        
        # Verifică că directorul este într-o locație sigură
        if not real_path.startswith(temp_base):
            # Curăță directorul creat
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise Exception(f"Invalid temp directory path: {real_path}")
        
        # Verifică permisiunile
        if not os.access(temp_dir, os.W_OK):
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise Exception(f"No write access to temp directory: {temp_dir}")
        
        logger.info(f"🔒 Secure temp directory created: {temp_dir}")
        return temp_dir
        
    except Exception as e:
        logger.error(f"❌ Failed to create secure temp directory: {e}")
        # Fallback la directorul curent
        fallback_dir = os.path.join(os.getcwd(), 'temp_downloads')
        os.makedirs(fallback_dir, exist_ok=True)
        logger.warning(f"Using fallback temp directory: {fallback_dir}")
        return fallback_dir

# Configurații îmbunătățite pentru toate platformele
ENHANCED_PLATFORM_CONFIGS = {
    'tiktok': {
        'user_agents': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 5,
            'fragment_retries': 5,
            'extractor_retries': 3,
            'socket_timeout': 30,
            'sleep_interval': 2,
            'max_sleep_interval': 10,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'tiktok': {
                    'webpage_download_timeout': 30,
                    'api_hostname': 'api.tiktokv.com'
                }
            }
        }
    },
    'instagram': {
        'user_agents': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'instagram': {
                    'api_version': 'v19.0',
                    'include_stories': False
                }
            }
        }
    },
    'reddit': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 5,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True
        }
    },
    'facebook': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 5,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'facebook': {
                    'api_version': 'v19.0',
                    'legacy_ssl': True,
                    'tab': 'videos'
                }
            }
        }
    },
    'twitter': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True
        }
    },
    'vimeo': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True
        }
    },
    'dailymotion': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True
        }
    },
    'pinterest': {
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True
        }
    },
    'threads': {
        'user_agents': [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        'ydl_opts_extra': {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'instagram': {  # Threads folosește Instagram extractor
                    'api_version': 'v19.0'
                }
            }
        }
    }
}

def get_platform_from_url(url):
    """Determină platforma din URL"""
    url_lower = url.lower()
    
    if any(domain in url_lower for domain in ['tiktok.com', 'vm.tiktok.com']):
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif any(domain in url_lower for domain in ['reddit.com', 'redd.it', 'v.redd.it']):
        return 'reddit'
    elif any(domain in url_lower for domain in ['facebook.com', 'fb.watch', 'fb.me']):
        return 'facebook'
    elif any(domain in url_lower for domain in ['twitter.com', 'x.com']):
        return 'twitter'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    elif any(domain in url_lower for domain in ['dailymotion.com', 'dai.ly']):
        return 'dailymotion'
    elif any(domain in url_lower for domain in ['pinterest.com', 'pin.it']):
        return 'pinterest'
    elif 'threads.net' in url_lower:
        return 'threads'
    
    return 'generic'

def create_enhanced_ydl_opts(url, temp_dir):
    """Creează opțiuni yt-dlp îmbunătățite cu anti-bot detection și configurații de producție"""
    platform = get_platform_from_url(url)
    
    # Validează securitatea URL-ului
    if not validate_url_security(url):
        raise ValueError(f"URL nesigur sau nepermis: {url}")
    
    # Folosește modulul anti-bot detection pentru configurații avansate
    try:
        ydl_opts = create_anti_bot_ydl_opts(url)
        ydl_opts = enhance_ydl_opts_for_production(ydl_opts, platform)
        
        # Actualizează outtmpl cu temp_dir specificat
        ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
        
        # Adaugă configurații specifice pentru producție
        production_opts = get_production_ydl_opts_enhancement()
        ydl_opts.update(production_opts)
        
        # Configurează proxy dacă este disponibil
        proxy = get_proxy_for_platform(platform)
        if proxy:
            ydl_opts['proxy'] = proxy
            logger.info(f"🌐 Folosind proxy pentru {platform}")
        
        # Configurează cookies dacă sunt disponibile
        cookies_file = get_cookies_for_platform(platform)
        if cookies_file:
            ydl_opts['cookiefile'] = cookies_file
            logger.info(f"🍪 Folosind cookies pentru {platform}")
        
        # Configurații suplimentare pentru mediul de producție
        if is_production_environment():
            ydl_opts.update({
                'quiet': True,  # Reduce logging în producție
                'no_warnings': True,
                'extract_flat': False,
                'writeinfojson': False,
                'writethumbnail': False,
                'writesubtitles': False,
                'writeautomaticsub': False
            })
            logger.info(f"🏭 Configurații de producție aplicate pentru {platform}")
        
        logger.info(f"🛡️ Configurații anti-bot și producție aplicate pentru {platform}")
        return ydl_opts
        
    except Exception as e:
        logger.warning(f"⚠️ Eroare la aplicarea configurațiilor avansate: {e}")
        # Fallback la configurația de bază
        config = ENHANCED_PLATFORM_CONFIGS.get(platform, {})
        
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
            'http_headers': get_random_headers()
        }
        
        # Adaugă configurații specifice platformei
        if config.get('ydl_opts_extra'):
            ydl_opts.update(config['ydl_opts_extra'])
        
        # Setează user agent aleatoriu din lista platformei
        if config.get('user_agents'):
            user_agent = random.choice(config['user_agents'])
            ydl_opts['http_headers']['User-Agent'] = user_agent
        
        logger.info(f"📋 Configurații fallback aplicate pentru {platform}")
        return ydl_opts

def download_with_enhanced_retry(url, temp_dir, max_attempts=3):
    """Descarcă cu strategii îmbunătățite de retry și anti-bot detection"""
    platform = get_platform_from_url(url)
    config = ENHANCED_PLATFORM_CONFIGS.get(platform, {})
    
    last_error = None
    last_request_time = None
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔄 Încercare {attempt + 1}/{max_attempts} pentru {platform}...")
            
            # Implementează rate limiting pentru evitarea detecției
            implement_rate_limiting(platform)
            last_request_time = time.time()
            
            # Creează opțiuni îmbunătățite cu anti-bot detection
            ydl_opts = create_enhanced_ydl_opts(url, temp_dir)
            
            # Adaugă delay între încercări (exponential backoff)
            if attempt > 0:
                delay = 2 ** attempt  # Exponential backoff
                logger.info(f"⏱️ Așteptare {delay}s înainte de încercarea {attempt + 1}...")
                time.sleep(delay)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extrage informații
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Nu s-au putut extrage informațiile video")
                
                # Verifică dacă este live stream
                if info.get('is_live'):
                    raise Exception("Live stream-urile nu sunt suportate")
                
                # Descarcă videoclipul
                ydl.download([url])
                
                # Găsește fișierul descărcat
                downloaded_files = []
                for file in os.listdir(temp_dir):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.3gp')):
                        downloaded_files.append(os.path.join(temp_dir, file))
                
                if not downloaded_files:
                    raise Exception("Nu s-a găsit fișierul video descărcat")
                
                video_file = downloaded_files[0]
                file_size = os.path.getsize(video_file)
                
                # Calculează durata descărcării
                download_duration = time.time() - last_request_time
                
                logger.info(f"✅ Descărcare reușită pentru {platform} la încercarea {attempt + 1}")
                log_anti_bot_status(platform, True, attempt + 1)
                log_production_metrics(platform, True, download_duration, file_size)
                
                return {
                    'success': True,
                    'file_path': video_file,
                    'title': info.get('title', 'Video'),
                    'description': info.get('description', ''),
                    'uploader': info.get('uploader', ''),
                    'duration': info.get('duration', 0),
                    'file_size': file_size,
                    'platform': platform,
                    'attempt_number': attempt + 1,
                    'anti_bot_bypass': True,
                    'download_duration': download_duration
                }
                
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            logger.warning(f"❌ Încercarea {attempt + 1} eșuată pentru {platform}: {error_msg[:100]}...")
            log_anti_bot_status(platform, False, f"Încercarea {attempt + 1}: {error_msg[:100]}")
            
            # Verifică dacă este o eroare critică care nu merită retry
            critical_errors = [
                'private video', 'video unavailable', 'video not found',
                'this video is private', 'content not available',
                'video has been removed', 'account suspended',
                'sign in to confirm', 'bot', 'captcha', '403', '429'
            ]
            
            if any(critical in error_msg.lower() for critical in critical_errors):
                logger.info(f"🛑 Eroare critică detectată (posibil anti-bot), oprire retry pentru {platform}")
                break
    
    return {
        'success': False,
        'error': f'❌ {platform.title()}: Toate încercările au eșuat. Ultima eroare: {last_error}',
        'file_path': None,
        'file_size': 0,
        'duration': 0,
        'title': f'{platform.title()} - Eșec descărcare',
        'platform': platform,
        'total_attempts': max_attempts
    }



# Lista de User Agents reali pentru a evita detecția
REAL_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# Lista de Accept-Language headers reali
ACCEPT_LANGUAGES = [
    'en-US,en;q=0.9',
    'en-GB,en;q=0.9',
    'en-US,en;q=0.8,es;q=0.6',
    'en-US,en;q=0.9,fr;q=0.8',
    'en-US,en;q=0.9,de;q=0.8',
    'en-US,en;q=0.9,it;q=0.8',
    'en-US,en;q=0.9,pt;q=0.8',
]

def get_random_headers():
    """Generează headers HTTP reali pentru a evita detecția"""
    user_agent = random.choice(REAL_USER_AGENTS)
    accept_language = random.choice(ACCEPT_LANGUAGES)
    
    # Generează un viewport realist bazat pe user agent
    if 'Mobile' in user_agent or 'Android' in user_agent:
        viewport = random.choice(['375x667', '414x896', '360x640', '412x915'])
    else:
        viewport = random.choice(['1920x1080', '1366x768', '1536x864', '1440x900', '1280x720'])
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': accept_language,
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # Adaugă headers specifice pentru Chrome
    if 'Chrome' in user_agent and 'Edg' not in user_agent:
        headers.update({
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0' if 'Mobile' not in user_agent else '?1',
            'sec-ch-ua-platform': '"Windows"' if 'Windows' in user_agent else ('"macOS"' if 'Mac' in user_agent else '"Linux"'),
        })
    
    return headers

def get_youtube_cookies():
    """Generează cookies simulate pentru YouTube (fără a fi trimise ca header pentru securitate)
    Conform avertismentului yt-dlp, cookies nu trebuie trimise ca header HTTP
    """
    # Nu mai returnăm cookies ca string în header pentru a evita avertismentul de securitate
    # În schimb, folosim configurații extractor specifice
    return None

def get_youtube_extractor_args(client_type='mweb'):
    """Configurează argumentele extractor pentru YouTube conform documentației oficiale"""
    client_config = YOUTUBE_CLIENT_CONFIGS.get(client_type, YOUTUBE_CLIENT_CONFIGS['mweb'])
    
    # Configurații de bază pentru extractor
    extractor_args = {
        'youtube': {
            'player_client': [client_config['player_client']],
            # Configurații pentru evitarea PO Token
            'player_skip': ['webpage', 'configs'] if not client_config.get('requires_po_token') else [],
            # Configurații pentru HLS
            'skip': [] if client_config.get('supports_hls') else ['hls'],
            # Configurații suplimentare pentru anti-detecție
            'innertube_host': 'www.youtube.com',
            'innertube_key': None,  # Lasă yt-dlp să detecteze automat
            'comment_sort': 'top',
            'max_comments': [0],  # Nu extrage comentarii
        }
    }
    
    # Configurații specifice pentru client mweb (recomandat)
    if client_type == 'mweb':
        extractor_args['youtube'].update({
            'player_client': ['mweb'],
            'player_skip': ['webpage'],  # Skip webpage pentru mweb
            'innertube_host': 'm.youtube.com',  # Host mobil
        })
    
    # Configurații pentru tv_embedded
    elif client_type == 'tv_embedded':
        extractor_args['youtube'].update({
            'player_client': ['tv_embedded'],
            'player_skip': ['webpage', 'configs'],
        })
    
    # Configurații pentru web_safari
    elif client_type == 'web_safari':
        extractor_args['youtube'].update({
            'player_client': ['web_safari'],
            'player_skip': ['webpage'],
        })
    
    return extractor_args

def create_youtube_session_advanced(client_type='mweb'):
    """Creează o sesiune YouTube avansată cu configurații anti-detecție și client optim"""
    headers = get_random_headers()
    client_config = YOUTUBE_CLIENT_CONFIGS.get(client_type, YOUTUBE_CLIENT_CONFIGS['mweb'])
    extractor_args = get_youtube_extractor_args(client_type)
    
    # Configurații avansate pentru a evita detecția
    session_config = {
        'http_headers': headers,
        'cookiefile': None,  # Nu salvăm cookies pe disk pentru securitate
        'nocheckcertificate': False,
        'prefer_insecure': False,
        'cachedir': False,  # Dezactivează cache pentru a evita detecția
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': False,
        'geo_bypass': True,
        'geo_bypass_country': random.choice(['US', 'GB', 'CA', 'AU']),
        'age_limit': None,
        'sleep_interval': 1,  # Redus pentru server mic
        'max_sleep_interval': 5,  # Redus pentru server mic
        'sleep_interval_subtitles': 1,
        'socket_timeout': 30,  # Redus dramatic pentru server mic
        'retries': 1,  # Redus pentru server mic
        'extractor_retries': 1,  # Redus pentru server mic
        'fragment_retries': 2,  # Redus pentru server mic
        'retry_sleep_functions': {
            'http': lambda n: min(2 + n, 10),  # Simplificat pentru server mic
            'fragment': lambda n: min(2 + n, 10)  # Simplificat pentru server mic
        },
        # Configurații extractor optimizate
        'extractor_args': extractor_args,
        # Simulează comportament de browser real
        'extract_comments': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'embed_subs': False,
        'writeinfojson': False,
        'writethumbnail': False,
        'writedescription': False,
        'writeannotations': False,
        # Configurații suplimentare pentru evitarea detecției
        'no_color': True,
        'no_check_certificate': False,
        'prefer_free_formats': True,
        'youtube_include_dash_manifest': False,  # Evită DASH pentru simplitate
    }
    
    # Nu mai adăugăm cookies în header pentru a evita avertismentele de securitate
    # Cookies sunt gestionate prin configurații extractor specifice
    
    return session_config, client_config

# Funcția create_youtube_session a fost eliminată - YouTube nu mai este suportat

# Funcția is_youtube_bot_detection_error a fost eliminată - YouTube nu mai este suportat

def is_youtube_bot_detection_error(error_msg):
    """Funcție păstrată pentru compatibilitate - YouTube nu mai este suportat"""
    return False  # YouTube nu mai este suportat

def is_po_token_required_error(error_msg):
    """Funcție păstrată pentru compatibilitate - YouTube nu mai este suportat"""
    return False  # YouTube nu mai este suportat

# Funcțiile YouTube au fost eliminate - YouTube nu mai este suportat

def get_youtube_retry_strategy_advanced(attempt_number):
    """Funcție păstrată pentru compatibilitate - YouTube nu mai este suportat"""
    return None  # YouTube nu mai este suportat

def sanitize_filename(filename):
    """
    Sanitizează numele fișierului pentru a fi compatibil cu Windows
    """
    import re
    # Înlocuiește caracterele invalide pentru Windows
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Limitează lungimea numelui
    if len(filename) > 200:
        filename = filename[:200]
    
    # Elimină spațiile de la început și sfârșit
    filename = filename.strip()
    
    return filename

def clean_title(title):
    """
    Curăță titlul de emoticoane, caractere Unicode problematice și alte caractere speciale
    """
    if not title:
        return ""
    
    # Înlocuiește newlines și carriage returns cu spații
    title = title.replace('\n', ' ').replace('\r', ' ')
    
    # Elimină emoticoanele și simbolurile Unicode problematice
    # Păstrează doar caracterele alfanumerice, spațiile și punctuația de bază
    title = re.sub(r'[^\w\s\-_.,!?()\[\]{}"\':;]+', '', title, flags=re.UNICODE)
    
    # Normalizează caracterele Unicode (convertește caractere accentuate la forma de bază)
    title = unicodedata.normalize('NFKD', title)
    
    # Elimină caracterele de control și caracterele invizibile
    title = ''.join(char for char in title if unicodedata.category(char)[0] != 'C')
    
    # Curăță spațiile multiple și trim
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Limitează lungimea titlului pentru a evita probleme
    if len(title) > 200:
        title = title[:200].strip()
        if not title.endswith('...'):
            title += '...'
    
    return title if title else "Video"

# Funcția YouTube fallback a fost eliminată - YouTube nu mai este suportat

def normalize_facebook_url(url):
    """
    Normalizează URL-urile Facebook noi în formate mai vechi pe care yt-dlp le poate procesa
    UPDATED: Folosește patch-ul Facebook pentru gestionarea URL-urilor share/v/
    """
    import re
    
    # Folosește funcția din patch pentru normalizare
    normalized_url = normalize_facebook_share_url(url)
    if normalized_url != url:
        logger.info(f"URL Facebook normalizat cu patch: {url} -> {normalized_url}")
        return normalized_url
    
    # Verifică alte formate noi care ar putea necesita conversie
    reel_pattern = r'facebook\.com/reel/([^/?]+)'
    reel_match = re.search(reel_pattern, url)
    if reel_match:
        reel_id = reel_match.group(1)
        old_format_url = f"https://www.facebook.com/watch?v={reel_id}"
        logger.info(f"URL Facebook Reel convertit: {url} -> {old_format_url}")
        return old_format_url
    
    # Dacă URL-ul este deja în format vechi sau alt format, îl returnează neschimbat
    return url

def try_facebook_fallback(url, output_path, title):
    """
    Încearcă descărcarea Facebook cu opțiuni alternative și gestionare îmbunătățită a erorilor
    UPDATED: Folosește patch-ul Facebook pentru configurații robuste + sistem de rotare URL
    """
    logger.info(f"Încercare Facebook fallback pentru: {url[:50]}...")
    
    # Normalizează URL-ul Facebook folosind patch-ul
    normalized_url = normalize_facebook_url(url)
    if normalized_url != url:
        logger.info(f"URL Facebook normalizat cu patch: {normalized_url}")
        url = normalized_url
    
    # STEP 1: Încearcă cu sistemul de rotare URL înainte de fallback-uri
    logger.info("🔄 STEP 1: Încercare cu sistemul de rotare URL (silențios)...")
    try:
        robust_opts = create_robust_facebook_opts()
        robust_opts.update({
            'outtmpl': output_path,
            'quiet': False,
            'noplaylist': True,
            'extractaudio': False,
            'skip_download': True,  # Doar extragere info pentru rotare
            'writeinfojson': False,
            'writethumbnail': False,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
        })
        
        # Încearcă rotarea URL-urilor
        rotation_result = try_facebook_with_rotation(url, robust_opts, max_attempts=4)
        success_url, video_info, rotation_info = rotation_result
        
        if success_url and video_info:
            logger.info(f"✅ Facebook rotation SUCCESS! Using {rotation_info['successful_format']} at attempt {rotation_info['attempt_number']}")
            
            # Acum descarcă cu URL-ul care funcționează
            download_opts = robust_opts.copy()
            download_opts['skip_download'] = False
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([success_url])
                
                # Verifică dacă fișierul a fost descărcat
                import glob
                temp_dir = os.path.dirname(output_path)
                downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
                downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
                
                if downloaded_files:
                    logger.info("✅ Facebook descărcare reușită cu sistem de rotare")
                    return {
                        'success': True,
                        'file_path': downloaded_files[0],
                        'title': video_info.get('title', title),
                        'description': video_info.get('description', ''),
                        'rotation_info': f"✅ Succes cu {rotation_info['successful_format']} la încercarea {rotation_info['attempt_number']}",
                        'uploader': video_info.get('uploader', ''),
                        'duration': video_info.get('duration', 0),
                        'file_size': os.path.getsize(downloaded_files[0])
                    }
        else:
            # Rotația a eșuat - oferă mesaj detaliat bazat pe informațiile de rotație
            if rotation_info:
                if rotation_info.get('error_type') == 'critical':
                    return {
                        'success': False,
                        'error': f"❌ Facebook: Conținut privat sau indisponibil.\n\n🔄 Formate încercate: {', '.join(rotation_info['attempted_formats'])}\n🛑 Oprire la încercarea {rotation_info['stopped_at_attempt']} din cauza erorii critice.\n\n💡 Verifică dacă link-ul este public și valid.",
                        'title': title
                    }
                elif rotation_info.get('error_type') == 'all_failed':
                    return {
                        'success': False,
                        'error': f"❌ Facebook: Toate formatele au eșuat.\n\n🔄 Formate încercate ({rotation_info['total_attempts']}): {', '.join(rotation_info['attempted_formats'])}\n\n📋 Continuă cu fallback-urile clasice...",
                        'title': title
                    }
    except Exception as rotation_error:
        logger.warning(f"🔄 Sistemul de rotare eșuat: {str(rotation_error)[:100]}...")
        logger.info("📋 Continuă cu fallback-urile clasice...")
    
    # STEP 2: Încearcă cu configurația robustă din patch (fallback clasic)
    logger.info("🔧 STEP 2: Încercare cu configurația robustă din patch...")
    try:
        robust_opts = create_robust_facebook_opts()
        robust_opts.update({
            'outtmpl': output_path,
            'quiet': False,
            'noplaylist': True,
            'extractaudio': False,
            'skip_download': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
        })
        
        with yt_dlp.YoutubeDL(robust_opts) as ydl:
            logger.info("Începe descărcarea Facebook cu patch robust...")
            ydl.download([url])
            
            # Verifică dacă fișierul a fost descărcat
            import glob
            temp_dir = os.path.dirname(output_path)
            downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
            downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
            
            if downloaded_files:
                logger.info("✅ Facebook descărcare reușită cu patch robust")
                return {
                    'success': True,
                    'file_path': downloaded_files[0],
                    'title': title,
                    'description': '',
                    'uploader': '',
                    'duration': 0,
                    'file_size': os.path.getsize(downloaded_files[0])
                }
    except Exception as patch_error:
        logger.warning(f"Patch robust eșuat: {str(patch_error)[:100]}...")
        logger.info("📋 Continuă cu fallback-urile alternative...")
    
    # Configurații alternative pentru Facebook - optimizate pentru 2025 cu strategii diverse
    fallback_configs = [
        # Configurația 1: Chrome desktop cu API v19.0 (cea mai recentă)
        {
            'format': 'best[filesize<45M][height<=720]/best',
            'restrictfilenames': True,
            'windowsfilenames': True,
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
                'Cache-Control': 'max-age=0',
            },
            'extractor_retries': 5,
            'fragment_retries': 5,
            'socket_timeout': 45,
            'retries': 5,
            'ignoreerrors': True,
            'extract_flat': False,
            'no_warnings': True,
            'sleep_interval': 2,
            'max_sleep_interval': 5,
            'extractor_args': {
                'facebook': {
                    'legacy_ssl': True,
                    'api_version': 'v19.0',
                    'tab': 'videos'
                }
            },
        },
        # Configurația 2: Firefox desktop cu strategii alternative
        {
            'format': 'best[filesize<45M][height<=720]/best',
            'restrictfilenames': True,
            'windowsfilenames': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
            'extractor_retries': 4,
            'fragment_retries': 4,
            'socket_timeout': 40,
            'retries': 4,
            'ignoreerrors': True,
            'sleep_interval': 3,
            'max_sleep_interval': 7,
            'extractor_args': {
                'facebook': {
                    'legacy_ssl': True,
                    'api_version': 'v18.0',
                    'tab': 'videos',
                    'legacy_format': True
                }
            },
        },
        # Configurația 3: iPhone Safari mobile cu API v17.0
        {
            'format': 'best[filesize<45M][height<=720]/best',
            'restrictfilenames': True,
            'windowsfilenames': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 35,
            'retries': 3,
            'ignoreerrors': True,
            'sleep_interval': 4,
            'max_sleep_interval': 8,
            'extractor_args': {
                'facebook': {
                    'mobile_client': True,
                    'legacy_ssl': True,
                    'api_version': 'v17.0',
                    'tab': 'videos'
                }
            },
        },
        # Configurația 4: Android Chrome mobile cu strategii agresive
        {
            'format': 'best[filesize<45M][height<=720]/best',
            'restrictfilenames': True,
            'windowsfilenames': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            'retries': 3,
            'ignoreerrors': True,
            'sleep_interval': 5,
            'max_sleep_interval': 10,
            'extractor_args': {
                'facebook': {
                    'android_client': True,
                    'legacy_ssl': True,
                    'api_version': 'v18.0',
                    'tab': 'videos'
                }
            },
        },
        # Configurația 5: Strategia de ultimă instanță - calitate scăzută, timeout mare
        {
            'format': 'worst[filesize<512M][height<=360]/worst[height<=360]/worst[filesize<512M]/worst',
            'restrictfilenames': True,
            'windowsfilenames': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Android 12; Mobile; rv:122.0) Gecko/122.0 Firefox/122.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            'extractor_retries': 2,
            'fragment_retries': 2,
            'socket_timeout': 60,
            'retries': 2,
            'ignoreerrors': True,
            'sleep_interval': 8,
            'max_sleep_interval': 15,
            'extractor_args': {
                'facebook': {
                    'android_client': True,
                    'legacy_ssl': True,
                    'low_quality': True,
                    'api_version': 'v16.0',
                    'tab': 'videos',
                    'legacy_format': True
                }
            },
        },
        # Configurația 6: Fallback extrem - fără extractor_args
        {
            'format': 'worst[filesize<256M]/worst',
            'restrictfilenames': True,
            'windowsfilenames': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': '*/*',
            },
            'extractor_retries': 1,
            'fragment_retries': 1,
            'socket_timeout': 90,
            'retries': 1,
            'ignoreerrors': True,
            'sleep_interval': 10,
            'max_sleep_interval': 20,
        }
    ]
    
    # Încearcă fiecare configurație până când una funcționează
    for i, config in enumerate(fallback_configs):
        logger.info(f"Încercare Facebook configurația {i+1}/{len(fallback_configs)}...")
        
        fallback_opts = {
            'outtmpl': output_path,
            'quiet': False,  # Activez logging pentru debugging
            'noplaylist': True,
            'extractaudio': False,
            'skip_download': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
        }
        
        # Adaugă configurația specifică
        fallback_opts.update(config)
    
        try:
            # Încearcă să obțină informații despre video mai întâi
            info_opts = fallback_opts.copy()
            info_opts['skip_download'] = True
            
            video_info = None
            try:
                with yt_dlp.YoutubeDL(info_opts) as ydl_info:
                    video_info = ydl_info.extract_info(url, download=False)
                    logger.info(f"Facebook video info extracted: {video_info.get('title', 'N/A')[:50]}...")
            except Exception as info_error:
                logger.warning(f"Nu s-au putut extrage informațiile video Facebook: {str(info_error)}")
                if i == len(fallback_configs) - 1:  # Ultima configurație
                    continue
            
            # Încearcă descărcarea efectivă
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                logger.info(f"Începe descărcarea Facebook cu configurația {i+1}...")
                ydl.download([url])
                
                # Găsește fișierul descărcat cu verificări îmbunătățite
                temp_dir = os.path.dirname(output_path)
                logger.info(f"Căutare fișiere în: {temp_dir}")
                
                # Caută toate fișierele din directorul temporar
                all_files = glob.glob(os.path.join(temp_dir, "*"))
                downloaded_files = [f for f in all_files if os.path.isfile(f) and not f.endswith('.part')]
                
                logger.info(f"Fișiere găsite: {len(downloaded_files)}")
                for file in downloaded_files:
                    logger.info(f"Fișier: {os.path.basename(file)} ({os.path.getsize(file)} bytes)")
                
                if downloaded_files:
                    # Ia cel mai mare fișier (probabil videoul)
                    downloaded_file = max(downloaded_files, key=os.path.getsize)
                    file_size = os.path.getsize(downloaded_file)
                    
                    # Verifică că fișierul nu este prea mic (probabil corupt)
                    if file_size < 1024:  # Mai mic de 1KB
                        logger.error(f"Fișierul descărcat este prea mic: {file_size} bytes")
                        if i < len(fallback_configs) - 1:  # Nu e ultima configurație
                            continue
                        return {
                            'success': False,
                            'error': '❌ Facebook: Fișierul descărcat pare să fie corupt (prea mic).',
                            'title': title or 'N/A'
                        }
                    
                    logger.info(f"Facebook download successful: {os.path.basename(downloaded_file)} ({file_size} bytes)")
                    return {
                        'success': True,
                        'file_path': downloaded_file,
                        'title': video_info.get('title') if video_info else (title or "Video Facebook"),
                        'description': video_info.get('description', 'Descărcat cu opțiuni alternative')[:200] if video_info else "Descărcat cu opțiuni alternative",
                        'uploader': video_info.get('uploader', 'Facebook') if video_info else "Facebook",
                        'duration': video_info.get('duration', 0) if video_info else 0,
                        'file_size': file_size
                    }
                else:
                    logger.error("Nu s-au găsit fișiere descărcate în directorul temporar")
                    if i < len(fallback_configs) - 1:  # Nu e ultima configurație
                        continue
                    return {
                        'success': False,
                        'error': '❌ Facebook: Nu s-a putut descărca videoul. Fișierul nu a fost găsit după descărcare.',
                        'title': title or 'N/A'
                    }
                    
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            logger.error(f"Facebook DownloadError configurația {i+1}: {str(e)}")
            
            # Dacă nu e ultima configurație, încearcă următoarea
            if i < len(fallback_configs) - 1:
                logger.info(f"Încercare următoarea configurație Facebook...")
                continue
            
            # Ultima configurație - returnează eroarea
            if 'private' in error_msg or 'login' in error_msg:
                return {
                    'success': False,
                    'error': '❌ Facebook: Videoul este privat sau necesită autentificare.',
                    'title': title or 'N/A'
                }
            elif 'not available' in error_msg or 'removed' in error_msg:
                return {
                    'success': False,
                    'error': '❌ Facebook: Videoul nu mai este disponibil sau a fost șters.',
                    'title': title or 'N/A'
                }
            elif 'parse' in error_msg or 'extract' in error_msg or 'Cannot parse data' in error_msg:
                logger.warning(f"Facebook parsing error pentru URL: {url}")
                return {
                    'success': False,
                    'error': '❌ Facebook: Nu pot procesa acest link din cauza schimbărilor recente ale Facebook.\n\n🔧 Soluții posibile:\n• Încearcă să copiezi link-ul direct din browser\n• Verifică dacă videoul este public\n• Încearcă un alt format de link Facebook\n• Contactează adminul dacă problema persistă\n\n💡 Facebook schimbă frecvent API-ul, ceea ce poate cauza probleme temporare.',
                    'title': title or 'N/A'
                }
            elif 'Unsupported URL' in error_msg:
                logger.warning(f"Facebook URL nesuportat: {url}")
                return {
                    'success': False,
                    'error': '❌ Facebook: Formatul acestui link nu este suportat. Te rog să încerci un link direct către video.',
                    'title': title or 'N/A'
                }
            else:
                return {
                    'success': False,
                    'error': f'❌ Facebook: Eroare la descărcare: {str(e)}',
                    'title': title or 'N/A'
                }
        except Exception as e:
            logger.error(f"Facebook unexpected error configurația {i+1}: {str(e)}")
            
            # Dacă nu e ultima configurație, încearcă următoarea
            if i < len(fallback_configs) - 1:
                logger.info(f"Încercare următoarea configurație Facebook...")
                continue
            
            # Ultima configurație - returnează eroarea
            return {
                'success': False,
                'error': f'❌ Facebook: Eroare neașteptată: {str(e)}',
                'title': title or 'N/A'
            }
    
    # Dacă ajungem aici, toate configurațiile au eșuat
    return {
        'success': False,
        'error': '❌ Facebook: Toate configurațiile au eșuat. Videoul poate fi privat sau restricționat.',
        'title': title or 'N/A'
    }

def validate_url(url):
    """Validează URL-ul pentru a preveni erorile DNS"""
    if not url or len(url.strip()) < 10:
        return False, "URL invalid sau prea scurt"
    
    url = url.strip()
    
    # Verifică dacă URL-ul conține domenii suportate
    supported_domains = [
        # TikTok
        'tiktok.com', 'vm.tiktok.com',
        # Instagram
        'instagram.com', 'www.instagram.com',
        # Facebook
        'facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.watch', 'fb.me',
        # Twitter/X
        'twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'x.com', 'www.x.com', 'mobile.x.com',
        # Threads
        'threads.net', 'www.threads.net', 'threads.com', 'www.threads.com',
        # Pinterest
        'pinterest.com', 'www.pinterest.com', 'pinterest.co.uk', 'pin.it', 'pinterest.fr', 'pinterest.de', 'pinterest.ca',
        # Reddit
        'reddit.com', 'www.reddit.com', 'old.reddit.com', 'redd.it', 'v.redd.it', 'i.redd.it',
        # Vimeo
        'vimeo.com', 'www.vimeo.com', 'player.vimeo.com',
        # Dailymotion
        'dailymotion.com', 'www.dailymotion.com', 'dai.ly', 'geo.dailymotion.com'
    ]
    
    if not any(domain in url.lower() for domain in supported_domains):
        return False, "Domeniu nesuportat"
    
    # Verifică dacă URL-ul nu este corupt (ex: doar "w")
    if len(url) < 15 or not url.startswith(('http://', 'https://')):
        return False, "URL corupt sau incomplet"
    
    return True, "URL valid"

def download_video(url, output_path=None):
    """
    Descarcă un video cu strategii îmbunătățite pentru toate platformele
    Optimizat special pentru mediul Render
    Returnează un dicționar cu rezultatul
    """
    logger.info(f"=== RENDER OPTIMIZED DOWNLOAD START === URL: {url}")
    
    try:
        # Verifică dacă rulează în mediul Render și aplică configurații specifice
        if is_render_environment():
            logger.info("🚀 Mediu Render detectat - aplicând configurații optimizate")
            cleanup_render_temp_files()  # Curăță fișierele vechi
        
        # Validează URL-ul înainte de procesare
        logger.info(f"=== RENDER OPTIMIZED Validating URL ===")
        is_valid, validation_msg = validate_url(url)
        if not is_valid:
            logger.error(f"=== RENDER OPTIMIZED URL Invalid === {validation_msg}")
            return {
                'success': False,
                'error': f'❌ URL invalid: {validation_msg}',
                'title': 'N/A'
            }
    
        # Creează directorul temporar optimizat pentru Render
        if is_render_environment():
            temp_dir = get_render_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(f"🏭 Folosind directorul Render: {temp_dir}")
        else:
            temp_dir = validate_and_create_temp_dir()
            if not temp_dir:
                return {
                    'success': False,
                    'error': '❌ Nu s-a putut crea directorul temporar',
                    'title': 'N/A'
                }
    
        logger.info(f"=== RENDER OPTIMIZED Temp dir ready: {temp_dir} ===")
    
        # Folosește strategia îmbunătățită de descărcare cu configurații Render
        result = download_with_render_optimization(url, temp_dir, max_attempts=3)
        
        if result['success']:
            logger.info(f"✅ RENDER OPTIMIZED SUCCESS: {result['title']}")
        else:
            logger.error(f"❌ RENDER OPTIMIZED FAILED: {result['error']}")
        
        return result
    
    except Exception as e:
        logger.error(f"=== ENHANCED DOWNLOAD_VIDEO Exception === {str(e)}")
        import traceback
        logger.error(f"=== ENHANCED DOWNLOAD_VIDEO Traceback === {traceback.format_exc()}")
        return {
            'success': False,
            'error': f'❌ Eroare neașteptată: {str(e)}',
            'title': 'N/A'
        }
    
    finally:
        # Nu șterge temp_dir aici - va fi șters după trimiterea fișierului
        pass


def download_with_render_optimization(url, temp_dir, max_attempts=3):
    """Descarcă cu optimizări specifice pentru mediul Render"""
    platform = get_platform_from_url(url)
    logger.info(f"🚀 RENDER OPTIMIZED DOWNLOAD pentru {platform}: {url}")
    
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔄 Render încercare {attempt + 1}/{max_attempts} pentru {platform}...")
            
            # Implementează rate limiting pentru evitarea detecției
            if is_render_environment():
                rate_config = RENDER_OPTIMIZED_CONFIG['rate_limiting']
                if rate_config['enabled']:
                    platform_limit = rate_config['requests_per_minute'].get(platform, 10)
                    cooldown = rate_config['cooldown_seconds']
                    logger.info(f"⏱️ Rate limiting Render: {platform_limit}/min, cooldown: {cooldown}s")
                    time.sleep(cooldown)
            
            # Creează opțiuni yt-dlp optimizate pentru Render
            if is_render_environment():
                ydl_opts = get_render_ytdl_opts(platform)
                ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
                logger.info(f"🏭 Folosind configurații Render pentru {platform}")
            else:
                ydl_opts = create_enhanced_ydl_opts(url, temp_dir)
            
            # Adaugă delay între încercări (exponential backoff)
            if attempt > 0:
                delay = min(2 ** attempt, 10)  # Max 10 secunde pentru Render
                logger.info(f"⏱️ Render backoff: {delay}s înainte de încercarea {attempt + 1}...")
                time.sleep(delay)
            
            # Înregistrează timpul de început
            start_time = time.time()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extrage informații
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Nu s-au putut extrage informațiile video")
                
                # Verifică dacă este live stream
                if info.get('is_live'):
                    raise Exception("Live stream-urile nu sunt suportate")
                
                # Verifică dimensiunea fișierului pentru Render
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize and filesize > RENDER_OPTIMIZED_CONFIG['security']['max_file_size']:
                    raise Exception(f"Fișier prea mare pentru Render: {filesize / (1024*1024):.1f}MB")
                
                # Descarcă videoclipul
                ydl.download([url])
                
                # Găsește fișierul descărcat
                downloaded_files = []
                for file in os.listdir(temp_dir):
                    if file.endswith(tuple(RENDER_OPTIMIZED_CONFIG['security']['allowed_extensions'])):
                        downloaded_files.append(os.path.join(temp_dir, file))
                
                if not downloaded_files:
                    raise Exception("Nu s-a găsit fișierul video descărcat")
                
                video_file = downloaded_files[0]
                file_size = os.path.getsize(video_file)
                download_duration = time.time() - start_time
                
                logger.info(f"✅ Render download reușit pentru {platform} la încercarea {attempt + 1}")
                logger.info(f"📊 Render stats: {file_size / (1024*1024):.1f}MB în {download_duration:.1f}s")
                
                # Log pentru anti-bot și producție
                log_anti_bot_status(platform, True, f"Render încercarea {attempt + 1}: {download_duration:.1f}s")
                if 'log_production_metrics' in globals():
                    log_production_metrics(platform, True, download_duration, file_size)
                
                return {
                    'success': True,
                    'file_path': video_file,
                    'title': info.get('title', 'Video'),
                    'description': info.get('description', ''),
                    'uploader': info.get('uploader', ''),
                    'duration': info.get('duration', 0),
                    'file_size': file_size,
                    'download_time': download_duration,
                    'render_optimized': True,
                    'attempt': attempt + 1
                }
                
        except Exception as e:
            last_error = str(e)
            error_msg = f"Render încercare {attempt + 1} eșuată pentru {platform}: {last_error[:100]}"
            logger.warning(error_msg)
            
            # Log pentru anti-bot
            log_anti_bot_status(platform, False, f"Render încercarea {attempt + 1}: {last_error[:100]}")
            
            # Cleanup parțial în caz de eroare
            if is_render_environment():
                try:
                    for file in os.listdir(temp_dir):
                        if file.endswith('.part') or file.endswith('.tmp'):
                            os.remove(os.path.join(temp_dir, file))
                except:
                    pass
            
            if attempt == max_attempts - 1:
                break
    
    # Toate încercările au eșuat
    logger.error(f"❌ Render download complet eșuat pentru {platform} după {max_attempts} încercări")
    return {
        'success': False,
        'error': f'❌ {platform}: Toate încercările Render au eșuat. Ultima eroare: {last_error}',
        'title': f'{platform} - Eroare Render',
        'render_optimized': True,
        'attempts': max_attempts
    }


def extract_post_id_from_url(url):
    """Extrage ID-ul postului din URL-ul Reddit"""
    import re
    match = re.search(r'/comments/([a-zA-Z0-9]+)/', url)
    return match.group(1) if match else None

def extract_reddit_video_direct(url, temp_dir):
    """
    Extrage video direct din Reddit folosind proxy-uri și strategii anti-blocking
    Evită problemele de autentificare și blocarea 403
    """
    logger.info(f"🔍 REDDIT EXTRACT START: {url}")
    logger.info(f"📁 Temp directory: {temp_dir}")
    print(f"[DEBUG] REDDIT EXTRACT CALLED: {url}")  # Debug explicit
    
    # Lista de proxy-uri - prioritate pentru conexiunea directă
    proxies_list = [
        None,  # Conexiune directă - prioritate maximă
        None,  # Încercăm din nou conexiunea directă
        None,  # A treia încercare directă
    ]
    
    # User agents reali pentru evitarea detectării
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0'
    ]
    
    # Strategii multiple de acces cu transformări URL corecte - optimizate pentru rapiditate
    strategies = [
        {
            'name': 'Reddit JSON Direct',
            'url_transform': lambda u: u.split('?')[0].rstrip('/') + '.json',  # Remove query params
        },
        {
            'name': 'Old Reddit JSON',
            'url_transform': lambda u: u.split('?')[0].replace('www.reddit.com', 'old.reddit.com').replace('//reddit.com', '//old.reddit.com').rstrip('/') + '.json',
        },
        {
            'name': 'Mobile Reddit',
            'url_transform': lambda u: u.replace('www.reddit.com', 'm.reddit.com').replace('//reddit.com', '//m.reddit.com').rstrip('/') + '.json',
        }
    ]
    
    errors = []
    failed_proxies = set()  # Ține evidența proxy-urilor care au eșuat
    
    # Încearcă fiecare combinație de strategie + proxy + user agent (optimizat)
    for strategy in strategies:
        for proxy in proxies_list:
            # Sari peste proxy-urile care au eșuat deja
            if proxy and proxy.get('http') in failed_proxies:
                continue
                
            for user_agent in user_agents[:3]:  # Limitează la primii 3 user agents pentru eficiență
                try:
                    proxy_info = f"proxy: {proxy['http'] if proxy else 'direct'}" if proxy else "direct"
                    logger.info(f"🔄 {strategy['name']} cu {proxy_info} și UA: {user_agent[:30]}...")
                    
                    # Headers mai autentice pentru evitarea detectării
                    headers = {
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                        'Pragma': 'no-cache'
                    }
                    
                    target_url = strategy['url_transform'](url)
                    logger.debug(f"🎯 Target URL: {target_url}")
                    
                    # Configurează sesiunea cu SSL warnings disabled
                    session = requests.Session()
                    session.headers.update(headers)
                    
                    # Disable SSL warnings pentru proxy-uri
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    
                    response = session.get(
                        target_url,
                        proxies=proxy,
                        timeout=10,  # Timeout redus pentru detectare rapidă a proxy-urilor defecte
                        verify=False,  # Ignoră SSL pentru proxy-uri
                        allow_redirects=True,
                        stream=False
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Succes cu {strategy['name']} prin {proxy_info}")
                        
                        # Procesează răspunsul în funcție de tip
                        if strategy['name'] == 'Reddit RSS':
                            video_url = extract_video_from_rss(response.text)
                        else:
                            try:
                                data = response.json()
                                video_url = extract_video_from_reddit_json(data)
                            except Exception as json_error:
                                logger.error(f"❌ JSON parsing error: {json_error}")
                                logger.error(f"Response content: {response.text[:200]}")
                                continue
                        
                        if video_url:
                            logger.info(f"📹 Video URL găsit: {video_url}")
                            download_result = download_reddit_video(video_url, temp_dir, session, proxy)
                            if download_result['success']:
                                logger.info(f"✅ Reddit video extras cu succes prin {strategy['name']} cu {proxy_info}")
                                return download_result
                            else:
                                logger.warning(f"❌ Descărcarea prin {strategy['name']} a eșuat: {download_result['error']}")
                                # Marchează proxy-ul ca defect dacă descărcarea eșuează
                                if proxy:
                                    failed_proxies.add(proxy.get('http'))
                                    logger.warning(f"❌ Proxy {proxy.get('http')} marcat ca defect după eșec descărcare")
                                continue
                        else:
                            logger.warning(f"Nu s-a găsit video în răspunsul de la {strategy['name']}")
                            continue
                    else:
                        error_msg = f"{strategy['name']} ({proxy_info}): HTTP {response.status_code}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        
                        # Marchează proxy-ul ca defect pentru coduri de eroare specifice
                        if proxy and response.status_code in [403, 429, 502, 503, 504]:
                            failed_proxies.add(proxy.get('http'))
                            logger.warning(f"❌ Proxy {proxy.get('http')} marcat ca defect: HTTP {response.status_code}")
                        
                except Exception as e:
                    error_msg = f"{strategy['name']} ({proxy_info if 'proxy_info' in locals() else 'unknown'}): {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    
                    # Marchează proxy-ul ca defect pentru anumite tipuri de erori
                    if proxy and any(err in str(e).lower() for err in ['connection', 'timeout', 'read timed out', 'incompleteread', 'http 403']):
                        failed_proxies.add(proxy.get('http'))
                        logger.warning(f"❌ Proxy {proxy.get('http')} marcat ca defect: {str(e)[:100]}")
                    
                # Delay între încercări pentru a evita rate limiting
                time.sleep(random.uniform(0.3, 1.5))
    
    # Strategie finală: încearcă fără proxy-uri deloc
    logger.info("🔄 Încercare finală fără proxy-uri...")
    for strategy in strategies[:2]:  # Doar primele 2 strategii pentru fallback
        for user_agent in user_agents[:2]:  # Doar primii 2 user agents
            try:
                logger.info(f"🔄 {strategy['name']} DIRECT (fără proxy) cu UA: {user_agent[:30]}...")
                
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache'
                }
                
                target_url = strategy['url_transform'](url)
                
                response = requests.get(
                    target_url,
                    headers=headers,
                    timeout=10,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    if strategy['name'] == 'Reddit RSS':
                        video_url = extract_video_from_rss(response.text)
                    else:
                        video_url = extract_video_from_reddit_json(response.text)
                    
                    if video_url:
                        logger.info(f"📹 Video URL găsit prin fallback: {video_url}")
                        download_result = download_reddit_video(video_url, temp_dir, None, None)
                        if download_result['success']:
                            logger.info(f"✅ Reddit video extras cu succes prin fallback {strategy['name']}")
                            return download_result
                        
            except Exception as e:
                logger.debug(f"Fallback {strategy['name']} eșuat: {str(e)}")
                continue
    
    # Toate strategiile au eșuat
    logger.error(f"❌ Toate strategiile Reddit au eșuat pentru {url}")
    for error in errors[-5:]:  # Afișează ultimele 5 erori
        logger.error(f"  - {error}")
    
    return {
        'success': False,
        'error': f'❌ Reddit: Toate strategiile au eșuat - {errors[0] if errors else "Eroare necunoscută"}',
        'file_path': None
    }

def extract_video_from_rss(rss_content):
    """Extrage URL-ul video din RSS feed"""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(rss_content)
        
        # Caută link-uri video în RSS
        for item in root.findall('.//item'):
            description = item.find('description')
            if description is not None and description.text:
                # Caută link-uri video în descriere
                import re
                video_patterns = [
                    r'https://v\.redd\.it/[a-zA-Z0-9]+',
                    r'https://i\.redd\.it/[a-zA-Z0-9]+\.mp4',
                    r'https://preview\.redd\.it/[^\s"]+\.mp4'
                ]
                
                for pattern in video_patterns:
                    match = re.search(pattern, description.text)
                    if match:
                        return match.group(0)
        
        return None
    except Exception as e:
        logger.warning(f"Eroare la parsarea RSS: {e}")
        return None

def extract_video_from_reddit_json(data):
    """Extrage URL-ul video din JSON Reddit"""
    try:
        logger.info(f"🔍 Analyzing JSON data type: {type(data)}")
        
        # Verifică dacă data este string (eroare de parsing)
        if isinstance(data, str):
            logger.error(f"❌ Data is string, not JSON: {data[:100]}")
            return None
            
        # Structura JSON poate varia
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        
        if not isinstance(data, dict):
            logger.error(f"❌ Data is not dict: {type(data)}")
            return None
            
        if 'data' in data and 'children' in data['data']:
            for child in data['data']['children']:
                post_data = child.get('data', {})
                
                # Caută video în diverse locații
                if 'secure_media' in post_data and post_data['secure_media']:
                    reddit_video = post_data['secure_media'].get('reddit_video')
                    if reddit_video and 'fallback_url' in reddit_video:
                        return reddit_video['fallback_url']
                
                if 'media' in post_data and post_data['media']:
                    reddit_video = post_data['media'].get('reddit_video')
                    if reddit_video and 'fallback_url' in reddit_video:
                        return reddit_video['fallback_url']
                
                # Caută în preview
                if 'preview' in post_data and 'reddit_video_preview' in post_data['preview']:
                    video_preview = post_data['preview']['reddit_video_preview']
                    if 'fallback_url' in video_preview:
                        return video_preview['fallback_url']
                
                # Caută URL direct
                url = post_data.get('url', '')
                if url and ('v.redd.it' in url or '.mp4' in url):
                    return url
        
        return None
    except Exception as e:
        logger.warning(f"Eroare la extragerea video din JSON: {e}")
        return None

def download_reddit_video(video_url, temp_dir, session=None, proxy=None):
    """Descarcă videoclipul Reddit folosind proxy dacă este disponibil"""
    try:
        logger.info(f"⬇️ Descarc video de la: {video_url}")
        
        # Creează sesiune dacă nu există
        if session is None:
            session = requests.Session()
        
        # Headers pentru descărcare
        download_headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]),
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.reddit.com/',
            'Origin': 'https://www.reddit.com',
            'Range': 'bytes=0-'
        }
        
        # Actualizează headers în sesiune
        session.headers.update(download_headers)
        
        response = session.get(
            video_url, 
            stream=True, 
            timeout=30,
            proxies=proxy,
            verify=False
        )
        
        # Accept both 200 (OK) and 206 (Partial Content) for video streaming
        if response.status_code not in [200, 206]:
            raise Exception(f"HTTP {response.status_code}: {response.reason}")
        
        # Determină extensia fișierului
        content_type = response.headers.get('content-type', '')
        if 'mp4' in content_type:
            ext = '.mp4'
        elif 'webm' in content_type:
            ext = '.webm'
        else:
            ext = '.mp4'  # default
        
        # Salvează fișierul
        timestamp = int(time.time())
        filename = f"reddit_video_{timestamp}{ext}"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(file_path)
        logger.info(f"✅ Video Reddit descărcat cu succes: {file_path} ({file_size} bytes)")
        
        return {
            'success': True,
            'file_path': file_path,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Eroare la descărcarea video Reddit: {e}")
        return {
            'success': False,
            'error': f'❌ Reddit: Eroare la descărcarea video - {str(e)}',
            'file_path': None
        }

def is_supported_url(url):
    """
    Verifică dacă URL-ul este suportat
    """
    supported_domains = [
        # TikTok
        'tiktok.com', 'vm.tiktok.com',
        # Instagram
        'instagram.com', 'www.instagram.com',
        # Facebook
        'facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.watch', 'fb.me',
        # Twitter/X
        'twitter.com', 'www.twitter.com', 'mobile.twitter.com', 'x.com', 'www.x.com', 'mobile.x.com',
        # Threads
        'threads.net', 'www.threads.net', 'threads.com', 'www.threads.com',
        # Pinterest
        'pinterest.com', 'www.pinterest.com', 'pinterest.co.uk', 'pin.it', 'pinterest.fr', 'pinterest.de', 'pinterest.ca',
        # Reddit
        'reddit.com', 'www.reddit.com', 'old.reddit.com', 'redd.it', 'v.redd.it', 'i.redd.it',
        # Vimeo
        'vimeo.com', 'www.vimeo.com', 'player.vimeo.com',
        # Dailymotion
        'dailymotion.com', 'www.dailymotion.com', 'dai.ly', 'geo.dailymotion.com'
    ]
    
    return any(domain in url.lower() for domain in supported_domains)


def get_url_variants(url):
    """Generează variante de URL pentru încercări multiple"""
    platform = get_platform_from_url(url)
    variants = [url]  # URL original
    
    if platform == 'facebook':
        # Variante Facebook
        if '/watch?v=' in url:
            video_id = url.split('/watch?v=')[1].split('&')[0]
            variants.extend([
                f"https://www.facebook.com/share/v/{video_id}/",
                f"https://m.facebook.com/watch?v={video_id}",
                f"https://fb.watch/{video_id}"
            ])
        elif '/share/v/' in url:
            video_id = url.split('/share/v/')[1].split('/')[0]
            variants.extend([
                f"https://www.facebook.com/watch?v={video_id}",
                f"https://m.facebook.com/watch?v={video_id}"
            ])
    
    elif platform == 'twitter':
        # Variante Twitter/X
        variants.extend([
            url.replace('twitter.com', 'x.com'),
            url.replace('x.com', 'twitter.com'),
            url.replace('mobile.twitter.com', 'twitter.com')
        ])
    
    elif platform == 'dailymotion':
        # Variante Dailymotion
        if 'dai.ly/' in url:
            video_id = url.split('dai.ly/')[1]
            variants.append(f"https://www.dailymotion.com/video/{video_id}")
        elif 'dailymotion.com/video/' in url:
            video_id = url.split('/video/')[1].split('?')[0]
            variants.append(f"https://dai.ly/{video_id}")
    
    elif platform == 'pinterest':
        # Variante Pinterest
        if 'pin.it/' in url:
            # Pentru pin.it, încercăm să găsim ID-ul real
            variants.append(url.replace('pin.it/', 'pinterest.com/pin/'))
    
    # Elimină duplicatele și returnează
    return list(dict.fromkeys(variants))

def normalize_url_for_platform(url):
    """Normalizează URL-ul pentru platformă"""
    platform = get_platform_from_url(url)
    
    if platform == 'reddit':
        # Elimină parametrii de query pentru Reddit
        url = url.split('?')[0].rstrip('/')
        # Asigură-te că nu se termină cu .json
        if url.endswith('.json'):
            url = url[:-5]
    
    elif platform == 'tiktok':
        # Normalizează TikTok URLs
        if 'vm.tiktok.com' in url:
            # Pentru link-uri scurte, le lăsăm așa cum sunt
            pass
        else:
            # Elimină parametrii extra
            url = url.split('?')[0]
    
    elif platform == 'instagram':
        # Normalizează Instagram URLs
        url = url.split('?')[0].rstrip('/')
    
    return url

