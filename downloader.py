import yt_dlp
import os
import tempfile
import time
import glob
import re
import unicodedata
import random
import json
from datetime import datetime, timedelta

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
    """Generează cookies simulate pentru YouTube"""
    # Simulează cookies de sesiune YouTube reali
    cookies = {
        'CONSENT': f'YES+cb.20210328-17-p0.en+FX+{random.randint(100, 999)}',
        'VISITOR_INFO1_LIVE': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=22)),
        'YSC': ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_', k=16)),
        'PREF': f'f4=4000000&tz=Europe.Bucharest&f5=30000&f6=8&f7=100',
        'GPS': '1',
    }
    return cookies

def create_youtube_session():
    """Creează o sesiune YouTube cu configurații anti-detecție"""
    headers = get_random_headers()
    cookies = get_youtube_cookies()
    
    # Configurații avansate pentru a evita detecția
    session_config = {
        'http_headers': headers,
        'cookiefile': None,  # Nu salvăm cookies pe disk
        'nocheckcertificate': False,
        'prefer_insecure': False,
        'cachedir': False,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': False,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'age_limit': None,
        'sleep_interval': random.uniform(1.5, 3.5),  # Pauză randomizată
        'max_sleep_interval': random.uniform(8, 15),
        'sleep_interval_subtitles': random.uniform(1, 3),
        'socket_timeout': random.randint(90, 150),
        'retries': 2,
        'extractor_retries': 3,
        'fragment_retries': 5,
        'retry_sleep_functions': {
            'http': lambda n: min(2 ** n + random.uniform(0.5, 2), 30),
            'fragment': lambda n: min(2 ** n + random.uniform(0.5, 2), 30)
        },
        # Simulează comportament de browser real
        'extract_comments': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'embed_subs': False,
        'writeinfojson': False,
        'writethumbnail': False,
        'writedescription': False,
        'writeannotations': False,
    }
    
    # Adaugă cookies în format yt-dlp
    cookie_string = '; '.join([f'{k}={v}' for k, v in cookies.items()])
    session_config['http_headers']['Cookie'] = cookie_string
    
    return session_config

def is_youtube_bot_detection_error(error_msg):
    """Detectează dacă eroarea este cauzată de sistemul anti-bot YouTube"""
    bot_detection_keywords = [
        'HTTP Error 429',
        'Too Many Requests',
        'rate limit',
        'bot',
        'automated',
        'suspicious',
        'blocked',
        'forbidden',
        'access denied',
        'captcha',
        'verification',
        'unusual traffic',
        'quota exceeded',
        'service unavailable',
        'temporarily unavailable',
        'sign in to confirm',
        'video unavailable',
        'private video',
        'age-restricted',
        'region blocked'
    ]
    
    error_lower = str(error_msg).lower()
    return any(keyword in error_lower for keyword in bot_detection_keywords)

def get_youtube_retry_strategy(attempt_number):
    """Returnează strategia de retry bazată pe numărul încercării"""
    strategies = [
        {  # Prima încercare - configurații standard
            'format': 'best[height<=720]/best',
            'sleep_multiplier': 1.0,
            'geo_country': 'US'
        },
        {  # A doua încercare - calitate mai mică
            'format': 'best[height<=480]/best',
            'sleep_multiplier': 1.5,
            'geo_country': 'GB'
        },
        {  # A treia încercare - calitate minimă
            'format': 'worst[height<=360]/worst',
            'sleep_multiplier': 2.0,
            'geo_country': 'CA'
        }
    ]
    
    if attempt_number < len(strategies):
        return strategies[attempt_number]
    else:
        # Pentru încercări suplimentare, folosește ultima strategie cu delay crescut
        last_strategy = strategies[-1].copy()
        last_strategy['sleep_multiplier'] = 3.0 + (attempt_number - len(strategies))
        last_strategy['geo_country'] = random.choice(['AU', 'NZ', 'IE', 'NL'])
        return last_strategy

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

