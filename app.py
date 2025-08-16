import os
import logging
import asyncio
import html
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from downloader import download_video, is_supported_url, upgrade_to_nightly_ytdlp
import tempfile
import time
import threading
from utils.security.auth_manager import AuthenticationManager, require_permission
from utils.security.security_monitor import SecurityMonitor
from utils.security.input_sanitizer import InputSanitizer, ValidationLevel
# Force redeploy - 2025-08-09 - Facebook fixes deployed
import re
from utils.activity_logger import activity_logger, log_command_executed, log_download_success, log_download_error
from urllib.parse import urlparse
# Render optimized config - using built-in alternatives
import tempfile
import logging

def is_render_environment():
    import os
    return os.getenv('RENDER') is not None

def setup_render_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def cleanup_render_temp_files(temp_dir=None):
    try:
        import os
        import tempfile
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.endswith(('.part', '.tmp')):
                os.remove(os.path.join(temp_dir, file))
    except Exception:
        pass

RENDER_OPTIMIZED_CONFIG = {
    'flask_config': {
        'MAX_CONTENT_LENGTH': 45 * 1024 * 1024,
        'SEND_FILE_MAX_AGE_DEFAULT': 31536000
    }
}

# Încarcă variabilele de mediu din .env pentru testare locală
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv nu este disponibil în producție, nu e problemă
    pass

# Configurare logging îmbunătățit pentru producție
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Reduce logging pentru biblioteci externe pentru a economisi resurse
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

# Metrici pentru monitoring
class BotMetrics:
    """Colectează metrici pentru monitoring"""
    
    def __init__(self):
        self.reset_metrics()
    
    def reset_metrics(self):
        """Resetează metricile"""
        self.downloads_total = 0
        self.downloads_success = 0
        self.downloads_failed = 0
        self.platform_stats = {
            'tiktok': {'success': 0, 'failed': 0},
            'instagram': {'success': 0, 'failed': 0},
            'facebook': {'success': 0, 'failed': 0},
            'twitter': {'success': 0, 'failed': 0},
            'unknown': {'success': 0, 'failed': 0}
        }
        self.error_types = {}
        self.webhook_requests = 0
        self.rate_limited_requests = 0
        self.start_time = time.time()
    
    def record_download_attempt(self, platform='unknown'):
        """Înregistrează o încercare de descărcare"""
        self.downloads_total += 1
        if platform not in self.platform_stats:
            platform = 'unknown'
    
    def record_download_success(self, platform='unknown'):
        """Înregistrează o descărcare reușită"""
        self.downloads_success += 1
        if platform not in self.platform_stats:
            platform = 'unknown'
        self.platform_stats[platform]['success'] += 1
    
    def record_download_failure(self, platform='unknown', error_type='unknown'):
        """Înregistrează o descărcare eșuată"""
        self.downloads_failed += 1
        if platform not in self.platform_stats:
            platform = 'unknown'
        self.platform_stats[platform]['failed'] += 1
        
        # Înregistrează tipul de eroare
        if error_type not in self.error_types:
            self.error_types[error_type] = 0
        self.error_types[error_type] += 1
    
    def record_webhook_request(self):
        """Înregistrează o cerere webhook"""
        self.webhook_requests += 1
    
    def record_rate_limit(self):
        """Înregistrează o cerere rate limited"""
        self.rate_limited_requests += 1
    
    def get_success_rate(self):
        """Calculează rata de succes"""
        if self.downloads_total == 0:
            return 0.0
        return (self.downloads_success / self.downloads_total) * 100
    
    def get_uptime(self):
        """Calculează uptime-ul în secunde"""
        return time.time() - self.start_time
    
    def get_stats(self):
        """Returnează statisticile complete"""
        uptime_hours = self.get_uptime() / 3600
        
        return {
            'uptime_hours': round(uptime_hours, 2),
            'downloads_total': self.downloads_total,
            'downloads_success': self.downloads_success,
            'downloads_failed': self.downloads_failed,
            'success_rate': round(self.get_success_rate(), 2),
            'webhook_requests': self.webhook_requests,
            'rate_limited_requests': self.rate_limited_requests,
            'platform_stats': self.platform_stats,
            'error_types': self.error_types
        }
    
    def log_periodic_stats(self):
        """Loghează statisticile periodic"""
        stats = self.get_stats()
        logger.info(f"📊 STATS: Downloads: {stats['downloads_success']}/{stats['downloads_total']} "
                   f"({stats['success_rate']}%), Webhooks: {stats['webhook_requests']}, "
                   f"Rate limited: {stats['rate_limited_requests']}, "
                   f"Uptime: {stats['uptime_hours']}h")
        
        # Loghează alertele pentru probleme
        if stats['success_rate'] < 50 and stats['downloads_total'] > 5:
            logger.warning(f"🚨 ALERT: Success rate scăzut: {stats['success_rate']}%")
        
        if stats['rate_limited_requests'] > stats['webhook_requests'] * 0.3:
            logger.warning(f"🚨 ALERT: Prea multe cereri rate limited: {stats['rate_limited_requests']}")

# Instanță globală pentru metrici
metrics = BotMetrics()

# Funcții pentru escaparea caracterelor speciale
def escape_markdown_v2(text: str) -> str:
    """
    Escapează caracterele speciale pentru MarkdownV2 conform specificației Telegram.
    Caractere ce trebuie escape-uite: _ * [ ] ( ) ~ > # + - = | { } . !
    """
    if not text:
        return ""
    
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def escape_html(text: str) -> str:
    """
    Escapează caracterele speciale pentru HTML.
    """
    if not text:
        return ""
    
    return html.escape(text)

def validate_chat_id(chat_id):
    """
    Validează chat_id înainte de trimiterea mesajelor
    """
    if not chat_id:
        return False
    if str(chat_id).lower() in ['none', 'null', '']:
        return False
    try:
        int(chat_id)
        return True
    except (ValueError, TypeError):
        return False

def extract_urls_from_text(text):
    """
    Extrage toate URL-urile dintr-un text și le returnează ca listă.
    Detectează URL-uri cu http/https și fără protocol.
    """
    if not text:
        return []
    
    # Pattern pentru URL-uri cu protocol
    url_pattern_with_protocol = r'https?://[^\s]+'
    
    # Pattern pentru URL-uri fără protocol (domenii cunoscute)
    url_pattern_without_protocol = r'(?:^|\s)((?:www\.|m\.|mobile\.)?(?:tiktok\.com|instagram\.com|facebook\.com|twitter\.com|x\.com|threads\.net|pinterest\.com|reddit\.com|vimeo\.com|dailymotion\.com)/[^\s]+)'
    
    urls = []
    
    # Găsește URL-uri cu protocol
    urls_with_protocol = re.findall(url_pattern_with_protocol, text, re.IGNORECASE)
    urls.extend(urls_with_protocol)
    
    # Găsește URL-uri fără protocol
    urls_without_protocol = re.findall(url_pattern_without_protocol, text, re.IGNORECASE)
    for url in urls_without_protocol:
        if not url.startswith('http'):
            urls.append('https://' + url)
        else:
            urls.append(url)
    
    # Elimină duplicatele și returnează lista
    return list(set(urls))

def filter_supported_urls(urls):
    """
    Filtrează doar URL-urile suportate din lista dată.
    """
    supported_urls = []
    for url in urls:
        if is_supported_url(url):
            supported_urls.append(url)
    return supported_urls
=======
def is_caption_too_long_error(error_msg: str) -> bool:
    """
    Detectează dacă eroarea este cauzată de un caption prea lung.
    """
    error_lower = str(error_msg).lower()
    caption_errors = [
        'caption too long',
        'message too long', 
        'text too long',
        'caption is too long',
        'message text is too long',
        'bad request: message caption is too long',
        'bad request: message text is too long'
    ]
    return any(err in error_lower for err in caption_errors)

class ErrorHandler:
    """
    Gestionează clasificarea erorilor și strategiile de retry pentru bot
    """
    
    # Tipuri de erori
    ERROR_TYPES = {
        'CAPTION_TOO_LONG': 'caption_too_long',
        'PRIVATE_VIDEO': 'private_video',
        'PLATFORM_ERROR': 'platform_error',
        'NETWORK_ERROR': 'network_error',
        'FILE_TOO_LARGE': 'file_too_large',
        'PARSING_ERROR': 'parsing_error',
        'CHAT_INACCESSIBLE': 'chat_inaccessible',
        'UNKNOWN_ERROR': 'unknown_error'
    }
    
    @staticmethod
    def classify_error(error_msg: str, platform: str = "unknown") -> str:
        """
        Clasifică tipul de eroare bazat pe mesajul de eroare
        """
        error_lower = str(error_msg).lower()
        
        # Erori de caption prea lung
        if is_caption_too_long_error(error_msg):
            return ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG']
        
        # Erori de chat inaccesibil
        chat_errors = ['chat not found', 'forbidden', 'blocked', 'user is deactivated']
        if any(err in error_lower for err in chat_errors):
            return ErrorHandler.ERROR_TYPES['CHAT_INACCESSIBLE']
        
        # Erori de videoclip privat
        private_errors = ['private', 'login required', 'sign in', 'authentication', 'access denied']
        if any(err in error_lower for err in private_errors):
            return ErrorHandler.ERROR_TYPES['PRIVATE_VIDEO']
        
        # Erori de fișier prea mare
        size_errors = ['file too large', 'too big', 'exceeds limit', 'file size', 'too heavy']
        if any(err in error_lower for err in size_errors):
            return ErrorHandler.ERROR_TYPES['FILE_TOO_LARGE']
        
        # Erori de parsing/extragere
        parsing_errors = ['cannot parse', 'extract', 'unsupported url', 'not available', 'removed', 'deleted']
        if any(err in error_lower for err in parsing_errors):
            return ErrorHandler.ERROR_TYPES['PARSING_ERROR']
        
        # Erori de rețea
        network_errors = ['timeout', 'connection', 'network', 'unreachable', 'dns', 'ssl']
        if any(err in error_lower for err in network_errors):
            return ErrorHandler.ERROR_TYPES['NETWORK_ERROR']
        
        # Erori specifice platformei
        platform_errors = ['rate limit', 'blocked', 'banned', 'restricted', 'geo', 'region']
        if any(err in error_lower for err in platform_errors):
            return ErrorHandler.ERROR_TYPES['PLATFORM_ERROR']
        
        return ErrorHandler.ERROR_TYPES['UNKNOWN_ERROR']
    
    @staticmethod
    def should_retry(error_type: str, attempt: int, max_attempts: int = 3) -> bool:
        """
        Determină dacă ar trebui să reîncerce bazat pe tipul de eroare și numărul de încercări
        """
        if attempt >= max_attempts:
            return False
        
        # Erori care merită retry
        retry_errors = [
            ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG'],
            ErrorHandler.ERROR_TYPES['NETWORK_ERROR'],
            ErrorHandler.ERROR_TYPES['PLATFORM_ERROR']
        ]
        
        return error_type in retry_errors
    
    @staticmethod
    def get_retry_delay(attempt: int, error_type: str) -> float:
        """
        Calculează delay-ul pentru retry cu exponential backoff
        """
        base_delays = {
            ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG']: 0.5,
            ErrorHandler.ERROR_TYPES['NETWORK_ERROR']: 2.0,
            ErrorHandler.ERROR_TYPES['PLATFORM_ERROR']: 3.0
        }
        
        base_delay = base_delays.get(error_type, 1.0)
        return min(base_delay * (2 ** attempt), 30.0)  # Max 30 secunde
    
    @staticmethod
    def get_user_message(error_type: str, platform: str = "unknown", original_error: str = "") -> str:
        """
        Returnează mesaj prietenos pentru utilizator bazat pe tipul de eroare
        """
        messages = {
            ErrorHandler.ERROR_TYPES['CAPTION_TOO_LONG']: 
                "❌ Descrierea videoclipului este prea lungă. Încerc cu o versiune mai scurtă...",
            
            ErrorHandler.ERROR_TYPES['PRIVATE_VIDEO']: 
                f"❌ Videoclipul este privat sau necesită autentificare.\n\n"
                f"💡 Asigură-te că videoclipul este public și accesibil fără cont.",
            
            ErrorHandler.ERROR_TYPES['FILE_TOO_LARGE']: 
                f"❌ Videoclipul este prea mare pentru Telegram (max 50MB).\n\n"
                f"💡 Încearcă un videoclip mai scurt sau de calitate mai mică.",
            
            ErrorHandler.ERROR_TYPES['PARSING_ERROR']: 
                f"❌ Nu pot procesa acest link de pe {platform.title()}.\n\n"
                f"💡 Verifică că link-ul este corect și videoclipul există.",
            
            ErrorHandler.ERROR_TYPES['NETWORK_ERROR']: 
                f"❌ Probleme de conectivitate.\n\n"
                f"💡 Te rog să încerci din nou în câteva momente.",
            
            ErrorHandler.ERROR_TYPES['PLATFORM_ERROR']: 
                f"❌ Probleme temporare cu {platform.title()}.\n\n"
                f"💡 Încearcă din nou mai târziu sau cu alt link.",
            
            ErrorHandler.ERROR_TYPES['CHAT_INACCESSIBLE']: 
                f"❌ Nu pot trimite mesaje în acest chat.",
            
            ErrorHandler.ERROR_TYPES['UNKNOWN_ERROR']: 
                f"❌ A apărut o eroare neașteptată.\n\n"
                f"💡 Te rog să încerci din nou sau cu alt link."
        }
        
        return messages.get(error_type, messages[ErrorHandler.ERROR_TYPES['UNKNOWN_ERROR']])
    
    @staticmethod
    def log_error(error_type: str, platform: str, error_msg: str, user_id: int = None):
        """
        Loghează eroarea pentru debugging
        """
        log_msg = f"Error [{error_type}] on {platform}"
        if user_id:
            log_msg += f" for user {user_id}"
        log_msg += f": {error_msg}"
        
        if error_type in [ErrorHandler.ERROR_TYPES['UNKNOWN_ERROR'], ErrorHandler.ERROR_TYPES['PLATFORM_ERROR']]:
            logger.error(log_msg)
        else:
            logger.warning(log_msg)
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e

