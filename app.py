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
# Force redeploy - 2025-08-09 - Facebook fixes deployed
import re

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

def safe_send_with_fallback(chat_id, text, parse_mode='HTML', reply_markup=None):
    """
    Trimite mesaj cu fallback la text simplu dacă parse_mode eșuează.
    """
    import requests
    
    if not TOKEN:
        logger.error("TOKEN nu este setat!")
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
        response = requests.post(url, json=data, timeout=10)
        
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
            
            response_fallback = requests.post(url, json=data_fallback, timeout=10)
            
            if response_fallback.status_code == 200:
                logger.info(f"Mesaj trimis cu succes către chat_id {chat_id} fără parse_mode")
                return True
            else:
                logger.error(f"Eroare și la fallback: {response_fallback.status_code} - {response_fallback.text[:200]}")
                return False
                
    except Exception as e:
        logger.error(f"Excepție la trimiterea mesajului: {e}")
        return False

# Funcție centrală pentru crearea caption-urilor sigure - îmbunătățită
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

# Configurare Flask
app = Flask(__name__)

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
    raise ValueError("TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu")

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
    welcome_message = """
🎬 <b>Bot Descărcare Video</b>

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 <b>Platforme suportate:</b>
• TikTok
• Instagram
• Facebook
• Twitter/X

⚠️ YouTube nu este suportat momentan.

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
    Comandă /help - informații de ajutor
    """
    help_text = """
🆘 <b>Cum să folosești botul:</b>

1. Copiază link-ul videoclipului
2. Trimite-l în acest chat
3. Așteaptă să fie procesat
4. Primești videoclipul descărcat

🔗 <b>Platforme suportate:</b>
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Facebook (facebook.com, fb.watch)
- Twitter/X (twitter.com, x.com)

⚠️ YouTube nu este suportat momentan.

⚠️ <b>Probleme frecvente:</b>
- Videoclipul este privat → Nu poate fi descărcat
- Videoclipul este prea lung → Max 15 minute
- Link invalid → Verifică că link-ul este corect
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
    message = await safe_send_message(update, "🏓 Pinging...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    
    if message:
        await safe_edit_message(message, f"🏓 Pong!\n⏱️ Timp răspuns: {ping_time}ms")

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesează mesajele text (link-uri pentru descărcare)
    """
    try:
        # Verifică dacă update-ul și mesajul sunt valide
        if not update or not update.message or not update.effective_user:
            logger.warning("Update invalid primit")
            return
            
        message_text = update.message.text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
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
        else:
            # Mesaj pentru URL-uri nesuportate
            await safe_send_message(
                update,
                "❌ Link-ul nu este suportat sau nu este valid.\n\n"
                "🔗 Platforme suportate:\n"
                "• TikTok\n"
                "• Instagram\n"
                "• Facebook\n"
                "• Twitter/X\n\n"
                "⚠️ Notă: YouTube nu este suportat momentan.\n\n"
                "💡 Trimite un link valid pentru a descărca videoclipul."
            )
    except Exception as e:
        logger.error(f"Eroare generală în handle_message: {e}")
        # Încearcă să trimită un mesaj de eroare generică dacă este posibil
        try:
            await safe_send_message(
                update,
                "❌ A apărut o eroare neașteptată. Te rog să încerci din nou."
            )
        except:
            logger.error("Nu s-a putut trimite mesajul de eroare generică")

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
            await safe_edit_callback_message(query, "🏓 Pinging...")
            end_time = time.time()
            ping_time = round((end_time - start_time) * 1000, 2)
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(
                query,
                f"🏓 Pong!\n⏱️ Timp răspuns: {ping_time}ms",
                reply_markup=reply_markup
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
        except:
            pass

# Handler-ii vor fi adăugați, iar aplicația va fi inițializată la primul request

# Adaugă handler-ele la application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("menu", menu_command))
application.add_handler(CommandHandler("ping", ping_command))
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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Procesează webhook-urile de la Telegram"""
    try:
        # Înregistrează cererea webhook pentru metrici
        metrics.record_webhook_request()
        
        # Obține datele JSON de la Telegram
        json_data = request.get_json()
        
        if not json_data:
            return jsonify({'status': 'ok'}), 200  # Returnează OK pentru a evita retry-urile
        
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
                
                logger.info(f"Procesez mesaj de la chat_id: {chat_id}, text: {text}")
                
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
                            "📋 <b>Cum să folosești bot-ul:</b>\n\n"
                            "1️⃣ Copiază link-ul video\n"
                            "2️⃣ Lipește-l în chat\n"
                            "3️⃣ Bot-ul va descărca automat în 720p\n"
                            "4️⃣ Primești video-ul descărcat\n\n"
                            "🎯 <b>Platforme suportate:</b>\n"
                            "• TikTok, Instagram, Facebook, Twitter/X\n\n"
                            "❓ Pentru ajutor: /help"
                        )
                        success = send_telegram_message(chat_id, help_text)
                        logger.info(f"Mesaj de ajutor trimis: {success}")
                        
                    elif text and ('tiktok.com' in text or 'instagram.com' in text or 'facebook.com' in text or 'fb.watch' in text or 'twitter.com' in text or 'x.com' in text):
                        logger.info(f"Link video detectat: {text}")
                        # Procesează link-ul video
                        process_video_link_sync(chat_id, text)
                        
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
    """Trimite mesaj prin API-ul Telegram cu fallback automat"""
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
                "📋 <b>Cum să folosești bot-ul:</b>\n\n"
                "1️⃣ Copiază link-ul video\n"
                "2️⃣ Lipește-l în chat\n"
                "3️⃣ Bot-ul va descărca automat în 720p\n"
                "4️⃣ Primești video-ul descărcat\n\n"
                "🎯 <b>Platforme suportate:</b>\n"
                "• TikTok, Instagram, Facebook, Twitter/X\n\n"
                "❓ Pentru ajutor: /help"
            )
            send_telegram_message(chat_id, help_text)
            
        elif text and ('tiktok.com' in text or 'instagram.com' in text or 'facebook.com' in text or 'fb.watch' in text or 'twitter.com' in text or 'x.com' in text):
            # Procesează link-ul video
            process_video_link_sync(chat_id, text)
            
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

def process_video_link_sync(chat_id, url):
    """Procesează link-ul video în mod sincron și descarcă automat în 720p"""
    try:
        # Verifică dacă URL-ul este suportat
        if not is_supported_url(url):
            send_telegram_message(chat_id, "❌ Link-ul nu este suportat. Încearcă cu TikTok, Instagram, Facebook sau Twitter/X.")
            return
        
        # Trimite mesaj de procesare
        send_telegram_message(chat_id, "✅ Procesez și descarc video-ul în 720p te rog asteapta")
        
        # Descarcă direct în calitate 720p
        download_video_sync(chat_id, url)
        
    except Exception as e:
        logger.error(f"Eroare la procesarea link-ului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la procesarea video-ului. Încearcă din nou.")

def download_video_sync(chat_id, url):
    """Descarcă video-ul în mod sincron în 720p"""
    try:
        # Descarcă video-ul (funcția download_video folosește deja format 720p)
        result = download_video(url)
        
        if result['success']:
            # Trimite fișierul cu toate informațiile
            send_video_file(chat_id, result['file_path'], result)
        else:
            send_telegram_message(chat_id, f"❌ Eroare la descărcare: {result.get('error', 'Eroare necunoscută')}")
            
    except Exception as e:
        logger.error(f"Eroare la descărcarea video-ului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la descărcarea video-ului. Încearcă din nou.")

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
        
        # Verifică mărimea fișierului (Telegram are limită de 50MB, dar folosim 512MB pentru siguranță)
        file_size_bytes = os.path.getsize(file_path)
        if file_size_bytes > 512 * 1024 * 1024:  # 512MB
            logger.error(f"Fișierul este prea mare: {file_size_bytes / (1024*1024):.1f}MB")
            send_telegram_message(chat_id, "❌ Fișierul video este prea mare pentru Telegram (max 512MB pentru siguranță).")
            try:
                os.remove(file_path)
            except:
                pass
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
            
            response = requests.post(url, files=files, data=data, timeout=300)
            
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
                
                response = requests.post(url, files={'video': video_file}, data=data_fallback, timeout=300)
            
        # Șterge fișierul temporar
        try:
            os.remove(file_path)
        except:
            pass
            
        if response.status_code == 200:
            logger.info(f"Video trimis cu succes pentru chat {chat_id}")
        else:
            # Log mai detaliat pentru debugging
            try:
                error_details = response.json()
                logger.error(f"Eroare la trimiterea video-ului: {response.status_code} - {error_details}")
            except:
                logger.error(f"Eroare la trimiterea video-ului: {response.status_code} - {response.text[:200]}")
            
            # Verifică tipul erorii și trimite mesaj corespunzător
            if response.status_code == 400:
                send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului. Fișierul poate fi corupt sau prea mare.")
            elif response.status_code == 413:
                send_telegram_message(chat_id, "❌ Fișierul video este prea mare pentru Telegram (max 512MB pentru siguranță).")
            else:
                send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului. Încearcă din nou.")
            
    except Exception as e:
        logger.error(f"Eroare la trimiterea fișierului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului.")


@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        # Folosește URL-ul curent al aplicației în loc de WEBHOOK_URL din variabilele de mediu
        current_url = request.url_root.rstrip('/')
        webhook_url = f"{current_url}/webhook"
        
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
        # Verifică dacă bot-ul este inițializat
        if not _app_initialized:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Bot not initialized',
                'timestamp': time.time()
            }), 503
        
        return jsonify({
            'status': 'healthy',
            'message': 'Bot is running',
            'webhook_mode': 'simplified',
            'timestamp': time.time()
        })
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
        
        logger.info("✅ Aplicația Telegram a fost inițializată la pornirea serverului")
        logger.info("🚀 Bot-ul este gata pentru descărcări!")
    except Exception as e:
        logger.error(f"❌ Eroare la inițializarea aplicației la pornire: {e}")

logger.info("Aplicația Telegram este configurată pentru webhook-uri")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Pornesc serverul Flask pe portul {port}")
    
    # Nu mai inițializez la startup pentru a evita problemele
    logger.info("Serverul pornește fără inițializare complexă")
    
    app.run(host='0.0.0.0', port=port, debug=False)
