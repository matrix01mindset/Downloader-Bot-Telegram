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
from datetime import datetime, timedelta

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
            'format': 'best[filesize<512M][height<=720]/best[height<=720]/best',
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
    logger.info("🔄 STEP 1: Încercare cu sistemul de rotare URL...")
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
            'format': 'best[filesize<512M][height<=720]/best[height<=720]/best[filesize<512M]/best',
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
            'format': 'best[filesize<512M][height<=720]/best[height<=720]/best[filesize<512M]/best',
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
            'format': 'best[filesize<512M][height<=480]/best[height<=480]/best[filesize<512M]/best',
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
            'format': 'best[filesize<512M][height<=480]/best[height<=480]/best[filesize<512M]/best',
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
        'tiktok.com', 'instagram.com', 
        'facebook.com', 'fb.watch', 'twitter.com', 'x.com'
    ]
    
    if not any(domain in url.lower() for domain in supported_domains):
        return False, "Domeniu nesuportat"
    
    # Verifică dacă URL-ul nu este corupt (ex: doar "w")
    if len(url) < 15 or not url.startswith(('http://', 'https://')):
        return False, "URL corupt sau incomplet"
    
    return True, "URL valid"

def download_video(url, output_path=None):
    """
    Descarcă un video de pe YouTube, TikTok, Instagram sau Facebook
    Returnează un dicționar cu rezultatul
    """
    logger.info(f"=== DOWNLOAD_VIDEO START === URL: {url}")
    
    try:
        # Validează URL-ul înainte de procesare
        logger.info(f"=== DOWNLOAD_VIDEO Validating URL ===")
        is_valid, validation_msg = validate_url(url)
        if not is_valid:
            logger.error(f"=== DOWNLOAD_VIDEO URL Invalid === {validation_msg}")
            return {
                'success': False,
                'error': f'❌ URL invalid: {validation_msg}',
                'title': 'N/A'
            }
        
        logger.info(f"=== DOWNLOAD_VIDEO URL Valid, creating temp dir ===")
        # Creează directorul temporar cu fallback pentru Render
        try:
            # Încearcă să folosească /tmp pe Render sau directorul temporar implicit
            temp_base = os.environ.get('TMPDIR', os.environ.get('TEMP', '/tmp'))
            if not os.path.exists(temp_base):
                temp_base = tempfile.gettempdir()
            temp_dir = tempfile.mkdtemp(dir=temp_base)
            logger.info(f"=== DOWNLOAD_VIDEO Temp dir created: {temp_dir} ===")
        except Exception as temp_error:
            logger.warning(f"Eroare la crearea directorului temporar: {temp_error}")
            # Fallback la directorul curent
            temp_dir = os.path.join(os.getcwd(), 'temp_downloads')
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(f"=== DOWNLOAD_VIDEO Fallback temp dir: {temp_dir} ===")
    
        if output_path is None:
            output_path = os.path.join(temp_dir, "%(title)s.%(ext)s")
        
        # YouTube este dezactivat - returnează eroare
        if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            return {
                'success': False,
                'error': '❌ YouTube nu este suportat momentan. Te rog să folosești alte platforme: Facebook, Instagram, TikTok, Twitter, etc.',
                'title': 'YouTube - Nu este suportat'
            }
        else:
            # Normalizează URL-urile Facebook înainte de descărcare
            if 'facebook.com' in url.lower() or 'fb.watch' in url.lower():
                url = normalize_facebook_url(url)
                logger.info(f"URL procesat pentru Facebook: {url}")
            
            # Configurație pentru alte platforme
            ydl_opts = {
                'outtmpl': os.path.join(temp_dir, '%(title).100s.%(ext)s'),  # Limitează titlul la 100 caractere
                'format': 'best[filesize<512M][height<=720]/best[height<=720]/best[filesize<512M]/best',
                'quiet': True,
                'noplaylist': True,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'restrictfilenames': True,  # Restricționează caracterele în nume
                'windowsfilenames': True,   # Compatibilitate Windows
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
                'extractor_retries': 5,
                'fragment_retries': 5,
                'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)},
                'ignoreerrors': False,
                'extract_flat': False,
                'skip_download': False,
                'socket_timeout': 30,
                'retries': 3,
            }
    
        logger.info("=== DOWNLOAD_VIDEO Creating YoutubeDL instance ===")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrage informații despre video
            logger.info("=== DOWNLOAD_VIDEO Extracting video info ===")
            info = ydl.extract_info(url, download=False)
            logger.info(f"=== DOWNLOAD_VIDEO Info extracted === Title: {info.get('title', 'N/A')}")
            logger.info(f"=== DOWNLOAD_VIDEO Info extracted === Duration: {info.get('duration', 0)}")
            logger.info(f"=== DOWNLOAD_VIDEO Info extracted === Uploader: {info.get('uploader', 'N/A')}")
            
            # Extrage titlul și alte informații
            title = info.get('title', 'video')
            description = info.get('description', '')
            uploader = info.get('uploader', '')
            duration = info.get('duration', 0)
            
            # Îmbunătățește titlul pentru diferite platforme
            if 'instagram.com' in url.lower():
                # Pentru Instagram, încearcă să găsești un titlu mai bun
                if description and len(description) > len(title):
                    # Ia primele 100 de caractere din descriere ca titlu
                    title = description[:100].strip()
                    if len(description) > 100:
                        title += '...'
                elif uploader:
                    title = f"Video de la {uploader}"
            
            elif 'tiktok.com' in url.lower():
                # Pentru TikTok, încearcă să găsești un titlu mai bun
                if description and len(description) > len(title):
                    # Ia primele 100 de caractere din descriere ca titlu
                    title = description[:100].strip()
                    if len(description) > 100:
                        title += '...'
                elif uploader:
                    title = f"TikTok de la {uploader}"
            
            # Curăță titlul de caractere speciale problematice și emoticoane
            title = clean_title(title)
            if not title or title == 'video':
                title = f"Video de pe {url.split('/')[2] if '/' in url else 'platformă necunoscută'}"
            
            # Verifică dacă videoul nu este prea lung (max 3 ore pentru fișiere mai mari)
            if duration and duration > 10800:  # 3 ore = 10800 secunde
                return {
                    'success': False,
                    'error': 'Videoul este prea lung (max 3 ore)',
                    'title': title
                }
            
            # Descarcă videoul
            try:
                logger.info("Încep descărcarea video-ului...")
                ydl.download([url])
                logger.info("Descărcare completă!")
            except Exception as download_error:
                logger.error(f"Eroare la descărcare: {download_error}")
                error_str = str(download_error).lower()
                # YouTube este dezactivat - returnează eroare
                if ('youtube.com' in url.lower() or 'youtu.be' in url.lower()):
                    return {
                        'success': False,
                        'error': '❌ YouTube nu este suportat momentan. Te rog să folosești alte platforme: Facebook, Instagram, TikTok, Twitter, etc.',
                        'title': title
                    }
                # Încearcă cu opțiuni alternative pentru Facebook - UPDATED cu patch
                elif 'facebook.com' in url.lower() or 'fb.watch' in url.lower():
                    error_str = str(download_error).lower()
                    logger.warning(f"Facebook error în download_video: {error_str[:100]}...")
                    
                    if 'cannot parse data' in error_str:
                        logger.warning(f"Facebook parsing error detectat pentru URL: {url}")
                        # Încearcă fallback cu patch înainte de a returna eroare
                        fallback_result = try_facebook_fallback(url, output_path, title)
                        if fallback_result['success']:
                            # Adaugă informații despre rotație dacă sunt disponibile
                            if 'rotation_info' in fallback_result:
                                fallback_result['success_message'] = f"✅ Facebook: {fallback_result['rotation_info']}"
                            return fallback_result
                        else:
                            # Mesajul de eroare va fi deja detaliat din try_facebook_fallback
                            return fallback_result
                    elif 'unsupported url' in error_str:
                        logger.warning(f"Facebook URL nesuportat în download_video: {url}")
                        # Încearcă normalizarea URL-ului și fallback
                        normalized_url = normalize_facebook_url(url)
                        if normalized_url != url:
                            logger.info(f"Încercare cu URL normalizat: {normalized_url}")
                            fallback_result = try_facebook_fallback(normalized_url, output_path, title)
                            if fallback_result['success'] and 'rotation_info' in fallback_result:
                                fallback_result['success_message'] = f"✅ Facebook: {fallback_result['rotation_info']}"
                            return fallback_result
                        else:
                            # Încearcă fallback chiar și pentru URL-uri nesuportate
                            fallback_result = try_facebook_fallback(url, output_path, title)
                            if fallback_result['success'] and 'rotation_info' in fallback_result:
                                fallback_result['success_message'] = f"✅ Facebook: {fallback_result['rotation_info']}"
                            return fallback_result
                    else:
                        # Pentru orice altă eroare Facebook, încearcă fallback cu patch
                        fallback_result = try_facebook_fallback(url, output_path, title)
                        if fallback_result['success'] and 'rotation_info' in fallback_result:
                            fallback_result['success_message'] = f"✅ Facebook: {fallback_result['rotation_info']}"
                        return fallback_result
                else:
                    raise download_error
            
            # Pentru YouTube, fișierele au fost deja găsite în bucla de încercări
            # Pentru alte platforme, găsește fișierul descărcat în directorul temporar
            downloaded_files = []
            if not ('youtube.com' in url.lower() or 'youtu.be' in url.lower()):
                downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
                downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
            
            if not downloaded_files:
                return {
                    'success': False,
                    'error': 'Fișierul nu a fost găsit după descărcare',
                    'title': title
                }
            
            # Ia primul fișier găsit (ar trebui să fie singurul)
            downloaded_file = downloaded_files[0]
            
            # Verifică dimensiunea fișierului (Telegram Bot API are limită strictă de 50MB)
            file_size = os.path.getsize(downloaded_file)
            max_size = 45 * 1024 * 1024  # 45MB în bytes (buffer pentru limita Telegram de 50MB)
            size_mb = file_size / (1024*1024) if isinstance(file_size, (int, float)) else 0

            if file_size > max_size:
                os.remove(downloaded_file)
                return {
                    'success': False,
                    'error': f'❌ Fișierul este prea mare ({size_mb:.1f}MB).\n\n📊 Dimensiune: {size_mb:.1f}MB\n⚠️ Limita Telegram: 50MB (pentru bot-uri)\n\n💡 Încearcă un clip mai scurt sau o calitate mai mică.',
                    'title': title
                }
            
            logger.info(f"=== DOWNLOAD_VIDEO SUCCESS === File: {downloaded_file}")
            return {
                 'success': True,
                 'file_path': downloaded_file,
                 'title': title,
                 'description': description,
                 'uploader': uploader,
                 'duration': duration,
                 'file_size': file_size
             }
            
    except yt_dlp.DownloadError as e:
        logger.error(f"=== DOWNLOAD_VIDEO DownloadError === {str(e)}")
        error_msg = str(e).lower()
        
        # Gestionare specifică pentru YouTube - dezactivat
        if ('youtube' in url.lower() or 'youtu.be' in url.lower()):
            return {
                'success': False,
                'error': '❌ YouTube nu este suportat momentan. Te rog să folosești alte platforme: Facebook, Instagram, TikTok, Twitter, etc.',
                'title': 'N/A'
            }
        elif 'rate' in error_msg and 'limit' in error_msg:
            return {
                'success': False,
                'error': '❌ Instagram/TikTok: Limită de rată atinsă. Încearcă din nou în câteva minute.',
                'title': 'N/A'
            }
        elif 'login' in error_msg or 'authentication' in error_msg or 'cookies' in error_msg:
            help_msg = '\n\nPentru Instagram: Folosește --cookies-from-browser sau --cookies pentru autentificare.'
            help_msg += '\nVezi: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
            return {
                'success': False,
                'error': f'❌ Instagram/TikTok: Conținut privat sau necesită autentificare.{help_msg}',
                'title': 'N/A'
            }
        elif 'not available' in error_msg:
            return {
                'success': False,
                'error': '❌ Conținutul nu este disponibil sau a fost șters.',
                'title': 'N/A'
            }
        elif 'cannot parse data' in error_msg or 'parse' in error_msg:
            # Pentru erori de parsare Facebook, încearcă patch-ul cu rotație
            if 'facebook' in error_msg and ('facebook.com' in url.lower() or 'fb.watch' in url.lower()):
                logger.info("Încercare patch Facebook cu rotație pentru eroare de parsare...")
                try:
                    # Încearcă fallback cu patch și rotație pentru DownloadError
                    temp_output = os.path.join(temp_dir, "%(title)s.%(ext)s")
                    fallback_result = try_facebook_fallback(url, temp_output, 'Facebook Video')
                    if fallback_result['success']:
                        # Adaugă informații despre rotație dacă sunt disponibile
                        if 'rotation_info' in fallback_result:
                            fallback_result['success_message'] = f"✅ Facebook: {fallback_result['rotation_info']}"
                        return fallback_result
                    else:
                        # Mesajul de eroare va fi deja detaliat din try_facebook_fallback
                        return fallback_result
                except Exception as fallback_error:
                    logger.warning(f"Fallback Facebook eșuat în DownloadError: {fallback_error}")
                    return {
                        'success': False,
                        'error': '❌ Facebook: Eroare de parsare a datelor (DownloadError). Patch-ul Facebook a fost aplicat dar problema persistă.\n\n🔧 Cauze posibile:\n• URL Facebook în format nou nesuportat\n• Conținut privat sau restricționat\n• Probleme temporare cu API Facebook\n\n💡 Încearcă:\n• Un alt link Facebook\n• Link în format facebook.com/watch?v=\n• Contactează adminul pentru suport',
                        'title': 'N/A'
                    }
            
            return {
                'success': False,
                'error': '❌ Facebook: Eroare de parsare a datelor. Acest lucru poate fi cauzat de:\n• Emoticoane sau caractere speciale în titlu\n• Conținut privat sau restricționat\n• Probleme temporare cu platforma\n\n💡 Încearcă din nou în câteva minute.',
                'title': 'N/A'
            }
        elif 'facebook' in error_msg and ('error' in error_msg or 'failed' in error_msg):
            return {
                'success': False,
                'error': '❌ Facebook: Eroare la accesarea conținutului. Patch-ul Facebook aplicat.\n\n🔧 Verifică:\n• Link-ul este public și valid\n• Nu este conținut restricționat\n• Formatul URL este corect\n\n💡 Încearcă un alt link Facebook.',
                'title': 'N/A'
            }
        else:
            return {
                'success': False,
                'error': f'❌ Eroare la descărcare: {str(e)}',
                'title': 'N/A'
            }
    except Exception as e:
        logger.error(f"=== DOWNLOAD_VIDEO Exception === {str(e)}")
        import traceback
        logger.error(f"=== DOWNLOAD_VIDEO Traceback === {traceback.format_exc()}")
        return {
            'success': False,
            'error': f'❌ Eroare neașteptată: {str(e)}',
            'title': 'N/A'
        }
    
    finally:
        # Cleanup temp dir - întotdeauna executat
        try:
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"=== DOWNLOAD_VIDEO Temp dir cleaned up: {temp_dir} ===")
        except Exception as cleanup_error:
            logger.warning(f"Eroare la cleanup temp dir: {cleanup_error}")

def is_supported_url(url):
    """
    Verifică dacă URL-ul este suportat
    """
    supported_domains = [
        'tiktok.com', 'instagram.com', 
        'facebook.com', 'fb.watch', 'twitter.com', 'x.com'
    ]
    
    return any(domain in url.lower() for domain in supported_domains)