def safe_send_with_fallback(chat_id, text, parse_mode='HTML', reply_markup=None):
    """
    Trimite mesaj cu fallback la text simplu dacă parse_mode eșuează.
    Versiune optimizată cu AsyncDownloadManager pentru performanță îmbunătățită.
    """
    import requests
    
    if not TOKEN:
        logger.error("TOKEN nu este setat!")
        return False
    
    # Validează chat_id înainte de trimitere
    if not validate_chat_id(chat_id):
        logger.error(f"Chat ID invalid: {chat_id}")
        return False
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # Încearcă mai întâi cu parse_mode
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    
    try:
        # Timeout mărit pentru Render (connect=20s, read=30s)
        response = requests.post(url, json=data, timeout=(20, 30))
        
        if response.status_code == 200:
            logger.info(f"Mesaj trimis cu succes către chat_id {chat_id} cu {parse_mode}")
            return True
        else:
            # Dacă eșuează cu parse_mode, încearcă fără
            logger.warning(f"Eroare cu {parse_mode}: {response.status_code} - {response.text[:200]}")
            logger.info(f"Încerc să trimit fără parse_mode...")
            
            data_fallback = {
                'chat_id': chat_id,
                'text': text
            }
            if reply_markup:
                data_fallback['reply_markup'] = reply_markup
            
            # Timeout mărit pentru fallback
            response_fallback = requests.post(url, json=data_fallback, timeout=(20, 30))
            
            if response_fallback.status_code == 200:
                logger.info(f"Mesaj trimis cu succes către chat_id {chat_id} fără parse_mode")
                return True
            else:
                logger.error(f"Eroare și la fallback: {response_fallback.status_code} - {response_fallback.text[:200]}")
                return False
                
    except Exception as e:
        logger.error(f"Excepție la trimiterea mesajului: {e}")
        return False

<<<<<<< HEAD
# Versiune asincronă optimizată pentru performanță
async def async_send_telegram_message(chat_id, text, parse_mode='HTML', reply_markup=None):
    """
    Versiune asincronă optimizată pentru trimiterea mesajelor Telegram.
    Utilizează AsyncDownloadManager pentru performanță îmbunătățită.
    """
    from utils.network.async_download_manager import get_download_manager, NetworkRequest
    
    if not TOKEN:
        logger.error("TOKEN nu este setat!")
        return False
    
    # Validează chat_id înainte de trimitere
    if not validate_chat_id(chat_id):
        logger.error(f"Chat ID invalid: {chat_id}")
        return False
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # Pregătește datele pentru cerere
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    
    try:
        # Obține download manager-ul
        download_manager = await get_download_manager()
        
        # Creează cererea de rețea
        network_request = NetworkRequest(
            url=url,
            method='POST',
            json=data,
            timeout=30,
            request_id=f"telegram_msg_{chat_id}_{int(time.time())}"
        )
        
        # Execută cererea
        result = await download_manager.make_request(network_request)
        
        if result.get('success', False) and result.get('status_code') == 200:
            logger.info(f"Mesaj trimis cu succes către chat_id {chat_id} cu {parse_mode}")
            return True
        else:
            # Fallback fără parse_mode
            logger.warning(f"Eroare cu {parse_mode}: {result.get('status_code')} - {str(result.get('error', ''))[:200]}")
            logger.info(f"Încerc să trimit fără parse_mode...")
            
            data_fallback = {
                'chat_id': chat_id,
                'text': text
            }
            if reply_markup:
                data_fallback['reply_markup'] = reply_markup
            
            # Cererea de fallback
            fallback_request = NetworkRequest(
                url=url,
                method='POST',
                json=data_fallback,
                timeout=30,
                request_id=f"telegram_msg_fallback_{chat_id}_{int(time.time())}"
            )
            
            fallback_result = await download_manager.make_request(fallback_request)
            
            if fallback_result.get('success', False) and fallback_result.get('status_code') == 200:
                logger.info(f"Mesaj trimis cu succes către chat_id {chat_id} fără parse_mode")
                return True
            else:
                logger.error(f"Eroare și la fallback: {fallback_result.get('status_code')} - {str(fallback_result.get('error', ''))[:200]}")
                return False
                
    except Exception as e:
        logger.error(f"Excepție la trimiterea mesajului asincron: {e}")
        return False