def try_youtube_fallback(url, output_path, title):
    """
    Încearcă descărcarea YouTube cu opțiuni ultra-conservative și anti-detecție pentru a evita rate limiting
    """
    # Creează o sesiune cu configurații anti-detecție pentru fallback
    session_config = create_youtube_session()
    
    fallback_opts = {
        'outtmpl': output_path,
        'format': 'worst[height<=360]/worst[height<=240]/worst',  # Calitate foarte mică
        'quiet': True,
        'noplaylist': True,
        'extractaudio': False,
        'embed_subs': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        # Folosește headers anti-detecție din sesiune
        'http_headers': session_config['http_headers'],
        'extractor_retries': 2,  # Încercări moderate
        'fragment_retries': 3,
        'retry_sleep_functions': {
            'http': lambda n: min(5 ** n + random.uniform(1, 3), 120),  # Delay randomizat
            'fragment': lambda n: min(5 ** n + random.uniform(1, 3), 120)
        },
        'socket_timeout': random.randint(90, 150),  # Timeout randomizat
        'retries': 1,  # O reîncercare
        'sleep_interval': random.uniform(8, 12),  # Pauză randomizată între cereri
        'max_sleep_interval': random.uniform(25, 35),
        'sleep_interval_subtitles': random.uniform(5, 8),
        'nocheckcertificate': False,
        'prefer_insecure': False,
        'cachedir': False,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': False,
        'geo_bypass': True,
        'geo_bypass_country': random.choice(['US', 'GB', 'CA', 'AU']),  # Țară randomizată
        # Configurații anti-detecție suplimentare
        'age_limit': None,
        'writeinfojson': False,
        'writethumbnail': False,
        'writedescription': False,
        'writeannotations': False,
        'extract_comments': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            # Adaugă un delay randomizat înainte de încercare pentru a simula comportament uman
            time.sleep(random.uniform(10, 20))
            ydl.download([url])
            
            # Găsește fișierul descărcat
            temp_dir = os.path.dirname(output_path)
            downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
            downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
            
            if downloaded_files:
                return {
                    'success': True,
                    'file_path': downloaded_files[0],
                    'title': title,
                    'description': '',
                    'uploader': '',
                    'duration': 0,
                    'file_size': os.path.getsize(downloaded_files[0])
                }
    except Exception:
        pass
    
    return {
        'success': False,
        'error': '❌ YouTube: Nu s-a putut descărca nici cu opțiunile alternative. Încearcă din nou mai târziu.',
        'title': title
    }

def try_facebook_fallback(url, output_path, title):
    """
    Încearcă descărcarea Facebook cu opțiuni alternative
    """
    # Configurație alternativă pentru Facebook
    fallback_opts = {
        'outtmpl': output_path,
        'format': 'worst[height<=480]/worst',  # Calitate mai mică pentru compatibilitate
        'quiet': True,
        'noplaylist': True,
        'extractaudio': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        },
        'extractor_retries': 2,
        'fragment_retries': 2,
        'socket_timeout': 15,
        'retries': 2,
        'ignoreerrors': True,
        # Opțiuni specifice pentru probleme de parsare
        'extract_flat': True,
        'skip_download': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            # Încearcă să descarce cu opțiuni alternative
            ydl.download([url])
            
            # Găsește fișierul descărcat
            temp_dir = os.path.dirname(output_path)
            downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
            downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
            
            if downloaded_files:
                downloaded_file = downloaded_files[0]
                file_size = os.path.getsize(downloaded_file)
                
                return {
                    'success': True,
                    'file_path': downloaded_file,
                    'title': title or "Video Facebook",
                    'description': "Descărcat cu opțiuni alternative",
                    'uploader': "Facebook",
                    'duration': 0,
                    'file_size': file_size
                }
            else:
                return {
                    'success': False,
                    'error': '❌ Facebook: Nu s-a putut descărca videoul cu opțiunile alternative.',
                    'title': title or 'N/A'
                }
                
    except Exception as e:
        return {
            'success': False,
            'error': f'❌ Facebook: Eroare la încercarea alternativă: {str(e)}',
            'title': title or 'N/A'
        }

def download_video(url, output_path=None):
    """
    Descarcă un video de pe YouTube, TikTok, Instagram sau Facebook
    Returnează un dicționar cu rezultatul
    """
    if output_path is None:
        # Creează un director temporar unic
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "%(title)s.%(ext)s")
    
    # Configurație specifică pentru YouTube cu măsuri anti-detecție avansate
    if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
        # Creează o sesiune cu configurații anti-detecție
        session_config = create_youtube_session()
        
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'worst[height<=480]/worst',  # Calitate mai mică pentru a reduce load-ul
            'quiet': True,
            'noplaylist': True,
            'extractaudio': False,
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            # Folosește configurațiile anti-detecție din sesiune
            'http_headers': session_config['http_headers'],
            'extractor_retries': session_config.get('extractor_retries', 3),
            'fragment_retries': session_config.get('fragment_retries', 5),
            'retry_sleep_functions': session_config.get('retry_sleep_functions', {
                'http': lambda n: min(3 ** n, 60),
                'fragment': lambda n: min(3 ** n, 60)
            }),
            'socket_timeout': session_config.get('socket_timeout', 120),
            'retries': session_config.get('retries', 2),
            'sleep_interval': session_config.get('sleep_interval', 2),
            'max_sleep_interval': session_config.get('max_sleep_interval', 10),
            'sleep_interval_subtitles': session_config.get('sleep_interval_subtitles', 2),
            # Configurații suplimentare anti-detecție
            'geo_bypass': session_config.get('geo_bypass', True),
            'geo_bypass_country': session_config.get('geo_bypass_country', 'US'),
            'nocheckcertificate': False,
            'prefer_insecure': False,
            'cachedir': False,  # Dezactivează cache-ul
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'age_limit': None,
            # Evită salvarea de metadate care pot fi detectate
            'writeinfojson': False,
            'writethumbnail': False,
            'writedescription': False,
            'writeannotations': False,
            'extract_comments': False,
        }
    else:
        # Configurație pentru alte platforme
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best[height<=720]/best',
            'quiet': True,
            'noplaylist': True,
            'extractaudio': False,
            'audioformat': 'mp3',
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
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
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrage informații despre video
            info = ydl.extract_info(url, download=False)
            
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
                ydl.download([url])
            except Exception as download_error:
                error_str = str(download_error).lower()
                # Încearcă cu strategii adaptive pentru YouTube la detectarea erorilor anti-bot
                if ('youtube.com' in url.lower() or 'youtu.be' in url.lower()) and is_youtube_bot_detection_error(str(download_error)):
                    print(f"Eroare anti-bot YouTube detectată, încerc strategii alternative: {str(download_error)}")
                    
                    # Încearcă mai multe strategii de retry
                    for attempt in range(3):
                        try:
                            print(f"Încercare YouTube #{attempt + 1} cu strategie adaptivă")
                            strategy = get_youtube_retry_strategy(attempt)
                            
                            # Creează o nouă sesiune pentru fiecare încercare
                            session_config = create_youtube_session()
                            
                            # Configurații adaptive bazate pe strategie
                            adaptive_opts = {
                                'format': strategy['format'],
                                'outtmpl': output_path,
                                'quiet': True,
                                'no_warnings': True,
                                'extractaudio': False,
                                'embed_subs': False,
                                'writesubtitles': False,
                                'writeautomaticsub': False,
                                'noplaylist': True,
                                'http_headers': session_config['http_headers'],
                                'retries': 1,
                                'extractor_retries': 2,
                                'fragment_retries': 3,
                                'socket_timeout': random.randint(120, 180),
                                'sleep_interval': random.uniform(5, 10) * strategy['sleep_multiplier'],
                                'max_sleep_interval': random.uniform(20, 40) * strategy['sleep_multiplier'],
                                'sleep_interval_subtitles': random.uniform(3, 6) * strategy['sleep_multiplier'],
                                'retry_sleep_functions': {
                                    'http': lambda n: min((7 ** n) * strategy['sleep_multiplier'] + random.uniform(2, 5), 300),
                                    'fragment': lambda n: min((7 ** n) * strategy['sleep_multiplier'] + random.uniform(2, 5), 300)
                                },
                                'geo_bypass': True,
                                'geo_bypass_country': strategy['geo_country'],
                                'cachedir': False,
                                'nocheckcertificate': False,
                                'prefer_insecure': False,
                                'age_limit': None,
                                'extract_flat': False,
                                'ignoreerrors': False,
                                'writeinfojson': False,
                                'writethumbnail': False,
                                'writedescription': False,
                                'writeannotations': False,
                                'extract_comments': False,
                            }
                            
                            # Pauză adaptivă înainte de încercare
                            delay = random.uniform(10, 25) * strategy['sleep_multiplier']
                            print(f"Aștept {delay:.1f} secunde înainte de încercare...")
                            time.sleep(delay)
                            
                            with yt_dlp.YoutubeDL(adaptive_opts) as ydl_retry:
                                ydl_retry.download([url])
                                
                            # Verifică dacă descărcarea a reușit
                            temp_dir = os.path.dirname(output_path)
                            downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
                            downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
                            
                            if downloaded_files:
                                print(f"Descărcare YouTube reușită cu strategia #{attempt + 1}")
                                break
                                
                        except Exception as retry_error:
                            print(f"Încercarea #{attempt + 1} eșuată: {str(retry_error)}")
                            if attempt == 2:  # Ultima încercare
                                print("Toate strategiile YouTube au eșuat, încerc fallback final")
                                return try_youtube_fallback(url, output_path, title)
                            continue
                # Încearcă cu opțiuni alternative pentru YouTube la alte erori
                elif ('youtube.com' in url.lower() or 'youtu.be' in url.lower()):
                    if ('429' in error_str or 'too many requests' in error_str or 'rate' in error_str or 
                        'unavailable' in error_str or 'private' in error_str or 'blocked' in error_str or
                        'sign in' in error_str or 'login' in error_str or 'bot' in error_str):
                        return try_youtube_fallback(url, output_path, title)
                # Încearcă cu opțiuni alternative pentru Facebook
                elif 'facebook.com' in url.lower() or 'fb.watch' in url.lower():
                    return try_facebook_fallback(url, output_path, title)
                else:
                    raise download_error
            
            # Găsește fișierul descărcat în directorul temporar
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
            
            # Verifică dimensiunea fișierului
            file_size = os.path.getsize(downloaded_file)
            max_size = 550 * 1024 * 1024  # 550MB în bytes

            if file_size > max_size:
                os.remove(downloaded_file)
                size_mb = file_size / (1024*1024) if isinstance(file_size, (int, float)) else 0
                return {
                    'success': False,
                    'error': f'Fișierul este prea mare ({size_mb:.1f}MB). Limita este 550MB.',
                    'title': title
                }
            
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
        error_msg = str(e).lower()
        
        # Gestionare specifică pentru YouTube HTTP 429
        if ('youtube' in url.lower() or 'youtu.be' in url.lower()) and ('429' in error_msg or 'too many requests' in error_msg or ('rate' in error_msg and 'limit' in error_msg)):
            return {
                'success': False,
                'error': '❌ YouTube: Prea multe cereri. YouTube a limitat temporar accesul.\n\n💡 Soluții:\n• Încearcă din nou în 10-15 minute\n• Folosește un VPN dacă problema persistă\n• Verifică că link-ul este valid și public',
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
            return {
                'success': False,
                'error': '❌ Facebook: Eroare de parsare a datelor. Acest lucru poate fi cauzat de:\n• Emoticoane sau caractere speciale în titlu\n• Conținut privat sau restricționat\n• Probleme temporare cu platforma\n\n💡 Încearcă din nou în câteva minute.',
                'title': 'N/A'
            }
        elif 'facebook' in error_msg and ('error' in error_msg or 'failed' in error_msg):
            return {
                'success': False,
                'error': '❌ Facebook: Eroare la accesarea conținutului. Verifică că link-ul este public și valid.',
                'title': 'N/A'
            }
        else:
            return {
                'success': False,
                'error': f'❌ Eroare la descărcare: {str(e)}',
                'title': 'N/A'
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'❌ Eroare neașteptată: {str(e)}',
            'title': 'N/A'
        }

def is_supported_url(url):
    """
    Verifică dacă URL-ul este suportat
    """
    supported_domains = [
        'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com', 
        'facebook.com', 'fb.watch', 'twitter.com', 'x.com'
    ]
    
    return any(domain in url.lower() for domain in supported_domains)