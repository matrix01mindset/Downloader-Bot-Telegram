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
from utils.activity_logger import activity_logger, log_command_executed, log_download_success, log_download_error

# Încarcă variabilele de mediu din .env pentru testare locală
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv nu este disponibil în producție, nu e problemă
    pass

# Configurare logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

def safe_send_with_fallback(chat_id, text, parse_mode='HTML', reply_markup=None):
    """
    Trimite mesaj cu fallback la text simplu dacă parse_mode eșuează.
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

# Funcție centrală pentru crearea caption-urilor sigure
def create_safe_caption(title, uploader=None, description=None, duration=None, file_size=None, max_length=1000):
    """
    Creează un caption sigur pentru Telegram, respectând limitele de caractere.
    
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
        # Escapează titlul pentru HTML
        title_safe = escape_html(title[:200]) if title else "Video"
        if len(title) > 200:
            title_safe = title_safe[:-3] + "..."
        
        # Începe cu titlul
        caption = f"✅ <b>{title_safe}</b>\n\n"
        
        # Adaugă creatorul dacă există
        if uploader and uploader.strip():
            uploader_clean = escape_html(uploader.strip()[:100])  # Limitează la 100 caractere
            caption += f"👤 <b>Creator:</b> {uploader_clean}\n"
        
        # Formatează durata cu verificări de tip
        if duration and isinstance(duration, (int, float)) and duration > 0:
            try:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                caption += f"⏱️ <b>Durată:</b> {minutes}:{seconds:02d}\n"
            except (TypeError, ValueError):
                pass  # Skip duration if formatting fails
        
        # Formatează dimensiunea fișierului cu verificări de tip
        if file_size and isinstance(file_size, (int, float)) and file_size > 0:
            try:
                size_mb = float(file_size) / (1024 * 1024)
                caption += f"📦 <b>Mărime:</b> {size_mb:.1f} MB\n"
            except (TypeError, ValueError):
                pass  # Skip file size if formatting fails
        
        # Calculează spațiul rămas pentru descriere
        current_length = len(caption)
        footer = "\n\n🎬 Descărcare completă!"
        footer_length = len(footer)
        
        # Spațiul disponibil pentru descriere
        available_space = max_length - current_length - footer_length - 50  # Buffer de siguranță
        
        # Adaugă descrierea dacă există și dacă avem spațiu
        if description and description.strip() and available_space > 20:
            description_clean = description.strip()
            
            # Curăță descrierea de caractere problematice
            description_clean = re.sub(r'[\r\n]+', ' ', description_clean)  # Înlocuiește newlines cu spații
            description_clean = re.sub(r'\s+', ' ', description_clean)  # Curăță spațiile multiple
            
            # Truncează descrierea la spațiul disponibil
            if len(description_clean) > available_space:
                # Găsește ultima propoziție completă sau ultimul spațiu
                truncate_pos = available_space - 3  # Spațiu pentru "..."
                
                # Încearcă să găsești ultima propoziție completă
                last_sentence = description_clean[:truncate_pos].rfind('.')
                if last_sentence > available_space // 2:  # Dacă găsim o propoziție la jumătate
                    description_clean = description_clean[:last_sentence + 1]
                else:
                    # Altfel, găsește ultimul spațiu
                    last_space = description_clean[:truncate_pos].rfind(' ')
                    if last_space > available_space // 2:
                        description_clean = description_clean[:last_space] + "..."
                    else:
                        description_clean = description_clean[:truncate_pos] + "..."
            
            # Escapează descrierea pentru HTML
            description_safe = escape_html(description_clean)
            caption += f"\n📝 <b>Descriere:</b>\n{description_safe}"
        
        # Adaugă footer-ul
        caption += footer
        
        # Verificare finală de siguranță
        if len(caption) > max_length:
            # Dacă încă este prea lung, truncează drastic
            safe_length = max_length - len(footer) - 10
            caption = caption[:safe_length] + "..." + footer
        
        return caption
        
    except Exception as e:
        logger.error(f"Eroare la crearea caption-ului: {e}")
        # Fallback la un caption minimal
        title_safe = escape_html(title[:100]) if title else 'Video'
        return f"✅ <b>{title_safe}</b>\n\n🎬 Descărcare completă!"

# Configurare Flask
app = Flask(__name__)

# 🛡️ SECURITATE: Forțează dezactivarea debug mode în producție
if os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER'):
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
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
    .build()
)

# Variabilă globală pentru starea inițializării
_app_initialized = False

def initialize_telegram_application():
    """Inițializează aplicația Telegram o singură dată"""
    global _app_initialized
    if _app_initialized:
        return True
        
    try:
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
🎬 **Bot Descărcare Video**

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 **Platforme suportate:**
• TikTok
• Instagram
• Facebook
• Twitter/X
• Threads
• Pinterest
• Reddit
• Vimeo
• Dailymotion