# Funcție centrală pentru crearea caption-urilor sigure
=======
# Funcție centrală pentru crearea caption-urilor sigure - îmbunătățită
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
def create_safe_caption(title, uploader=None, description=None, duration=None, file_size=None, max_length=1000):
    """
    Creează un caption sigur pentru Telegram, respectând limitele de caractere.
    Îmbunătățită pentru gestionarea caracterelor Unicode, emoticoanelor și diacriticelor.
    
    Args:
        title (str): Titlul videoclipului
        uploader (str, optional): Numele creatorului
        description (str, optional): Descrierea videoclipului
        duration (int/float, optional): Durata în secunde
        file_size (int/float, optional): Mărimea fișierului în bytes
        max_length (int): Lungimea maximă a caption-ului (default: 1000)
    
    Returns:
        str: Caption-ul formatat și sigur pentru Telegram
    """
    try:
        # Funcție helper pentru curățarea textului
        def clean_text(text, max_len):
            if not text:
                return ""
            
            # Normalizează Unicode pentru diacritice și caractere speciale
            import unicodedata
            text = unicodedata.normalize('NFC', str(text))
            
            # Curăță caractere de control și invizibile, dar păstrează emoticoanele
            cleaned = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or ord(char) > 127)
            
            # Înlocuiește newlines și spații multiple
            cleaned = re.sub(r'[\r\n]+', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # Truncare inteligentă
            if len(cleaned) <= max_len:
                return cleaned
            
            # Încearcă să găsești o întrerupere naturală
            truncate_pos = max_len - 3  # Spațiu pentru "..."
            
            # Caută ultima propoziție completă
            for punct in ['. ', '! ', '? ']:
                last_punct = cleaned[:truncate_pos].rfind(punct)
                if last_punct > max_len // 2:
                    return cleaned[:last_punct + 1]
            
            # Caută ultimul spațiu
            last_space = cleaned[:truncate_pos].rfind(' ')
            if last_space > max_len // 2:
                return cleaned[:last_space] + "..."
            
            # Truncare forțată
            return cleaned[:truncate_pos] + "..."
        
        # Procesează titlul cu prioritate maximă
        title_clean = clean_text(title, 200) if title else "Video"
        title_safe = escape_html(title_clean)
        
        # Începe cu titlul
        caption = f"✅ <b>{title_safe}</b>\n\n"
        
        # Adaugă creatorul cu prioritate înaltă
        if uploader and uploader.strip():
            uploader_clean = clean_text(uploader, 100)
            uploader_safe = escape_html(uploader_clean)
            caption += f"👤 <b>Creator:</b> {uploader_safe}\n"
        
        # Formatează durata cu verificări robuste
        if duration and isinstance(duration, (int, float)) and duration > 0:
            try:
                total_seconds = int(float(duration))
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                if hours > 0:
                    caption += f"⏱️ <b>Durată:</b> {hours}:{minutes:02d}:{seconds:02d}\n"
                else:
                    caption += f"⏱️ <b>Durată:</b> {minutes}:{seconds:02d}\n"
            except (TypeError, ValueError, OverflowError):
                pass  # Skip duration if formatting fails
        
        # Formatează dimensiunea fișierului cu verificări robuste
        if file_size and isinstance(file_size, (int, float)) and file_size > 0:
            try:
                size_bytes = float(file_size)
                if size_bytes >= 1024 * 1024 * 1024:  # GB
                    size_gb = size_bytes / (1024 * 1024 * 1024)
                    caption += f"📦 <b>Mărime:</b> {size_gb:.1f} GB\n"
                elif size_bytes >= 1024 * 1024:  # MB
                    size_mb = size_bytes / (1024 * 1024)
                    caption += f"📦 <b>Mărime:</b> {size_mb:.1f} MB\n"
                elif size_bytes >= 1024:  # KB
                    size_kb = size_bytes / 1024
                    caption += f"📦 <b>Mărime:</b> {size_kb:.1f} KB\n"
                else:
                    caption += f"📦 <b>Mărime:</b> {int(size_bytes)} bytes\n"
            except (TypeError, ValueError, OverflowError):
                pass  # Skip file size if formatting fails
        
        # Calculează spațiul rămas pentru descriere
        current_length = len(caption.encode('utf-8'))  # Folosește byte length pentru precizie
        footer = "\n\n🎬 Descărcare completă!"
        footer_length = len(footer.encode('utf-8'))
        
        # Spațiul disponibil pentru descriere (buffer mai mare pentru siguranță)
        available_space = max_length - current_length - footer_length - 100
        
        # Adaugă descrierea dacă există și dacă avem spațiu suficient
        if description and description.strip() and available_space > 50:
            # Calculează lungimea maximă pentru descriere în caractere (aproximativ)
            max_desc_chars = max(50, available_space // 2)  # Estimare conservatoare
            
            description_clean = clean_text(description, max_desc_chars)
            if description_clean:
                description_safe = escape_html(description_clean)
                desc_section = f"\n📝 <b>Descriere:</b>\n{description_safe}"
                
                # Verifică dacă adăugarea descrierii nu depășește limita
                test_caption = caption + desc_section + footer
                if len(test_caption.encode('utf-8')) <= max_length:
                    caption += desc_section
        
        # Adaugă footer-ul
        caption += footer
        
        # Verificare finală de siguranță cu byte length
        caption_bytes = len(caption.encode('utf-8'))
        if caption_bytes > max_length:
            logger.warning(f"Caption prea lung după procesare: {caption_bytes} bytes")
            # Truncare de urgență - păstrează doar titlul și footer-ul
            safe_title = escape_html(clean_text(title, 100)) if title else "Video"
            caption = f"✅ <b>{safe_title}</b>\n\n🎬 Descărcare completă!"
        
        return caption
        
    except Exception as e:
        logger.error(f"Eroare la crearea caption-ului: {e}")
        # Fallback la un caption minimal ultra-sigur
        try:
            safe_title = escape_html(str(title)[:50]) if title else 'Video'
            return f"✅ <b>{safe_title}</b>\n\n🎬 Descărcare completă!"
        except:
            return "✅ <b>Video</b>\n\n🎬 Descărcare completă!"

# Configurare Flask cu optimizări pentru Render
app = Flask(__name__)

# Inițializare sisteme de securitate
auth_manager = AuthenticationManager()
security_monitor = SecurityMonitor()
input_sanitizer = InputSanitizer()

@app.before_request
def security_middleware():
    """Middleware de securitate pentru toate cererile"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    
    # Verifică dacă IP-ul este blocat
    if security_monitor.is_ip_blocked(client_ip):
        logger.warning(f"Cerere blocată de la IP: {client_ip}")
        return jsonify({'status': 'blocked', 'message': 'Access denied'}), 403
    
    # Analizează cererea pentru amenințări (doar pentru webhook-uri)
    if request.endpoint == 'webhook':
        security_monitor.analyze_request({
            'ip': client_ip,
            'path': request.path,
            'method': request.method,
            'user_agent': request.headers.get('User-Agent', ''),
            'timestamp': time.time()
        })

# 🛡️ SECURITATE: Forțează dezactivarea debug mode în producție
if os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER') or is_render_environment():
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Configurare optimizată pentru Render
    if is_render_environment():
        setup_render_logging()
        cleanup_render_temp_files()
        logger.info("🚀 Configurație optimizată pentru Render activată")
        
        # Configurări specifice pentru Render
        app.config.update(RENDER_OPTIMIZED_CONFIG['flask_config'])
        
    logger.info("🔒 Debug mode forțat dezactivat pentru producție")
else:
    logger.info("🔧 Rulare în modul development")

# Debug: Afișează toate variabilele de mediu relevante
print("=== DEBUG: VARIABILE DE MEDIU ===")
print(f"TELEGRAM_BOT_TOKEN: {'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET'}")
print(f"WEBHOOK_URL: {os.getenv('WEBHOOK_URL', 'NOT SET')}")
print(f"PORT: {os.getenv('PORT', 'NOT SET')}")
print("===========================================")

# Token-ul botului
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')

if not TOKEN:
    print("❌ EROARE: TELEGRAM_BOT_TOKEN nu este setat!")
    print("Verifică că ai adăugat variabila de mediu în Render Dashboard.")
    print("Variabilele de mediu disponibile:")
    for key in os.environ.keys():
        if 'TOKEN' in key.upper() or 'TELEGRAM' in key.upper():
            print(f"  - {key}")
    print("⚠️ AVERTISMENT: TELEGRAM_BOT_TOKEN nu este setat!")
    TOKEN = "PLACEHOLDER_TOKEN"

<<<<<<< HEAD
# Inițializare bot și application cu configurații optimizate pentru producție
# Configurare bot cu connection pool și timeout-uri reduse pentru Render
try:
    bot = Bot(TOKEN) if TOKEN and TOKEN != "PLACEHOLDER_TOKEN" else None
except Exception as e:
    print(f"⚠️ Eroare la inițializarea bot-ului: {e}")
    bot = None
application = (
    Application.builder()
    .token(TOKEN)
    .connection_pool_size(50)  # Redus pentru mediul de producție
    .pool_timeout(30.0)  # Timeout mărit pentru Render
    .get_updates_connection_pool_size(5)  # Redus pentru webhook mode
    .get_updates_pool_timeout(30.0)  # Timeout mărit pentru Render
    .read_timeout(30.0)  # Timeout mărit pentru Render
    .write_timeout(30.0)  # Timeout mărit pentru Render
    .connect_timeout(20.0)  # Timeout mărit pentru Render
=======
# Inițializare bot și application cu configurații optimizate pentru Render free tier
# Configurații agresiv optimizate pentru limitările de memorie și CPU
bot = Bot(TOKEN)
application = (
    Application.builder()
    .token(TOKEN)
    .connection_pool_size(10)  # Redus dramatic pentru Render free tier
    .pool_timeout(10.0)  # Timeout foarte redus pentru a evita blocarea
    .get_updates_connection_pool_size(2)  # Minimal pentru webhook mode
    .get_updates_pool_timeout(10.0)  # Timeout redus
    .read_timeout(8.0)  # Timeout foarte redus pentru citire
    .write_timeout(8.0)  # Timeout foarte redus pentru scriere
    .connect_timeout(5.0)  # Timeout foarte redus pentru conectare
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
    .build()
)

# Variabilă globală pentru starea inițializării
_app_initialized = False

def cleanup_temp_files():
    """
    Curăță agresiv fișierele temporare pentru a economisi spațiu pe Render
    """
    try:
        import glob
        import os
        
        # Directoare temporare comune
        temp_dirs = [
            tempfile.gettempdir(),
            '/tmp',
            './temp',
            './downloads'
        ]
        
        files_deleted = 0
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                # Șterge fișiere video temporare
                patterns = ['*.mp4', '*.avi', '*.mkv', '*.webm', '*.mov', '*.flv', '*.part', '*.tmp']
                for pattern in patterns:
                    for file_path in glob.glob(os.path.join(temp_dir, pattern)):
                        try:
                            if os.path.isfile(file_path):
                                # Verifică dacă fișierul este mai vechi de 5 minute
                                file_age = time.time() - os.path.getmtime(file_path)
                                if file_age > 300:  # 5 minute
                                    os.remove(file_path)
                                    files_deleted += 1
                        except Exception as e:
                            logger.debug(f"Nu s-a putut șterge {file_path}: {e}")
        
        if files_deleted > 0:
            logger.info(f"Cleanup: {files_deleted} fișiere temporare șterse")
            
    except Exception as e:
        logger.debug(f"Eroare la cleanup fișiere temporare: {e}")

def initialize_telegram_application():
    """Inițializează aplicația Telegram o singură dată"""
    global _app_initialized
    if _app_initialized:
        return True
        
    try:
        # Cleanup la inițializare
        cleanup_temp_files()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.initialize())
            _app_initialized = True
            logger.info("✅ Aplicația Telegram a fost inițializată cu succes")
            return True
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"❌ Eroare la inițializarea aplicației: {e}")
        return False

# Funcții pentru comenzi cu meniu interactiv
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /start - mesaj de bun venit cu meniu interactiv
    """
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Log comanda executată
        log_command_executed('/start', user.id, chat_id, True)
        
        # DEBUG: Afișează ID-ul utilizatorului pentru configurare admin
        logger.info(f"User {user.first_name} ({user.username}) used /start command with ID: {user.id}")
        
    except Exception as e:
        logger.error(f"Eroare în comanda /start: {e}")
        # Log eroarea comenzii
        user = update.effective_user if update and update.effective_user else None
        chat_id = update.effective_chat.id if update and update.effective_chat else 0
        log_command_executed('/start', user.id if user else 0, chat_id, False)
        
    welcome_message = """
🎬 <b>Bot Descărcare Video</b>

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 <b>Platforme suportate:</b>
• TikTok
• Instagram
• Facebook
• Twitter/X
• Threads
• Pinterest
• Reddit
• Vimeo
• Dailymotion

⚠️ <b>Limitări:</b>
- Videoclipuri max 3 ore
- Mărime max 550MB
- Calitate max 720p
- Doar videoclipuri publice
    """
    
    # Creează butoanele pentru meniu
    keyboard = [
        [InlineKeyboardButton("📖 Cum să folosesc botul", callback_data='help')],
        [InlineKeyboardButton("🔗 Platforme suportate", callback_data='platforms')],
        [InlineKeyboardButton("⚙️ Setări și limitări", callback_data='settings')],
        [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')],
        [InlineKeyboardButton("🔄 Ping Server", callback_data='ping_again'), InlineKeyboardButton("🌅 Wakeup Server", callback_data='wakeup_server')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_send_message(update, welcome_message, parse_mode='HTML', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /help - informații complete de ajutor
    """
    help_text = """
<<<<<<< HEAD
🤖 **Bot Descărcare Video - Ghid Complet**
=======
🆘 <b>Cum să folosești botul:</b>
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e

📋 **Comenzi disponibile:**
• `/start` - Pornește botul și afișează meniul principal
• `/help` - Afișează acest ghid complet
• `/menu` - Revine la meniul principal
• `/ping` - Verifică dacă botul funcționează

🆘 **Cum să folosești botul:**
1️⃣ Copiază link-ul videoclipului
2️⃣ Trimite-l în acest chat
3️⃣ Așteaptă să fie procesat (poate dura 30s-2min)
4️⃣ Primești videoclipul descărcat automat

<<<<<<< HEAD
🔗 **Platforme suportate:**
• TikTok (tiktok.com, vm.tiktok.com)
• Instagram (instagram.com, reels, stories)
• Facebook (facebook.com, fb.watch, watch)
• Twitter/X (twitter.com, x.com)
=======
🔗 <b>Platforme suportate:</b>
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Facebook (facebook.com, fb.watch)
- Twitter/X (twitter.com, x.com)
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e

⚠️ **Limitări importante:**
• Mărime maximă: 45MB (limita Telegram)
• Durată maximă: 3 ore
• Calitate maximă: 720p
• Doar videoclipuri publice
• YouTube nu este suportat momentan

<<<<<<< HEAD
🔧 **Funcționalități:**
• Descărcare automată în calitate optimă
• Detectare automată a platformei
• Cleanup automat al fișierelor temporare
• Retry automat în caz de eroare
• Validare chat_id pentru securitate

❌ **Probleme frecvente și soluții:**
• Videoclip privat → Fă-l public sau folosește alt link
• Video prea mare → Botul va încerca să compreseze
• Link invalid → Verifică că link-ul este complet
• Eroare de rețea → Încearcă din nou după câteva minute
• Platform rate limit → Așteaptă 5-10 minute

💡 **Sfaturi:**
• Folosește link-uri directe (nu scurtate)
• Verifică că videoclipul este public
• Pentru probleme persistente, folosește `/ping`
=======
⚠️ <b>Probleme frecvente:</b>
- Videoclipul este privat → Nu poate fi descărcat
- Videoclipul este prea lung → Max 15 minute
- Link invalid → Verifică că link-ul este corect
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_send_message(update, help_text, parse_mode='HTML', reply_markup=reply_markup)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Afișează meniul principal
    """
    welcome_message = """
🎬 <b>Bot Descărcare Video</b>

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 <b>Platforme suportate:</b>
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X

⚠️ <b>Limitări:</b>
- Videoclipuri max 3 ore
- Mărime max 550MB
- Calitate max 720p
- Doar videoclipuri publice
    """
    
    keyboard = [
        [InlineKeyboardButton("📖 Cum să folosesc botul", callback_data='help')],
        [InlineKeyboardButton("🔗 Platforme suportate", callback_data='platforms')],
        [InlineKeyboardButton("⚙️ Setări și limitări", callback_data='settings')],
        [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')],
        [InlineKeyboardButton("🔄 Ping Server", callback_data='ping_again'), InlineKeyboardButton("🌅 Wakeup Server", callback_data='wakeup_server')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_send_message(update, welcome_message, parse_mode='HTML', reply_markup=reply_markup)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /ping - verifică dacă botul funcționează
    """
    start_time = time.time()
    message = await safe_send_message(update, "🏓 <b>Ping...</b>", parse_mode='HTML')
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 1)
    
    if message:
        await safe_edit_message(message, f"🏓 <b>Pong!</b>\n\n⏱️ <b>Timp răspuns:</b> {ping_time}ms\n✅ <b>Status:</b> Funcțional", parse_mode='HTML')

async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /log - trimite raportul de activitate (doar pentru admin)
    """
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Simplitate: oricine poate folosi comanda /log
        logger.info(f"User {user.first_name} ({user.username}) requested activity logs with ID: {user.id}")
        
        # Log comanda executată
        log_command_executed('/log', user.id, chat_id, True)
        
        # Trimite mesaj de procesare
        status_message = await safe_send_message(
            update,
            "📊 <b>Generez raportul de activitate...</b>\n\nTe rog așteaptă...",
            parse_mode='HTML'
        )
        
        # Generează raportul
        report = activity_logger.generate_report(hours=24)
        
        # Trimite raportul ca text (pentru debugging)
        from datetime import datetime
        
        # Limitează lungimea raportului pentru Telegram (max 4096 caractere)
        if len(report) > 4000:
            report = report[:4000] + "\n\n... (raport trunchiat)"
        
        await safe_send_message(
            update,
            f"📊 <b>Raport Activitate Bot</b>\n\n"
            f"📅 <b>Perioada:</b> Ultimele 24 ore\n"
            f"🕐 <b>Generat la:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            f"<pre>{report}</pre>",
            parse_mode='HTML'
        )
        
        # Șterge mesajul de status
        if status_message:
            await safe_delete_message(status_message)
                
    except Exception as e:
        logger.error(f"Eroare în comanda /log: {e}")
        # Log eroarea comenzii
        user = update.effective_user if update and update.effective_user else None
        chat_id = update.effective_chat.id if update and update.effective_chat else 0
        log_command_executed('/log', user.id if user else 0, chat_id, False)
        
        try:
            await safe_send_message(
                update,
                f"❌ Eroare la generarea raportului: {e}",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Nu s-a putut trimite mesajul de eroare pentru comanda /log: {e}")

async def safe_send_message(update, text, **kwargs):
    """
    Trimite un mesaj în mod sigur, gestionând erorile de chat inexistent
    """
    try:
        if hasattr(update.message, 'reply_text'):
            return await update.message.reply_text(text, **kwargs)
        else:
            return await update.effective_chat.send_message(text, **kwargs)
    except Exception as e:
        error_msg = str(e).lower()
        if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
            logger.warning(f"Chat inaccesibil pentru user {update.effective_user.id}: {e}")
            return None
        else:
            logger.error(f"Eroare la trimiterea mesajului: {e}")
            raise

async def safe_edit_message(message, text, **kwargs):
    """
    Editează un mesaj în mod sigur, gestionând erorile de chat inexistent
    """
    try:
        return await message.edit_text(text, **kwargs)
    except Exception as e:
        error_msg = str(e).lower()
        if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
            logger.warning(f"Nu se poate edita mesajul - chat inaccesibil: {e}")
            return None
        else:
            logger.error(f"Eroare la editarea mesajului: {e}")
            return None

async def safe_delete_message(message):
    """
    Șterge un mesaj în mod sigur, gestionând erorile de chat inexistent
    """
    try:
        await message.delete()
    except Exception as e:
        error_msg = str(e).lower()
        if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
            logger.warning(f"Nu se poate șterge mesajul - chat inaccesibil: {e}")
        else:
            logger.error(f"Eroare la ștergerea mesajului: {e}")

async def safe_edit_callback_message(query, text, **kwargs):
    """
    Editează un mesaj de callback în mod sigur, gestionând erorile de chat inexistent
    """
    try:
        return await query.edit_message_text(text, **kwargs)
    except Exception as e:
        error_msg = str(e).lower()
        if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
            logger.warning(f"Nu se poate edita mesajul callback - chat inaccesibil: {e}")
            return None
        else:
            logger.error(f"Eroare la editarea mesajului callback: {e}")
            return None

<<<<<<< HEAD
async def process_single_video(update, url, video_index=None, total_videos=None, delay_seconds=3):
    """
    Procesează un singur video cu mesaje de status actualizate.
    Optimizat pentru mediul Render.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Cleanup fișiere temporare pentru Render
    if is_render_environment():
        cleanup_render_temp_files()
    
    # Creează mesajul de status
    if video_index and total_videos:
        status_text = f"📥 Procesez video {video_index}/{total_videos}...\n🔗 {url[:50]}{'...' if len(url) > 50 else ''}\n⏳ Te rog așteaptă..."
    else:
        status_text = f"📥 Procesez video-ul...\n🔗 {url[:50]}{'...' if len(url) > 50 else ''}\n⏳ Te rog așteaptă..."
    
    status_message = await safe_send_message(update, status_text)
    
    if not status_message:
        logger.warning(f"Nu s-a putut trimite mesajul de status pentru user {user_id}")
        return False
    
    try:
        # Execută descărcarea în thread separat
        import concurrent.futures
        
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(executor, download_video, url)
        
        if result['success']:
            # Actualizează mesajul de status
            if video_index and total_videos:
                success_text = f"✅ Video {video_index}/{total_videos} descărcat cu succes!\n📤 Trimit videoclipul..."
            else:
                success_text = "✅ Video descărcat cu succes!\n📤 Trimit videoclipul..."
            
            await safe_edit_message(status_message, success_text)
            
            # Trimite videoclipul sau fișierul audio
            try:
                file_path = result['file_path']
                file_extension = os.path.splitext(file_path)[1].lower()
                
                with open(file_path, 'rb') as media_file:
                    caption = create_safe_caption(
                        title=result.get('title', 'Media'),
                        uploader=result.get('uploader'),
                        description=result.get('description'),
                        duration=result.get('duration'),
                        file_size=result.get('file_size')
                    )
                    
                    try:
                        # Check if it's an audio file (MP3 from SoundCloud)
                        if file_extension in ['.mp3', '.m4a', '.aac', '.wav', '.flac']:
                            # Send as audio
                            if hasattr(update.message, 'reply_audio'):
                                await update.message.reply_audio(
                                    audio=media_file,
                                    caption=caption,
                                    title=result.get('title', 'Audio'),
                                    performer=result.get('uploader', 'Unknown'),
                                    duration=result.get('duration'),
                                    parse_mode='Markdown'
                                )
                            else:
                                await update.effective_chat.send_audio(
                                    audio=media_file,
                                    caption=caption,
                                    title=result.get('title', 'Audio'),
                                    performer=result.get('uploader', 'Unknown'),
                                    duration=result.get('duration'),
                                    parse_mode='Markdown'
                                )
                        else:
                            # Send as video
                            if hasattr(update.message, 'reply_video'):
                                await update.message.reply_video(
                                    video=media_file,
                                    caption=caption,
                                    supports_streaming=True,
                                    parse_mode='Markdown'
                                )
                            else:
                                await update.effective_chat.send_video(
                                    video=media_file,
                                    caption=caption,
                                    supports_streaming=True,
                                    parse_mode='Markdown'
                                )
                    except Exception as e:
                        error_msg = str(e).lower()
                        if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
                            logger.warning(f"Nu se poate trimite videoclipul - chat inaccesibil pentru user {user_id}: {e}")
                            return False
                        else:
                            raise
            except Exception as e:
                logger.error(f"Eroare la trimiterea videoclipului: {e}")
                await safe_edit_message(
                    status_message,
                    f"❌ Eroare la trimiterea videoclipului:\n{str(e)}"
                )
                return False
            
            # Șterge fișierul temporar cu cleanup optimizat pentru Render
            try:
                os.remove(result['file_path'])
                if is_render_environment():
                    logger.info(f"[RENDER] Fișier temporar șters: {result['file_path']}")
            except Exception as e:
                if is_render_environment():
                    logger.warning(f"[RENDER] Nu s-a putut șterge fișierul temporar: {e}")
                pass
            
            # Șterge mesajul de status
            await safe_delete_message(status_message)
            
            # Adaugă pauză între videoclipuri (doar dacă nu este ultimul)
            if video_index and total_videos and video_index < total_videos:
                await asyncio.sleep(delay_seconds)
            
            return True
            
        else:
            # Eroare la descărcare
            if video_index and total_videos:
                error_text = f"❌ Eroare la video {video_index}/{total_videos}:\n{result['error']}"
            else:
                error_text = f"❌ Eroare la descărcarea videoclipului:\n{result['error']}"
            
            await safe_edit_message(status_message, error_text)
            
            # Șterge mesajul de eroare după 5 secunde
            await asyncio.sleep(5)
            await safe_delete_message(status_message)
            
            return False
            
    except Exception as e:
        logger.error(f"Eroare la procesarea videoclipului: {e}")
        if status_message:
            await safe_edit_message(
                status_message,
                f"❌ Eroare neașteptată:\n{str(e)}"
            )
            # Șterge mesajul de eroare după 5 secunde
            await asyncio.sleep(5)
            await safe_delete_message(status_message)
        return False
=======
async def send_video_with_retry(update, file_path, title, uploader=None, description=None, duration=None, file_size=None, max_retries=3):
    """
    Trimite videoclip cu retry logic inteligent folosind ErrorHandler
    """
    user_id = update.effective_user.id
    
    # Determină platforma pentru metrici
    platform = 'unknown'
    if hasattr(update.message, 'text') and update.message.text:
        from downloader import get_platform_from_url
        platform = get_platform_from_url(update.message.text)
    
    # Înregistrează încercarea de descărcare
    metrics.record_download_attempt(platform)
    
    # Strategii de fallback pentru caption-uri
    caption_strategies = [
        # Strategia 1: Caption complet
        lambda: create_safe_caption(title, uploader, description, duration, file_size, 1000),
        # Strategia 2: Fără descriere
        lambda: create_safe_caption(title, uploader, None, duration, file_size, 800),
        # Strategia 3: Doar titlu și creator
        lambda: create_safe_caption(title, uploader, None, None, None, 500),
        # Strategia 4: Doar titlu
        lambda: create_safe_caption(title, None, None, None, None, 200),
        # Strategia 5: Caption minimal
        lambda: f"✅ <b>{escape_html(str(title)[:50]) if title else 'Video'}</b>\n\n🎬 Descărcare completă!"
    ]
    
    for attempt in range(max_retries):
        try:
            # Alege strategia de caption bazată pe încercare
            caption_strategy = caption_strategies[min(attempt, len(caption_strategies) - 1)]
            caption = caption_strategy()
            
            logger.info(f"Încercare {attempt + 1} de trimitere video pentru user {user_id}, caption length: {len(caption)} chars")
            
            with open(file_path, 'rb') as video_file:
                if hasattr(update.message, 'reply_video'):
                    await update.message.reply_video(
                        video=video_file,
                        caption=caption,
                        supports_streaming=True,
                        parse_mode='HTML'
                    )
                else:
                    await update.effective_chat.send_video(
                        video=video_file,
                        caption=caption,
                        supports_streaming=True,
                        parse_mode='HTML'
                    )
            
            logger.info(f"Video trimis cu succes pentru user {user_id} la încercarea {attempt + 1}")
            
            # Înregistrează succesul pentru metrici
            metrics.record_download_success(platform)
            
            # Cleanup imediat după trimiterea cu succes
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Fișier șters imediat după trimitere: {file_path}")
            except Exception as cleanup_error:
                logger.debug(f"Nu s-a putut șterge fișierul {file_path}: {cleanup_error}")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            error_type = ErrorHandler.classify_error(error_msg, "telegram")
            
            # Loghează eroarea
            ErrorHandler.log_error(error_type, "telegram", error_msg, user_id)
            
            # Verifică dacă este eroare de chat inaccesibil
            if error_type == ErrorHandler.ERROR_TYPES['CHAT_INACCESSIBLE']:
                logger.warning(f"Chat inaccesibil pentru user {user_id}")
                return False
            
            # Verifică dacă ar trebui să reîncerce
            if ErrorHandler.should_retry(error_type, attempt, max_retries):
                delay = ErrorHandler.get_retry_delay(attempt, error_type)
                logger.info(f"Reîncerc după {delay} secunde pentru user {user_id}")
                await asyncio.sleep(delay)
                continue
            else:
                # Nu mai încearcă - aruncă eroarea
                metrics.record_download_failure(platform, error_type)
                raise e
    
    # Dacă ajungem aici, toate încercările au eșuat
    metrics.record_download_failure(platform, 'max_retries_exceeded')
    return False
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesează mesajele text (link-uri pentru descărcare)
    Suportă multiple link-uri într-un singur mesaj
    Optimizat pentru mediul Render
    """
    try:
        # Cleanup fișiere temporare pentru Render
        if is_render_environment():
            cleanup_render_temp_files()
        
        # Verifică dacă update-ul și mesajul sunt valide
        if not update or not update.message or not update.effective_user:
            logger.warning("Update invalid primit")
            return
            
        message_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
<<<<<<< HEAD
        # Logging îmbunătățit pentru Render
        if is_render_environment():
            logger.info(f"[RENDER] Mesaj primit de la {user_id} în chat {chat_id}: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")
=======
        logger.info(f"Mesaj primit de la {user_id} în chat {chat_id}: {message_text}")
        
        # Verifică dacă mesajul conține un URL suportat
        if is_supported_url(message_text):
            # Trimite mesaj de confirmare
            status_message = await safe_send_message(
                update,
                "✅ Procesez și descarc video-ul în 720p te rog asteapta"
            )
            
            if not status_message:
                logger.warning(f"Nu s-a putut trimite mesajul de status pentru user {user_id}")
                return
            
            try:
                # Execută descărcarea în thread separat pentru a nu bloca event loop-ul
                import concurrent.futures
                import asyncio
                
                loop = asyncio.get_event_loop()
                
                # Rulează descărcarea în thread pool cu progress updates
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    # Actualizează mesajul cu progres
                    await safe_edit_message(
                        status_message,
                        "🔄 Analizez videoclipul și verific compatibilitatea..."
                    )
                    
                    # Așteaptă puțin pentru a permite utilizatorului să vadă mesajul
                    await asyncio.sleep(1)
                    
                    await safe_edit_message(
                        status_message,
                        "📥 Descarc videoclipul optimizat pentru Telegram..."
                    )
                    
                    result = await loop.run_in_executor(executor, download_video, message_text)
                
                if result['success']:
                    # Trimite videoclipul cu retry logic pentru caption-uri prea lungi
                    try:
                        await send_video_with_retry(
                            update, 
                            result['file_path'],
                            result.get('title', 'Video'),
                            result.get('uploader'),
                            result.get('description'),
                            result.get('duration'),
                            result.get('file_size')
                        )
                    except Exception as e:
                        logger.error(f"Eroare la trimiterea videoclipului: {e}")
                        await safe_edit_message(
                            status_message,
                            f"❌ Eroare la trimiterea videoclipului:\n{str(e)}"
                        )
                    
                    # Cleanup este făcut automat în send_video_with_retry()
                    await safe_delete_message(status_message)
                    
                    # Cleanup suplimentar pentru siguranță
                    cleanup_temp_files()
                    
                else:
                    # Clasifică eroarea și oferă mesaj prietenos
                    error_type = ErrorHandler.classify_error(result['error'], "download")
                    user_message = ErrorHandler.get_user_message(error_type, "download", result['error'])
                    ErrorHandler.log_error(error_type, "download", result['error'], user_id)
                    
                    await safe_edit_message(status_message, user_message)
                    
            except Exception as e:
                error_msg = str(e)
                error_type = ErrorHandler.classify_error(error_msg, "processing")
                user_message = ErrorHandler.get_user_message(error_type, "processing", error_msg)
                ErrorHandler.log_error(error_type, "processing", error_msg, user_id)
                
                if status_message:
                    await safe_edit_message(status_message, user_message)
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
        else:
            logger.info(f"Mesaj primit de la {user_id} în chat {chat_id}: {message_text}")
        
        # Extrage toate URL-urile din mesaj
        all_urls = extract_urls_from_text(message_text)
        
        # Filtrează doar URL-urile suportate
        supported_urls = filter_supported_urls(all_urls)
        
        if supported_urls:
            # Verifică dacă sunt multiple URL-uri
            if len(supported_urls) > 1:
                # Trimite mesaj de confirmare pentru multiple videoclipuri
                confirmation_message = await safe_send_message(
                    update,
                    f"🎯 Am găsit {len(supported_urls)} videoclipuri de descărcat!\n"
                    f"📥 Voi procesa fiecare videoclip cu o pauză de 3 secunde între ele.\n"
                    f"⏳ Procesarea va dura aproximativ {len(supported_urls) * 10} secunde..."
                )
                
                # Procesează fiecare URL cu pauză
                successful_downloads = 0
                failed_downloads = 0
                
                for index, url in enumerate(supported_urls, 1):
                    logger.info(f"Procesez video {index}/{len(supported_urls)}: {url}")
                    
                    success = await process_single_video(
                        update, 
                        url, 
                        video_index=index, 
                        total_videos=len(supported_urls),
                        delay_seconds=3
                    )
                    
                    if success:
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                
                # Trimite raportul final
                if confirmation_message:
                    final_report = f"📊 Procesare completă!\n\n"
                    final_report += f"✅ Videoclipuri descărcate cu succes: {successful_downloads}\n"
                    if failed_downloads > 0:
                        final_report += f"❌ Videoclipuri cu erori: {failed_downloads}\n"
                    final_report += f"\n🎉 Toate videoclipurile au fost procesate!"
                    
                    await safe_edit_message(confirmation_message, final_report)
                    
                    # Șterge raportul final după 10 secunde
                    await asyncio.sleep(10)
                    await safe_delete_message(confirmation_message)
            
            else:
                # Un singur URL - procesează normal
                await process_single_video(update, supported_urls[0])
        
        else:
            # Verifică dacă mesajul conține URL-uri nesuportate
            if all_urls:
                unsupported_message = "❌ Link-urile găsite nu sunt suportate.\n\n"
                unsupported_message += "🔗 URL-uri detectate:\n"
                for url in all_urls[:3]:  # Afișează doar primele 3
                    unsupported_message += f"• {url[:50]}{'...' if len(url) > 50 else ''}\n"
                if len(all_urls) > 3:
                    unsupported_message += f"• ... și încă {len(all_urls) - 3} URL-uri\n"
                unsupported_message += "\n"
            else:
                unsupported_message = "❌ Nu am găsit link-uri valide în mesaj.\n\n"
            
            unsupported_message += "🔗 Platforme suportate:\n"
            unsupported_message += "• TikTok\n"
            unsupported_message += "• Instagram\n"
            unsupported_message += "• Facebook\n"
            unsupported_message += "• Twitter/X\n"
            unsupported_message += "• Threads\n"
            unsupported_message += "• Pinterest\n"
            unsupported_message += "• Reddit\n"
            unsupported_message += "• Vimeo\n"
            unsupported_message += "• Dailymotion\n\n"
            unsupported_message += "💡 Trimite link-uri valide pentru a descărca videoclipurile."
            
            await safe_send_message(update, unsupported_message)
            
    except Exception as e:
        logger.error(f"Eroare generală în handle_message: {e}")
        # Încearcă să trimită un mesaj de eroare generică dacă este posibil
        try:
            await safe_send_message(
                update,
                "❌ A apărut o eroare neașteptată. Te rog să încerci din nou."
            )
        except Exception as e:
            logger.error(f"Nu s-a putut trimite mesajul de eroare generică: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionează callback-urile de la butoanele inline
    """
    try:
        # Verifică dacă update-ul și callback query sunt valide
        if not update or not update.callback_query:
            logger.warning("Callback query invalid primit")
            return
            
        query = update.callback_query
        
        # Răspunde la callback query în mod sigur
        try:
            await query.answer()
        except Exception as e:
            error_msg = str(e).lower()
            if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
                logger.warning(f"Nu se poate răspunde la callback - chat inaccesibil: {e}")
                return
            else:
                logger.error(f"Eroare la răspunsul callback-ului: {e}")
        
        if query.data == 'help':
            help_text = """
🆘 <b>Cum să folosești botul:</b>

1. Copiază link-ul videoclipului
2. Trimite-l în acest chat
3. Așteaptă să fie procesat
4. Primești videoclipul descărcat

🔗 <b>Platforme suportate:</b>
- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Facebook (facebook.com, fb.watch)
- Twitter/X (twitter.com, x.com)

⚠️ <b>Probleme frecvente:</b>
- Videoclipul este privat → Nu poate fi descărcat
- Videoclipul este prea lung → Max 15 minute
- Link invalid → Verifică că link-ul este corect
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, help_text, parse_mode='HTML', reply_markup=reply_markup)
            
        elif query.data == 'platforms':
            platforms_text = """
🔗 <b>Platforme suportate:</b>

✅ <b>TikTok</b>
- tiktok.com
- vm.tiktok.com

✅ <b>Instagram</b>
- instagram.com
- Reels, IGTV, Posts video

✅ <b>Facebook</b>
- facebook.com
- fb.watch
- m.facebook.com

✅ <b>Twitter/X</b>
- twitter.com
- x.com
- mobile.twitter.com

⚠️ <b>Notă:</b> Doar videoclipurile publice pot fi descărcate.

❌ <b>YouTube nu este suportat momentan</b> din cauza complexității tehnice și a restricțiilor platformei.
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, platforms_text, parse_mode='HTML', reply_markup=reply_markup)
            
        elif query.data == 'settings':
            settings_text = """
⚙️ <b>Setări și limitări:</b>

📏 <b>Limitări de dimensiune:</b>
- Durată maximă: 3 ore
- Calitate maximă: 720p
- Dimensiune maximă: 550MB

🚫 <b>Restricții:</b>
- Doar videoclipuri publice
- Nu se suportă livestream-uri
- Nu se suportă playlist-uri

⚡ <b>Performanță:</b>
- Timp mediu de procesare: 30-60 secunde
- Depinde de dimensiunea videoclipului
- Server gratuit cu limitări

🔒 <b>Confidențialitate:</b>
- Nu salvez videoclipurile
- Nu salvez link-urile
- Procesare temporară
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, settings_text, parse_mode='HTML', reply_markup=reply_markup)
            
        elif query.data == 'faq':
            faq_text = """
❓ <b>Întrebări frecvente:</b>

<b>Q: De ce nu funcționează link-ul meu?</b>
A: Verifică că videoclipul este public și de pe o platformă suportată.

<b>Q: Cât timp durează descărcarea?</b>
A: De obicei 30-60 secunde, depinde de dimensiunea videoclipului.

<b>Q: Pot descărca videoclipuri private?</b>
A: Nu, doar videoclipurile publice pot fi descărcate.

<b>Q: Ce calitate au videoclipurile?</b>
A: Maxim 720p pentru a respecta limitările serverului.

<b>Q: Botul nu răspunde?</b>
A: Serverul gratuit poate fi în hibernare. Încearcă din nou în câteva minute.

<b>Q: Pot descărca playlist-uri?</b>
A: Nu, doar videoclipuri individuale.
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, faq_text, parse_mode='HTML', reply_markup=reply_markup)
            
        elif query.data == 'ping_again':
            start_time = time.time()
            await safe_edit_callback_message(query, "🏓 <b>Ping...</b>", parse_mode='HTML')
            end_time = time.time()
            ping_time = round((end_time - start_time) * 1000, 1)
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(
                query,
                f"🏓 <b>Pong!</b>\n\n⏱️ <b>Timp răspuns:</b> {ping_time}ms\n✅ <b>Status:</b> Funcțional",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        elif query.data == 'wakeup_server':
            await safe_edit_callback_message(query, "🌅 Server trezit! Botul este activ și gata de utilizare.")
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await asyncio.sleep(2)
            await safe_edit_callback_message(
                query,
                "✅ Server activ!\n🤖 Botul funcționează normal.",
                reply_markup=reply_markup
            )
            
        elif query.data == 'back_to_menu':
            welcome_message = """
🎬 <b>Bot Descărcare Video</b>

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 <b>Platforme suportate:</b>
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X

⚠️ <b>Limitări:</b>
- Videoclipuri max 15 minute
- Calitate max 720p
- Doar videoclipuri publice
            """
            
            keyboard = [
                [InlineKeyboardButton("📖 Cum să folosesc botul", callback_data='help')],
                [InlineKeyboardButton("🔗 Platforme suportate", callback_data='platforms')],
                [InlineKeyboardButton("⚙️ Setări și limitări", callback_data='settings')],
                [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')],
                [InlineKeyboardButton("🔄 Ping Server", callback_data='ping_again'), InlineKeyboardButton("🌅 Wakeup Server", callback_data='wakeup_server')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, welcome_message, parse_mode='HTML', reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Eroare generală în button_callback: {e}")
        # Încearcă să răspundă la callback query dacă nu s-a făcut deja
        try:
            if update and update.callback_query:
                await update.callback_query.answer("❌ A apărut o eroare neașteptată.")
        except Exception as e:
            logger.error(f"Nu s-a putut răspunde la callback query: {e}")

# Handler-ii vor fi adăugați, iar aplicația va fi inițializată la primul request

# Adaugă handler-ele la application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("menu", menu_command))
application.add_handler(CommandHandler("ping", ping_command))
application.add_handler(CommandHandler("log", log_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(button_callback))

# Flask routes
@app.route('/')
def index():
    return jsonify({
        'status': 'Bot is running',
        'message': 'Telegram Video Downloader Bot is active'
    })

# Configurații simplificate pentru webhook-uri
# Thread pool eliminat pentru a evita problemele în producție

# Rate limiting și deduplicare pentru Render free tier
processed_messages = set()
user_last_request = {}  # chat_id -> timestamp
MAX_REQUESTS_PER_MINUTE = 3  # Limită agresivă pentru Render free tier

def is_rate_limited(chat_id):
    """Verifică dacă utilizatorul este rate limited"""
    current_time = time.time()
    
    if chat_id in user_last_request:
        time_diff = current_time - user_last_request[chat_id]
        if time_diff < 60 / MAX_REQUESTS_PER_MINUTE:  # 20 secunde între cereri
            metrics.record_rate_limit()
            return True
    
    user_last_request[chat_id] = current_time
    
    # Cleanup periodic pentru a economisi memorie
    if len(user_last_request) > 100:
        # Păstrează doar ultimele 50 de utilizatori
        sorted_users = sorted(user_last_request.items(), key=lambda x: x[1], reverse=True)
        user_last_request.clear()
        user_last_request.update(dict(sorted_users[:50]))
    
    return False

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Procesează webhook-urile de la Telegram - Optimizat pentru Render"""
    try:
<<<<<<< HEAD
        # Cleanup fișiere temporare pentru Render
        if is_render_environment():
            cleanup_render_temp_files()
        
        # Dacă este o cerere GET, returnează status OK
        if request.method == 'GET':
            return jsonify({'status': 'webhook_ready', 'method': 'GET', 'environment': 'render' if is_render_environment() else 'local'}), 200
            
=======
        # Înregistrează cererea webhook pentru metrici
        metrics.record_webhook_request()
        
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
        # Obține datele JSON de la Telegram
        json_data = request.get_json()
        
        if not json_data:
<<<<<<< HEAD
            if is_render_environment():
                logger.error("[RENDER] Nu s-au primit date JSON")
            else:
                logger.error("Nu s-au primit date JSON")
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
=======
            return jsonify({'status': 'ok'}), 200  # Returnează OK pentru a evita retry-urile
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
        
        # Logging optimizat pentru Render
        if is_render_environment():
            logger.info(f"[RENDER] Webhook primit: update_id={json_data.get('update_id', 'N/A')}")
        else:
            logger.info(f"Webhook primit: {json_data}")
        
        # Procesare simplificată fără crearea obiectului Update
        if 'message' in json_data:
            message = json_data['message']
            if 'chat' in message and 'id' in message['chat']:
                chat_id = message['chat']['id']
                text = message.get('text', '')
                message_id = message.get('message_id')
                
                # Creează un identificator unic pentru mesaj
                unique_id = f"{chat_id}_{message_id}_{text}"
                
                # Verifică dacă mesajul a fost deja procesat
                if unique_id in processed_messages:
                    logger.info(f"Mesaj deja procesat, ignorat: {unique_id}")
                    return jsonify({'status': 'ok'}), 200
                
                # Adaugă mesajul la lista celor procesate
                processed_messages.add(unique_id)
                
                # Limitează dimensiunea set-ului (păstrează ultimele 1000 de mesaje)
                if len(processed_messages) > 1000:
                    processed_messages.clear()
                
                # Pentru link-urile Facebook, nu bloca procesarea, doar previne mesajele duplicate
                # Mecanismul de debouncing pentru erori este gestionat în download_video_sync
                
                # Extrage user_id din mesaj
                user_id = None
                if 'from' in message and 'id' in message['from']:
                    user_id = message['from']['id']
                
                # Verificări de securitate suplimentare pentru utilizatori
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
                if user_id and security_monitor.is_user_blocked(str(user_id)):
                    logger.warning(f"Utilizator blocat: {user_id} de la IP: {client_ip}")
                    return jsonify({'status': 'blocked'}), 403
                
                # Analizează cererea pentru amenințări specifice utilizatorului
                security_monitor.analyze_request({
                    'ip': client_ip,
                    'user_id': str(user_id) if user_id else None,
                    'text': text,
                    'chat_id': str(chat_id),
                    'timestamp': time.time()
                })
                
                # Sanitizează input-ul
                sanitized_text = input_sanitizer.sanitize_text(text, ValidationLevel.STRICT)
                
                logger.info(f"Procesez mesaj de la chat_id: {chat_id}, text: {sanitized_text}")
                
                # Procesează mesajul și trimite răspuns
                try:
                    if text == '/start':
                        welcome_text = (
                            "🎬 <b>Bun venit la Video Downloader Bot!</b>\n\n"
                            "📱 Trimite-mi un link de pe:\n"
                            "• TikTok\n"
                            "• Instagram\n"
                            "• Facebook\n"
                            "• Twitter/X\n\n"
                            "🔗 Doar copiază și lipește link-ul aici!"
                        )
                        success = send_telegram_message(chat_id, welcome_text)
                        logger.info(f"Mesaj de bun venit trimis: {success}")
                        
                    elif text == '/help':
                        help_text = (
                            "🤖 <b>Bot Descărcare Video - Ghid Complet</b>\n\n"
                            "📋 <b>Comenzi disponibile:</b>\n"
                            "• /start - Pornește botul și afișează meniul\n"
                            "• /help - Afișează acest ghid complet\n"
                            "• /menu - Revine la meniul principal\n"
                            "• /ping - Verifică dacă botul funcționează\n\n"
                            "🆘 <b>Cum să folosești botul:</b>\n"
                            "1️⃣ Copiază link-ul videoclipului\n"
                            "2️⃣ Trimite-l în acest chat\n"
                            "3️⃣ Așteaptă să fie procesat (30s-2min)\n"
                            "4️⃣ Primești videoclipul descărcat automat\n\n"
                            "🔗 <b>Platforme suportate:</b>\n"
                            "• TikTok (tiktok.com, vm.tiktok.com)\n"
                            "• Instagram (instagram.com, reels, stories)\n"
                            "• Facebook (facebook.com, fb.watch, fb.me)\n"
                            "• Twitter/X (twitter.com, x.com)\n"
                            "• Threads (threads.net, threads.com)\n"
                            "• Pinterest (pinterest.com, pin.it)\n"
                            "• Reddit (reddit.com, redd.it, v.redd.it)\n"
                            "• Vimeo (vimeo.com, player.vimeo.com)\n"
                            "• Dailymotion (dailymotion.com, dai.ly)\n\n"
                            "⚠️ <b>Limitări importante:</b>\n"
                            "• Mărime max: 45MB (limita Telegram)\n"
                            "• Durată max: 3 ore\n"
                            "• Calitate max: 720p\n"
                            "• Doar videoclipuri publice\n\n"
                            "💡 <b>Sfaturi:</b>\n"
                            "• Folosește link-uri directe\n"
                            "• Verifică că videoclipul este public\n"
                            "• Pentru probleme, folosește /ping"
                        )
                        success = send_telegram_message(chat_id, help_text)
                        logger.info(f"Mesaj de ajutor trimis: {success}")
                        
                    elif sanitized_text and ('tiktok.com' in sanitized_text or 'instagram.com' in sanitized_text or 'facebook.com' in sanitized_text or 'fb.watch' in sanitized_text or 'twitter.com' in sanitized_text or 'x.com' in sanitized_text or 'threads.net' in sanitized_text or 'threads.com' in sanitized_text or 'pinterest.com' in sanitized_text or 'pin.it' in sanitized_text or 'reddit.com' in sanitized_text or 'redd.it' in sanitized_text or 'vimeo.com' in sanitized_text or 'dailymotion.com' in sanitized_text or 'dai.ly' in sanitized_text):
                        logger.info(f"Link video detectat: {sanitized_text}")
                        # Procesează link-ul video
                        process_video_link_sync(chat_id, sanitized_text, user_id)
                        
                    else:
                        success = send_telegram_message(chat_id, "❌ Te rog trimite un link valid de video sau folosește /help pentru ajutor.")
                        logger.info(f"Mesaj de eroare trimis: {success}")
                        
                except Exception as msg_error:
                    logger.error(f"Eroare la procesarea mesajului: {msg_error}")
                    # Nu ridica excepția, doar loghează
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Eroare în webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def send_telegram_message(chat_id, text, reply_markup=None):
    """Trimite mesaj prin API-ul Telegram cu fallback automat și validare chat_id"""
    # Validează chat_id înainte de trimitere
    if not validate_chat_id(chat_id):
        logger.error(f"Încercare trimitere mesaj către chat_id invalid: {chat_id}")
        return False
    
    # Escapează textul pentru HTML
    text_safe = escape_html(text) if text else ""
    return safe_send_with_fallback(chat_id, text_safe, 'HTML', reply_markup)

def process_message_sync(update):
    """Procesează mesajele în mod sincron"""
    try:
        logger.info("=== PROCESSING MESSAGE ===")
        
        # Verifică dacă update-ul are mesaj
        if not hasattr(update, 'message') or not update.message:
            logger.error("Update nu conține mesaj valid")
            return
            
        message = update.message
        logger.info(f"Message received: {type(message)}")
        
        # Obține chat_id în mod simplu
        try:
            chat_id = message.chat.id
            logger.info(f"Chat ID: {chat_id}")
        except Exception as e:
            logger.error(f"Nu se poate obține chat_id: {e}")
            return
            
        # Obține textul mesajului
        try:
            text = message.text
            logger.info(f"Message text: {text}")
        except Exception as e:
            logger.error(f"Nu se poate obține textul mesajului: {e}")
            return
        
        # Obține user_id din mesaj
        user_id = None
        try:
            if hasattr(message, 'from_user') and message.from_user:
                user_id = message.from_user.id
            elif hasattr(message, 'from') and message.from_:
                user_id = message.from_.id
            logger.info(f"User ID: {user_id}")
        except Exception as e:
            logger.error(f"Nu se poate obține user_id: {e}")
        
        # Verifică dacă mesajul are text
        if not text:
            logger.info("No text in message, returning")
            return
        
        if text == '/start':
            welcome_text = (
                "🎬 <b>Bun venit la Video Downloader Bot!</b>\n\n"
                "📱 Trimite-mi un link de pe:\n"
                "• TikTok\n"
                "• Instagram\n"
                "• Facebook\n"
                "• Twitter/X\n\n"
                "🔗 Doar copiază și lipește link-ul aici!"
            )
            send_telegram_message(chat_id, welcome_text)
            
        elif text == '/help':
            help_text = (
                "🤖 <b>Bot Descărcare Video - Ghid Complet</b>\n\n"
                "📋 <b>Comenzi disponibile:</b>\n"
                "• /start - Pornește botul și afișează meniul\n"
                "• /help - Afișează acest ghid complet\n"
                "• /menu - Revine la meniul principal\n"
                "• /ping - Verifică dacă botul funcționează\n\n"
                "🆘 <b>Cum să folosești botul:</b>\n"
                "1️⃣ Copiază link-ul videoclipului\n"
                "2️⃣ Trimite-l în acest chat\n"
                "3️⃣ Așteaptă să fie procesat (30s-2min)\n"
                "4️⃣ Primești videoclipul descărcat automat\n\n"
                "🔗 <b>Platforme suportate:</b>\n"
                "• TikTok (tiktok.com, vm.tiktok.com)\n"
                "• Instagram (instagram.com, reels, stories)\n"
                "• Facebook (facebook.com, fb.watch, fb.me)\n"
                "• Twitter/X (twitter.com, x.com)\n"
                "• Threads (threads.net, threads.com)\n"
                "• Pinterest (pinterest.com, pin.it)\n"
                "• Reddit (reddit.com, redd.it, v.redd.it)\n"
                "• Vimeo (vimeo.com, player.vimeo.com)\n"
                "• Dailymotion (dailymotion.com, dai.ly)\n\n"
                "⚠️ <b>Limitări importante:</b>\n"
                "• Mărime max: 45MB (limita Telegram)\n"
                "• Durată max: 3 ore\n"
                "• Calitate max: 720p\n"
                "• Doar videoclipuri publice\n\n"
                "💡 <b>Sfaturi:</b>\n"
                "• Folosește link-uri directe\n"
                "• Verifică că videoclipul este public\n"
                "• Pentru probleme, folosește /ping"
            )
            send_telegram_message(chat_id, help_text)
            
        elif text and ('tiktok.com' in text or 'instagram.com' in text or 'facebook.com' in text or 'fb.watch' in text or 'twitter.com' in text or 'x.com' in text or 'threads.net' in text or 'threads.com' in text or 'pinterest.com' in text or 'pin.it' in text or 'reddit.com' in text or 'redd.it' in text or 'vimeo.com' in text or 'dailymotion.com' in text or 'dai.ly' in text):
            # Procesează link-ul video
            process_video_link_sync(chat_id, text, user_id)
            
        else:
            send_telegram_message(chat_id, "❌ Te rog trimite un link valid de video sau folosește /help pentru ajutor.")
            
    except Exception as e:
        logger.error(f"Eroare la procesarea mesajului: {e}")

def process_callback_sync(update):
    """Procesează callback-urile în mod sincron"""
    try:
        query = update.callback_query
        if not query or not query.message:
            return
            
        # Accesează chat_id în mod sigur
        if hasattr(query.message, 'chat_id'):
            chat_id = query.message.chat_id
        elif hasattr(query.message, 'chat') and hasattr(query.message.chat, 'id'):
            chat_id = query.message.chat.id
        else:
            logger.error("Nu se poate obține chat_id din callback")
            return
            
        data = query.data if hasattr(query, 'data') else None
        
        if not data:
            return
        
        # Răspunde la callback pentru a elimina loading-ul
        answer_callback_query(query.id)
        
        # Callback-urile pentru descărcare cu calitate au fost eliminate
        # Descărcarea se face automat în 720p când se trimite un link
        
    except Exception as e:
        logger.error(f"Eroare la procesarea callback-ului: {e}")

def answer_callback_query(callback_query_id):
    """Răspunde la callback query"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
        data = {'callback_query_id': callback_query_id}
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        logger.error(f"Eroare la răspunsul callback: {e}")

def process_video_link_sync(chat_id, url, user_id=None):
    """Procesează link-ul video în mod sincron și descarcă automat în 720p"""
    try:
        # Verifică dacă URL-ul este suportat
        if not is_supported_url(url):
            send_telegram_message(chat_id, "❌ Link-ul nu este suportat. Încearcă cu TikTok, Instagram, Facebook, Twitter/X, Threads, Pinterest, Reddit, Vimeo sau Dailymotion.")
            return
        
        # Trimite mesaj de procesare
        send_telegram_message(chat_id, "✅ Procesez și descarc video-ul în 720p te rog asteapta")
        
        # Descarcă direct în calitate 720p
        download_video_sync(chat_id, url, user_id)
        
    except Exception as e:
        logger.error(f"Eroare la procesarea link-ului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la procesarea video-ului. Încearcă din nou.")

# Set pentru a preveni mesajele repetate de eroare
error_messages_sent = set()

def download_video_sync(chat_id, url, user_id=None):
    """Descarcă video-ul în mod sincron în 720p"""
    global error_messages_sent
    
    try:
        # Descarcă video-ul (funcția download_video folosește deja format 720p)
        result = download_video(url)
        
        if result['success']:
            # Log succesul descărcării
            log_download_success(result.get('platform', 'unknown'), url, 0, user_id or chat_id, chat_id)
            # Trimite fișierul cu toate informațiile
            send_video_file(chat_id, result['file_path'], result)
            # Șterge din cache-ul de erori dacă descărcarea a reușit
            error_key = f"{chat_id}_{url}"
            error_messages_sent.discard(error_key)
        else:
            # Log eroarea descărcării
            error_msg = result.get('error', 'Eroare necunoscută')
            log_download_error(result.get('platform', 'unknown'), url, error_msg, user_id or chat_id, chat_id)
            # Previne trimiterea de mesaje repetate de eroare pentru același URL
            error_key = f"{chat_id}_{url}"
            if error_key not in error_messages_sent:
                send_telegram_message(chat_id, f"❌ Eroare la descărcare: {error_msg}")
                error_messages_sent.add(error_key)
                # Limitează cache-ul de erori
                if len(error_messages_sent) > 100:
                    error_messages_sent.clear()
            else:
                logger.info(f"Mesaj de eroare deja trimis pentru {error_key}, ignorat")
            
    except Exception as e:
        logger.error(f"Eroare la descărcarea video-ului: {e}")
        # Log eroarea generală
        log_download_error('unknown', url, f"Exception: {str(e)}", user_id or chat_id, chat_id)
        # Previne trimiterea de mesaje repetate de eroare pentru excepții
        error_key = f"{chat_id}_{url}_exception"
        if error_key not in error_messages_sent:
            send_telegram_message(chat_id, "❌ Eroare la descărcarea video-ului. Încearcă din nou.")
            error_messages_sent.add(error_key)
            # Limitează cache-ul de erori
            if len(error_messages_sent) > 100:
                error_messages_sent.clear()
        else:
            logger.info(f"Mesaj de eroare pentru excepție deja trimis pentru {error_key}, ignorat")

def send_video_file(chat_id, file_path, video_info):
    """Trimite fișierul video prin Telegram"""
    try:
        import requests
        import os
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
        
        # Creează caption-ul detaliat
        title = video_info.get('title', 'Video')
        uploader = video_info.get('uploader', '')
        description = video_info.get('description', '')
        duration = video_info.get('duration', 0)
        file_size = video_info.get('file_size', 0)
        
        # Formatează durata cu verificări de tip
        if duration and isinstance(duration, (int, float)) and duration > 0:
            try:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            except (TypeError, ValueError):
                duration_str = "N/A"
        else:
            duration_str = "N/A"
        
        # Formatează dimensiunea fișierului cu verificări de tip
        if file_size and isinstance(file_size, (int, float)) and file_size > 0:
            try:
                size_mb = float(file_size) / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB"
            except (TypeError, ValueError):
                size_str = "N/A"
        else:
            size_str = "N/A"
        
        # Verificări suplimentare pentru fișierul video
        if not os.path.exists(file_path):
            logger.error(f"Fișierul video nu există: {file_path}")
            send_telegram_message(chat_id, "❌ Fișierul video nu a fost găsit.")
            return
        
        # Verifică mărimea fișierului (Telegram Bot API are limită strictă de 50MB)
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_bytes > 45 * 1024 * 1024:  # 45MB (buffer de siguranță pentru limita Telegram de 50MB)
            logger.error(f"Fișierul este prea mare: {file_size_mb:.1f}MB")
            
            # Mesaj detaliat pentru utilizator
            error_message = (
                f"❌ **Fișierul este prea mare pentru Telegram**\n\n"
                f"📊 **Dimensiune fișier:** {file_size_mb:.1f}MB\n"
                f"⚠️ **Limita Telegram:** 50MB (pentru bot-uri)\n\n"
                f"💡 **Soluții:**\n"
                f"• Încearcă un clip mai scurt\n"
                f"• Folosește o calitate mai mică\n"
                f"• Împarte clipul în segmente mai mici\n\n"
                f"🔧 Această limită este impusă de Telegram API și nu poate fi depășită."
            )
            
            send_telegram_message(chat_id, error_message)
            try:
                # Șterge fișierul
                os.remove(file_path)
                
                # Dacă fișierul era într-un director temporar, șterge și directorul
                parent_dir = os.path.dirname(file_path)
                if 'tmp' in parent_dir.lower() or 'temp' in parent_dir.lower():
                    try:
                        import shutil
                        if os.path.exists(parent_dir) and os.path.isdir(parent_dir):
                            shutil.rmtree(parent_dir)
                            logger.info(f"Director temporar șters: {parent_dir}")
                    except Exception as cleanup_error:
                        logger.warning(f"Nu s-a putut șterge directorul temporar {parent_dir}: {cleanup_error}")
            except Exception as file_error:
                logger.warning(f"Nu s-a putut șterge fișierul {file_path}: {file_error}")
            return
        
        # Folosește funcția centrală pentru caption sigur
        caption = create_safe_caption(
            title=title,
            uploader=uploader,
            description=description,
            duration=duration,
            file_size=file_size
        )
        
        logger.info(f"Trimit video de {file_size_bytes / (1024*1024):.1f}MB pentru chat {chat_id}")
        
        with open(file_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            # Timeout mărit pentru Render (600 secunde = 10 minute)
            response = requests.post(url, files=files, data=data, timeout=(30, 600))
            
            # Dacă eșuează cu HTML, încearcă fără parse_mode
            if response.status_code != 200:
                logger.warning(f"Eroare cu HTML parse_mode: {response.status_code} - {response.text[:200]}")
                logger.info("Încerc să trimit caption fără parse_mode...")
                
                # Reset file pointer
                video_file.seek(0)
                
                data_fallback = {
                    'chat_id': chat_id,
                    'caption': caption  # Fără parse_mode
                }
                
                # Timeout mărit pentru fallback
                response = requests.post(url, files={'video': video_file}, data=data_fallback, timeout=(30, 600))
            
        # Șterge fișierul temporar și directorul părinte dacă este temporar
        try:
            # Șterge fișierul
            os.remove(file_path)
            
            # Dacă fișierul era într-un director temporar, șterge și directorul
            parent_dir = os.path.dirname(file_path)
            if 'tmp' in parent_dir.lower() or 'temp' in parent_dir.lower():
                try:
                    import shutil
                    if os.path.exists(parent_dir) and os.path.isdir(parent_dir):
                        shutil.rmtree(parent_dir)
                        logger.info(f"Director temporar șters: {parent_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Nu s-a putut șterge directorul temporar {parent_dir}: {cleanup_error}")
        except Exception as file_error:
            logger.warning(f"Nu s-a putut șterge fișierul {file_path}: {file_error}")
            
        if response.status_code == 200:
            logger.info(f"Video trimis cu succes pentru chat {chat_id}")
        else:
            # Log mai detaliat pentru debugging
            try:
                error_details = response.json()
                logger.error(f"Eroare la trimiterea video-ului: {response.status_code} - {error_details}")
            except Exception as e:
                logger.error(f"Eroare la parsarea răspunsului JSON pentru video: {e}. Status: {response.status_code} - Text: {response.text[:200]}")
            
            # Verifică tipul erorii și trimite mesaj corespunzător
            if response.status_code == 400:
                send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului. Fișierul poate fi corupt sau prea mare.")
            elif response.status_code == 413:
                error_message = (
                    "❌ **Fișierul este prea mare pentru Telegram**\n\n"
                    "⚠️ **Limita Telegram:** 50MB (pentru bot-uri)\n\n"
                    "💡 **Soluții:**\n"
                    "• Încearcă un clip mai scurt\n"
                    "• Folosește o calitate mai mică\n"
                    "• Împarte clipul în segmente mai mici"
                )
                send_telegram_message(chat_id, error_message)
            else:
                send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului. Încearcă din nou.")
            
    except Exception as e:
        logger.error(f"Eroare la trimiterea fișierului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului.")


@app.route('/get_webhook_info', methods=['GET'])
def get_webhook_info():
    """Endpoint pentru verificarea informațiilor despre webhook"""
    try:
        import requests
        
        if TOKEN == "PLACEHOLDER_TOKEN":
            return jsonify({
                'status': 'error',
                'message': 'TOKEN nu este setat corect',
                'token_status': 'PLACEHOLDER_TOKEN'
            }), 400
        
        telegram_api_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
        response = requests.get(telegram_api_url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'webhook_info': result,
                'token_status': 'VALID' if result.get('ok') else 'INVALID'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'HTTP error {response.status_code}',
                'response': response.text
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error: {type(e).__name__}: {str(e)}'
        }), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        # Verifică dacă TOKEN-ul este valid
        if TOKEN == "PLACEHOLDER_TOKEN":
            logger.error("TOKEN nu este setat corect - încă este PLACEHOLDER_TOKEN")
            return jsonify({
                'status': 'error',
                'message': 'TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu Render',
                'token_status': 'PLACEHOLDER_TOKEN',
                'instructions': 'Verifică Render Dashboard -> Environment Variables'
            }), 400
        
        # Forțează HTTPS pentru webhook-ul Telegram (necesar pentru Render)
        current_url = request.url_root.rstrip('/')
        # Înlocuiește HTTP cu HTTPS dacă este necesar
        if current_url.startswith('http://'):
            current_url = current_url.replace('http://', 'https://', 1)
        webhook_url = f"{current_url}/webhook"
        
        logger.info(f"Încercare setare webhook la: {webhook_url}")
        logger.info(f"TOKEN status: {'VALID' if TOKEN != 'PLACEHOLDER_TOKEN' else 'PLACEHOLDER'}")
        
        # Folosește requests direct pentru a evita problemele cu event loop-ul
        import requests
        
        telegram_api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
        payload = {'url': webhook_url}
        
        response = requests.post(telegram_api_url, data=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"Webhook setat cu succes la: {webhook_url}")
                return jsonify({
                    'status': 'success',
                    'message': f'Webhook setat la: {webhook_url}',
                    'telegram_response': result
                })
            else:
                logger.error(f"Telegram API a returnat eroare: {result}")
                return jsonify({
                    'status': 'error',
                    'message': f'Telegram API error: {result.get("description", "Unknown error")}'
                }), 500
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text}")
            return jsonify({
                'status': 'error',
                'message': f'HTTP error {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Eroare la setarea webhook-ului: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {type(e).__name__}: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint pentru verificarea stării aplicației"""
    try:
        import time
        # Returnează întotdeauna status healthy pentru Render
        return jsonify({
            'status': 'healthy',
            'message': 'Bot is running',
            'webhook_mode': 'simplified',
            'timestamp': time.time()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/debug', methods=['GET'])
def debug():
    """Endpoint pentru debug - testează inițializarea aplicației"""
    try:
        import time
        # Testează inițializarea aplicației
        ensure_app_initialized()
        return jsonify({
            'status': 'success',
            'app_initialized': _app_initialized,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'server': 'online'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }), 500

@app.route('/ping', methods=['GET'])
def ping_endpoint():
    """Endpoint simplu pentru ping"""
    import time
    return jsonify({
        'pong': True,
        'timestamp': time.time(),
        'status': 'alive'
    })

<<<<<<< HEAD
@app.route('/security/status', methods=['GET'])
def security_status():
    """Endpoint pentru monitorizarea stării securității"""
    try:
        status = security_monitor.get_security_status()
        return jsonify({
            'status': 'ok',
            'security_status': status,
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Eroare la obținerea stării securității: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Security status unavailable'
        }), 500

@app.route('/security/threats', methods=['GET'])
def recent_threats():
    """Endpoint pentru vizualizarea amenințărilor recente"""
    try:
        threats = security_monitor.get_recent_threats(limit=50)
        return jsonify({
            'status': 'ok',
            'threats': [threat.__dict__ for threat in threats],
            'count': len(threats),
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Eroare la obținerea amenințărilor: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Threats data unavailable'
=======
@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    """Endpoint pentru metrici și monitoring"""
    try:
        stats = metrics.get_stats()
        
        # Adaugă informații despre sistem dacă psutil este disponibil
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            stats['system'] = {
                'memory_mb': round(memory_mb, 1),
                'cpu_percent': round(cpu_percent, 1),
                'pid': process.pid
            }
        except ImportError:
            stats['system'] = {'note': 'psutil not available'}
        
        # Loghează statisticile periodic
        metrics.log_periodic_stats()
        
        return jsonify({
            'status': 'ok',
            'timestamp': time.time(),
            'metrics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Eroare la obținerea metricilor: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/reset_metrics', methods=['POST'])
def reset_metrics_endpoint():
    """Endpoint pentru resetarea metricilor"""
    try:
        metrics.reset_metrics()
        logger.info("📊 Metrici resetate")
        return jsonify({
            'status': 'ok',
            'message': 'Metrics reset successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Eroare la resetarea metricilor: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
        }), 500

# Funcție pentru inițializarea în contextul Flask
def ensure_app_initialized():
    """Asigură că aplicația și bot-ul sunt inițializate în contextul Flask"""
    global _app_initialized
    if not _app_initialized:
        try:
            logger.info("Încercare de inițializare simplificată...")
            # Marcăm ca inițializat pentru a evita blocarea
            _app_initialized = True
            logger.info("✅ Aplicația a fost marcată ca inițializată")
        except Exception as e:
            logger.error(f"❌ Eroare la inițializarea simplificată: {e}")
            # Nu aruncăm excepția pentru a nu bloca webhook-ul
            _app_initialized = True

# Inițializează aplicația la pornirea serverului
def initialize_on_startup():
    """Inițializează aplicația la pornire cu delay pentru prevenirea erorilor după hibernare"""
    try:
        # Delay inițial pentru a permite stabilizarea conexiunilor
        import time
        logger.info("⏳ Aștept 3 secunde pentru stabilizarea conexiunilor...")
        time.sleep(3)
        
        # Upgrade yt-dlp la versiunea nightly pentru fix-uri Facebook
        logger.info("🔄 Upgrading yt-dlp pentru fix-uri Facebook...")
        upgrade_success = upgrade_to_nightly_ytdlp()
        if upgrade_success:
            logger.info("✅ yt-dlp upgraded cu succes")
        else:
            logger.warning("⚠️ yt-dlp upgrade parțial sau eșuat")
        
        ensure_app_initialized()
        
        # Delay suplimentar pentru prima descărcare
        # Skip warming-up pe Render pentru startup rapid
        if not is_render_environment():
            logger.info("⏳ Pregătesc bot-ul pentru prima descărcare...")
            time.sleep(2)
            
            # Warming-up: testez funcția de caption pentru a încărca toate dependențele
            try:
                test_caption = create_safe_caption(
                    title="Test warming-up",
                    uploader="Bot",
                    description="Test pentru încărcarea dependențelor",
                    duration="0:01",
                    file_size="1 MB"
                )
                logger.info("🔥 Warming-up complet - toate dependențele sunt încărcate")
            except Exception as e:
                logger.warning(f"⚠️ Warming-up parțial - unele dependențe pot să nu fie încărcate: {e}")
        else:
            logger.info("[RENDER] Skip warming-up pentru startup rapid")
        
        logger.info("✅ Aplicația Telegram a fost inițializată la pornirea serverului")
        logger.info("🚀 Bot-ul este gata pentru descărcări!")
    except Exception as e:
        logger.error(f"❌ Eroare la inițializarea aplicației la pornire: {e}")

logger.info("Aplicația Telegram este configurată pentru webhook-uri")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    # Configurare optimizată pentru Render
    if is_render_environment():
        logger.info(f"[RENDER] Pornesc serverul Flask pe portul {port} cu configurație optimizată")
        setup_render_logging()
        cleanup_render_temp_files()
        
        # Configurări specifice pentru Render
        render_config = RENDER_OPTIMIZED_CONFIG.get('flask_config', {})
        logger.info(f"[RENDER] Aplicând configurații: {list(render_config.keys())}")
    else:
        logger.info(f"Pornesc serverul Flask pe portul {port}")
    
    # Nu mai inițializez la startup pentru a evita problemele
    logger.info("Serverul pornește fără inițializare complexă")
    
<<<<<<< HEAD
    # Pentru gunicorn, nu rulăm app.run() direct
    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=port, debug=False)
=======
    app.run(host='0.0.0.0', port=port, debug=False)
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
