#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch pentru îmbunătățirea downloader.py cu soluții concrete pentru toate platformele
"""

import os
import sys
import logging
import re
from datetime import datetime

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def apply_enhanced_downloader_patch():
    """Aplică patch-ul îmbunătățit pentru downloader.py"""
    logger.info("🔧 Aplicare patch îmbunătățit pentru downloader.py...")
    
    downloader_path = 'downloader.py'
    
    if not os.path.exists(downloader_path):
        logger.error(f"❌ Fișierul {downloader_path} nu există!")
        return False
    
    # Citește conținutul actual
    with open(downloader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_path = f'downloader.py.backup_enhanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"📄 Backup creat: {backup_path}")
    
    # 1. Îmbunătățește configurațiile yt-dlp pentru toate platformele
    enhanced_configs = '''
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
    """Creează opțiuni yt-dlp îmbunătățite bazate pe platformă"""
    platform = get_platform_from_url(url)
    config = ENHANCED_PLATFORM_CONFIGS.get(platform, {})
    
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
        'http_headers': get_random_headers()
    }
    
    # Adaugă configurații specifice platformei
    if config.get('ydl_opts_extra'):
        ydl_opts.update(config['ydl_opts_extra'])
    
    # Setează user agent aleatoriu din lista platformei
    if config.get('user_agents'):
        import random
        user_agent = random.choice(config['user_agents'])
        ydl_opts['http_headers']['User-Agent'] = user_agent
    
    return ydl_opts

def download_with_enhanced_retry(url, temp_dir, max_attempts=3):
    """Descarcă cu strategii îmbunătățite de retry"""
    platform = get_platform_from_url(url)
    config = ENHANCED_PLATFORM_CONFIGS.get(platform, {})
    
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔄 Încercare {attempt + 1}/{max_attempts} pentru {platform}...")
            
            # Creează opțiuni îmbunătățite
            ydl_opts = create_enhanced_ydl_opts(url, temp_dir)
            
            # Adaugă delay între încercări
            if attempt > 0:
                import time
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
                
                logger.info(f"✅ Descărcare reușită pentru {platform} la încercarea {attempt + 1}")
                
                return {
                    'success': True,
                    'file_path': video_file,
                    'title': info.get('title', 'Video'),
                    'description': info.get('description', ''),
                    'uploader': info.get('uploader', ''),
                    'duration': info.get('duration', 0),
                    'file_size': file_size,
                    'platform': platform,
                    'attempt_number': attempt + 1
                }
                
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            logger.warning(f"❌ Încercarea {attempt + 1} eșuată pentru {platform}: {error_msg[:100]}...")
            
            # Verifică dacă este o eroare critică care nu merită retry
            critical_errors = [
                'private video', 'video unavailable', 'video not found',
                'this video is private', 'content not available',
                'video has been removed', 'account suspended'
            ]
            
            if any(critical in error_msg.lower() for critical in critical_errors):
                logger.info(f"🛑 Eroare critică detectată, oprire retry pentru {platform}")
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

'''
    
    # Găsește locația unde să insereze configurațiile
    insert_pos = content.find('# Lista de User Agents reali')
    if insert_pos == -1:
        insert_pos = content.find('REAL_USER_AGENTS = [')
    
    if insert_pos != -1:
        content = content[:insert_pos] + enhanced_configs + '\n\n' + content[insert_pos:]
        logger.info("✅ Configurații îmbunătățite adăugate")
    else:
        logger.warning("⚠️ Nu s-a găsit locația pentru configurații, adăugare la sfârșitul fișierului")
        content += '\n\n' + enhanced_configs
    
    # 2. Îmbunătățește funcția download_video
    download_function_pattern = r'(def download_video\([^)]+\):[^\n]*\n)(\s+)"""[^"]*"""\n'
    download_match = re.search(download_function_pattern, content, re.DOTALL)
    
    if download_match:
        indent = download_match.group(2)
        enhanced_download_start = f'''{download_match.group(1)}{download_match.group(2)}"""\n{indent}Descarcă un video cu strategii îmbunătățite pentru toate platformele\n{indent}Returnează un dicționar cu rezultatul\n{indent}"""\n{indent}logger.info(f"=== ENHANCED DOWNLOAD_VIDEO START === URL: {{url}}")\n{indent}\n{indent}try:\n{indent}    # Validează URL-ul înainte de procesare\n{indent}    logger.info(f"=== ENHANCED DOWNLOAD_VIDEO Validating URL ===")\n{indent}    is_valid, validation_msg = validate_url(url)\n{indent}    if not is_valid:\n{indent}        logger.error(f"=== ENHANCED DOWNLOAD_VIDEO URL Invalid === {{validation_msg}}")\n{indent}        return {{\n{indent}            'success': False,\n{indent}            'error': f'❌ URL invalid: {{validation_msg}}',\n{indent}            'title': 'N/A'\n{indent}        }}\n{indent}\n{indent}    # Creează directorul temporar\n{indent}    temp_dir = validate_and_create_temp_dir()\n{indent}    if not temp_dir:\n{indent}        return {{\n{indent}            'success': False,\n{indent}            'error': '❌ Nu s-a putut crea directorul temporar',\n{indent}            'title': 'N/A'\n{indent}        }}\n{indent}\n{indent}    logger.info(f"=== ENHANCED DOWNLOAD_VIDEO Temp dir created: {{temp_dir}} ===")\n{indent}\n{indent}    # Folosește strategia îmbunătățită de descărcare\n{indent}    result = download_with_enhanced_retry(url, temp_dir, max_attempts=3)\n{indent}    \n{indent}    if result['success']:\n{indent}        logger.info(f"✅ ENHANCED DOWNLOAD SUCCESS: {{result['title']}}")\n{indent}    else:\n{indent}        logger.error(f"❌ ENHANCED DOWNLOAD FAILED: {{result['error']}}")\n{indent}    \n{indent}    return result\n{indent}\n{indent}except Exception as e:\n{indent}    logger.error(f"=== ENHANCED DOWNLOAD_VIDEO Exception === {{str(e)}}")\n{indent}    import traceback\n{indent}    logger.error(f"=== ENHANCED DOWNLOAD_VIDEO Traceback === {{traceback.format_exc()}}")\n{indent}    return {{\n{indent}        'success': False,\n{indent}        'error': f'❌ Eroare neașteptată: {{str(e)}}',\n{indent}        'title': 'N/A'\n{indent}    }}\n{indent}\n{indent}finally:\n{indent}    # Nu șterge temp_dir aici - va fi șters după trimiterea fișierului\n{indent}    pass\n\n'''
        
        # Înlocuiește funcția download_video existentă
        old_function_end = content.find('finally:', download_match.end())
        if old_function_end != -1:
            # Găsește sfârșitul funcției
            lines = content[old_function_end:].split('\n')
            function_end = old_function_end
            for i, line in enumerate(lines):
                if line and not line.startswith(' ') and not line.startswith('\t') and i > 0:
                    function_end = old_function_end + len('\n'.join(lines[:i]))
                    break
            else:
                function_end = len(content)
            
            content = content[:download_match.start()] + enhanced_download_start + content[function_end:]
            logger.info("✅ Funcția download_video îmbunătățită")
        else:
            logger.warning("⚠️ Nu s-a putut găsi sfârșitul funcției download_video")
    else:
        logger.warning("⚠️ Nu s-a găsit funcția download_video")
    
    # 3. Adaugă funcții de suport pentru URL variants
    url_variants_functions = '''
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

'''
    
    # Adaugă funcțiile de suport
    content += '\n\n' + url_variants_functions
    logger.info("✅ Funcții de suport pentru URL variants adăugate")
    
    # Salvează fișierul modificat
    with open(downloader_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"✅ Patch îmbunătățit aplicat cu succes în {downloader_path}")
    return True

def main():
    """Funcția principală"""
    logger.info(f"🚀 Începere aplicare patch îmbunătățit la {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        success = apply_enhanced_downloader_patch()
        
        if success:
            logger.info("\n" + "="*60)
            logger.info("✅ PATCH ÎMBUNĂTĂȚIT APLICAT CU SUCCES!")
            logger.info("="*60)
            logger.info("\n🎯 Îmbunătățiri implementate:")
            logger.info("  1. ✅ Configurații optimizate pentru toate platformele")
            logger.info("  2. ✅ Strategii de retry îmbunătățite")
            logger.info("  3. ✅ User-agent rotation per platformă")
            logger.info("  4. ✅ Gestionare îmbunătățită a erorilor")
            logger.info("  5. ✅ URL normalization și variants")
            logger.info("  6. ✅ Timeout-uri și retry logic optimizate")
            logger.info("  7. ✅ Geo-bypass și SSL bypass pentru toate platformele")
            logger.info("\n🔄 Următorii pași:")
            logger.info("  1. Testează din nou toate platformele")
            logger.info("  2. Verifică îmbunătățirile în acțiune")
            logger.info("  3. Monitorizează rata de succes")
            return 0
        else:
            logger.error("❌ Aplicarea patch-ului a eșuat")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Eroare în timpul aplicării patch-ului: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())