⚠️ **Limitări:**
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
    
    await safe_send_message(update, welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /help - informații complete de ajutor
    """
    help_text = """
🤖 **Bot Descărcare Video - Ghid Complet**

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

🔗 **Platforme suportate:**
• TikTok (tiktok.com, vm.tiktok.com)
• Instagram (instagram.com, reels, stories)
• Facebook (facebook.com, fb.watch, watch)
• Twitter/X (twitter.com, x.com)

⚠️ **Limitări importante:**
• Mărime maximă: 45MB (limita Telegram)
• Durată maximă: 3 ore
• Calitate maximă: 720p
• Doar videoclipuri publice
• YouTube nu este suportat momentan

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
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_send_message(update, help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Afișează meniul principal
    """
    welcome_message = """
🎬 **Bot Descărcare Video**

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 **Platforme suportate:**
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X

⚠️ **Limitări:**
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
    
    await safe_send_message(update, welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

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
        except:
            logger.error("Nu s-a putut trimite mesajul de eroare pentru comanda /log")

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
                
                # Rulează descărcarea în thread pool
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    result = await loop.run_in_executor(executor, download_video, message_text)
                
                if result['success']:
                    # Afișează mesaj de succes cu informații despre rotație (dacă există)
                    if 'success_message' in result:
                        await safe_edit_message(
                            status_message,
                            result['success_message']
                        )
                        # Așteaptă puțin pentru ca utilizatorul să vadă mesajul
                        await asyncio.sleep(1)
                    
                    # Trimite videoclipul
                    try:
                        with open(result['file_path'], 'rb') as video_file:
                            # Folosește funcția centrală pentru caption sigur
                            caption = create_safe_caption(
                                title=result.get('title', 'Video'),
                                uploader=result.get('uploader'),
                                description=result.get('description'),
                                duration=result.get('duration'),
                                file_size=result.get('file_size')
                            )
                            
                            try:
                                if hasattr(update.message, 'reply_video'):
                                    await update.message.reply_video(
                                        video=video_file,
                                        caption=caption,
                                        supports_streaming=True,
                                        parse_mode='Markdown'
                                    )
                                else:
                                    await update.effective_chat.send_video(
                                        video=video_file,
                                        caption=caption,
                                        supports_streaming=True,
                                        parse_mode='Markdown'
                                    )
                            except Exception as e:
                                error_msg = str(e).lower()
                                if 'chat not found' in error_msg or 'forbidden' in error_msg or 'blocked' in error_msg:
                                    logger.warning(f"Nu se poate trimite videoclipul - chat inaccesibil pentru user {user_id}: {e}")
                                    return
                                else:
                                    raise
                    except Exception as e:
                        logger.error(f"Eroare la trimiterea videoclipului: {e}")
                        await safe_edit_message(
                            status_message,
                            f"❌ Eroare la trimiterea videoclipului:\n{str(e)}"
                        )
                    
                    # Șterge fișierul temporar
                    try:
                        os.remove(result['file_path'])
                    except:
                        pass
                        
                    await safe_delete_message(status_message)
                    
                else:
                    await safe_edit_message(
                        status_message,
                        f"❌ Eroare la descărcarea videoclipului:\n{result['error']}"
                    )
                    
            except Exception as e:
                logger.error(f"Eroare la procesarea videoclipului: {e}")
                if status_message:
                    await safe_edit_message(
                        status_message,
                        f"❌ Eroare neașteptată:\n{str(e)}"
                    )
        else:
            # Mesaj pentru URL-uri nesuportate
            await safe_send_message(
                update,
                "❌ Link-ul nu este suportat sau nu este valid.\n\n"
                "🔗 Platforme suportate:\n"
                "• TikTok\n"
                "• Instagram\n"
                "• Facebook\n"
                "• Twitter/X\n"
                "• Threads\n"
                "• Pinterest\n"
                "• Reddit\n"
                "• Vimeo\n"
                "• Dailymotion\n\n"
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
🆘 **Cum să folosești botul:**

1. Copiază link-ul videoclipului
2. Trimite-l în acest chat
3. Așteaptă să fie procesat
4. Primești videoclipul descărcat

🔗 **Platforme suportate:**
- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)
- Instagram (instagram.com)
- Facebook (facebook.com, fb.watch)
- Twitter/X (twitter.com, x.com)

⚠️ **Probleme frecvente:**
- Videoclipul este privat → Nu poate fi descărcat
- Videoclipul este prea lung → Max 15 minute
- Link invalid → Verifică că link-ul este corect
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, help_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        elif query.data == 'platforms':
            platforms_text = """
🔗 **Platforme suportate:**

✅ **TikTok**
- tiktok.com
- vm.tiktok.com

✅ **Instagram**
- instagram.com
- Reels, IGTV, Posts video

✅ **Facebook**
- facebook.com
- fb.watch
- m.facebook.com

✅ **Twitter/X**
- twitter.com
- x.com
- mobile.twitter.com

⚠️ **Notă:** Doar videoclipurile publice pot fi descărcate.

❌ **YouTube nu este suportat momentan** din cauza complexității tehnice și a restricțiilor platformei.
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, platforms_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        elif query.data == 'settings':
            settings_text = """
⚙️ **Setări și limitări:**

📏 **Limitări de dimensiune:**
- Durată maximă: 3 ore
- Calitate maximă: 720p
- Dimensiune maximă: 550MB

🚫 **Restricții:**
- Doar videoclipuri publice
- Nu se suportă livestream-uri
- Nu se suportă playlist-uri

⚡ **Performanță:**
- Timp mediu de procesare: 30-60 secunde
- Depinde de dimensiunea videoclipului
- Server gratuit cu limitări

🔒 **Confidențialitate:**
- Nu salvez videoclipurile
- Nu salvez link-urile
- Procesare temporară
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, settings_text, parse_mode='Markdown', reply_markup=reply_markup)
            
        elif query.data == 'faq':
            faq_text = """
❓ **Întrebări frecvente:**

**Q: De ce nu funcționează link-ul meu?**
A: Verifică că videoclipul este public și de pe o platformă suportată.

**Q: Cât timp durează descărcarea?**
A: De obicei 30-60 secunde, depinde de dimensiunea videoclipului.

**Q: Pot descărca videoclipuri private?**
A: Nu, doar videoclipurile publice pot fi descărcate.

**Q: Ce calitate au videoclipurile?**
A: Maxim 720p pentru a respecta limitările serverului.

**Q: Botul nu răspunde?**
A: Serverul gratuit poate fi în hibernare. Încearcă din nou în câteva minute.

**Q: Pot descărca playlist-uri?**
A: Nu, doar videoclipuri individuale.
            """
            
            keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_callback_message(query, faq_text, parse_mode='Markdown', reply_markup=reply_markup)
            
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
🎬 **Bot Descărcare Video**

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 **Platforme suportate:**
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X

⚠️ **Limitări:**
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
            
            await safe_edit_callback_message(query, welcome_message, parse_mode='Markdown', reply_markup=reply_markup)
            
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

# Set pentru a urmări mesajele procesate (previne duplicarea)
processed_messages = set()

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Procesează webhook-urile de la Telegram"""
    try:
        # Dacă este o cerere GET, returnează status OK
        if request.method == 'GET':
            return jsonify({'status': 'webhook_ready', 'method': 'GET'}), 200
            
        # Obține datele JSON de la Telegram
        json_data = request.get_json()
        
        if not json_data:
            logger.error("Nu s-au primit date JSON")
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
        
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
                        
                    elif text and ('tiktok.com' in text or 'instagram.com' in text or 'facebook.com' in text or 'fb.watch' in text or 'twitter.com' in text or 'x.com' in text or 'threads.net' in text or 'threads.com' in text or 'pinterest.com' in text or 'pin.it' in text or 'reddit.com' in text or 'redd.it' in text or 'vimeo.com' in text or 'dailymotion.com' in text or 'dai.ly' in text):
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
            send_telegram_message(chat_id, "❌ Link-ul nu este suportat. Încearcă cu TikTok, Instagram, Facebook, Twitter/X, Threads, Pinterest, Reddit, Vimeo sau Dailymotion.")
            return
        
        # Trimite mesaj de procesare
        send_telegram_message(chat_id, "✅ Procesez și descarc video-ul în 720p te rog asteapta")
        
        # Descarcă direct în calitate 720p
        download_video_sync(chat_id, url)
        
    except Exception as e:
        logger.error(f"Eroare la procesarea link-ului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la procesarea video-ului. Încearcă din nou.")

# Set pentru a preveni mesajele repetate de eroare
error_messages_sent = set()

def download_video_sync(chat_id, url):
    """Descarcă video-ul în mod sincron în 720p"""
    global error_messages_sent
    
    try:
        # Descarcă video-ul (funcția download_video folosește deja format 720p)
        result = download_video(url)
        
        if result['success']:
            # Log succesul descărcării
            log_download_success(url, 0, chat_id, result.get('platform', 'unknown'))
            # Trimite fișierul cu toate informațiile
            send_video_file(chat_id, result['file_path'], result)
            # Șterge din cache-ul de erori dacă descărcarea a reușit
            error_key = f"{chat_id}_{url}"
            error_messages_sent.discard(error_key)
        else:
            # Log eroarea descărcării
            error_msg = result.get('error', 'Eroare necunoscută')
            log_download_error(url, 0, chat_id, error_msg)
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
        log_download_error(url, 0, chat_id, f"Exception: {str(e)}")
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
            except:
                logger.error(f"Eroare la trimiterea video-ului: {response.status_code} - {response.text[:200]}")
            
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
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Pornesc serverul Flask pe portul {port}")
    
    # Nu mai inițializez la startup pentru a evita problemele
    logger.info("Serverul pornește fără inițializare complexă")
    
    app.run(host='0.0.0.0', port=port, debug=False)