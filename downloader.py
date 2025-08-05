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
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrage informații despre video
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            duration = info.get('duration', 0)
            
            # Verifică dacă videoul nu este prea lung (max 15 minute pentru fișiere mai mari)
            if duration and duration > 900:
                return {
                    'success': False,
                    'error': 'Videoul este prea lung (max 15 minute)',
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
            max_size = 100 * 1024 * 1024  # 100MB în bytes
            
            if file_size > max_size:
                os.remove(downloaded_file)
                return {
                    'success': False,
                    'error': f'Fișierul este prea mare ({file_size / (1024*1024):.1f}MB). Limita este 100MB.',
                    'title': title
                }
            
            return {
                'success': True,
                'file_path': downloaded_file,
                'title': title,
                'duration': duration,
                'file_size': file_size
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Eroare la descărcarea videoclipului: {str(e)}',
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