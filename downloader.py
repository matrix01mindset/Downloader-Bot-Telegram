import yt_dlp
import os
import tempfile
import time
import glob

def download_video(url, output_path=None):
    """
    Descarcă un video de pe YouTube, TikTok, Instagram sau Facebook
    Returnează un dicționar cu rezultatul
    """
    if output_path is None:
        # Creează un director temporar unic
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "%(title)s.%(ext)s")
    
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'best[height<=720]/best',  # Limitează calitatea pentru a evita fișiere prea mari
        'quiet': True,
        'noplaylist': True,
        'extractaudio': False,
        'audioformat': 'mp3',
        'embed_subs': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        # Opțiuni pentru Instagram și alte platforme
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'extractor_retries': 3,
        'fragment_retries': 3,
        'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)},
        'ignoreerrors': False,
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
            
            # Curăță titlul de caractere speciale problematice
            title = title.replace('\n', ' ').replace('\r', ' ').strip()
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
            ydl.download([url])
            
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
        if 'rate' in error_msg and 'limit' in error_msg:
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