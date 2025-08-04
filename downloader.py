import yt_dlp
import os
import tempfile
import time
import glob

def download_video(url, output_path=None):
    """
    Descarcă un video de pe YouTube, TikTok, Instagram sau Facebook
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
                raise Exception("Videoul este prea lung (max 15 minute)")
            
            # Descarcă videoul
            ydl.download([url])
            
            # Găsește fișierul descărcat în directorul temporar
            downloaded_files = glob.glob(os.path.join(temp_dir, "*"))
            downloaded_files = [f for f in downloaded_files if os.path.isfile(f)]
            
            if not downloaded_files:
                raise Exception("Fișierul nu a fost găsit după descărcare")
            
            # Ia primul fișier găsit (ar trebui să fie singurul)
            downloaded_file = downloaded_files[0]
            
            # Verifică dimensiunea fișierului
            file_size = os.path.getsize(downloaded_file)
            max_size = 100 * 1024 * 1024  # 100MB în bytes
            
            if file_size > max_size:
                os.remove(downloaded_file)
                raise Exception(f"Fișierul este prea mare ({file_size / (1024*1024):.1f}MB). Limita este 100MB.")
            
            return downloaded_file
            
    except Exception as e:
        raise Exception(f"Eroare la descărcarea videoclipului: {str(e)}")

def is_supported_url(url):
    """
    Verifică dacă URL-ul este suportat
    """
    supported_domains = [
        'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com', 
        'facebook.com', 'fb.watch', 'twitter.com', 'x.com'
    ]
    
    return any(domain in url.lower() for domain in supported_domains)