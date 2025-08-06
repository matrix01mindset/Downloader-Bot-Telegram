import yt_dlp
import os
import tempfile
import time
import glob
import re
import unicodedata

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
    Încearcă descărcarea YouTube cu opțiuni conservative pentru a evita rate limiting
    """
    fallback_opts = {
        'outtmpl': output_path,
        'format': 'worst[height<=480]/worst',  # Calitate mai mică pentru a reduce load-ul
        'quiet': True,
        'noplaylist': True,
        'extractaudio': False,
        'embed_subs': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        },
        'extractor_retries': 1,
        'fragment_retries': 1,
        'retry_sleep_functions': {
            'http': lambda n: min(5 ** n, 120),  # Delay-uri mai mari
            'fragment': lambda n: min(5 ** n, 120)
        },
        'socket_timeout': 120,
        'retries': 1,
        'sleep_interval': 3,  # Pauză mai mare între cereri
        'max_sleep_interval': 15,
        'cachedir': False,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            # Adaugă un delay înainte de încercare
            time.sleep(2)
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
    
    # Configurație specifică pentru YouTube pentru a evita HTTP 429
    if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best[height<=720]/best',
            'quiet': True,
            'noplaylist': True,
            'extractaudio': False,
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            # Opțiuni specifice pentru YouTube anti-rate-limit
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {
                'http': lambda n: min(2 ** n, 30),  # Exponential backoff mai conservator
                'fragment': lambda n: min(2 ** n, 30)
            },
            'socket_timeout': 60,
            'retries': 2,
            'sleep_interval': 1,  # Pauză între cereri
            'max_sleep_interval': 5,
            'sleep_interval_subtitles': 1,
            # Opțiuni pentru a evita detectarea ca bot
            'nocheckcertificate': False,
            'prefer_insecure': False,
            'cachedir': False,  # Dezactivează cache-ul
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
                # Încearcă cu opțiuni alternative pentru YouTube la erori de rate limiting
                if ('youtube.com' in url.lower() or 'youtu.be' in url.lower()) and ('429' in error_str or 'too many requests' in error_str or 'rate' in error_str):
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