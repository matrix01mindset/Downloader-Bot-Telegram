import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from downloader import download_video, is_supported_url
import tempfile
import time
import threading

# Încarcă variabilele de mediu din .env pentru testare locală
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv nu este instalat, continuă fără el
    pass

# Configurare logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

# Inițializare bot și application cu configurații optimizate pentru producție
# Configurare bot cu connection pool și timeout-uri reduse pentru Render
bot = Bot(TOKEN)
application = (
    Application.builder()
    .token(TOKEN)
    .connection_pool_size(50)  # Redus pentru mediul de producție
    .pool_timeout(20.0)  # Timeout redus
    .get_updates_connection_pool_size(5)  # Redus pentru webhook mode
    .get_updates_pool_timeout(20.0)  # Timeout redus
    .read_timeout(15.0)  # Timeout redus pentru citire
    .write_timeout(15.0)  # Timeout redus pentru scriere
    .connect_timeout(10.0)  # Timeout redus pentru conectare
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
    Comandă /help - informații de ajutor
    """
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
                "🔄 Procesez videoclipul...\n⏳ Te rog să aștepți..."
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
                    await safe_edit_message(status_message, "📤 Trimit videoclipul...")
                    
                    # Trimite videoclipul
                    try:
                        with open(result['file_path'], 'rb') as video_file:
                            # Construiește caption-ul cu informații detaliate
                            caption = f"✅ Videoclip descărcat cu succes!\n\n"
                            caption += f"🎬 **Titlu:** {result.get('title', 'N/A')}\n"
                            
                            if result.get('uploader'):
                                caption += f"👤 **Creator:** {result.get('uploader')}\n"
                            
                            if result.get('duration'):
                                duration = result.get('duration')
                                minutes = int(duration // 60)
                                seconds = int(duration % 60)
                                caption += f"⏱️ **Durată:** {minutes}:{seconds:02d}\n"
                            
                            if result.get('file_size') and isinstance(result.get('file_size'), (int, float)):
                                size_mb = result.get('file_size') / (1024 * 1024)
                                caption += f"📦 **Mărime:** {size_mb:.1f} MB\n"
                            
                            # Adaugă descrierea/hashtag-urile dacă există
                            description = result.get('description', '')
                            if description and len(description.strip()) > 0:
                                caption += f"\n📝 **Descriere/Tags:**\n{description}"
                            
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
                "• YouTube\n"
                "• TikTok\n"
                "• Instagram\n"
                "• Facebook\n"
                "• Twitter/X\n\n"
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

✅ **YouTube**
- youtube.com
- youtu.be
- m.youtube.com

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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook complet sincron pentru a evita problemele cu event loop-urile"""
    try:
        # Asigură că aplicația este inițializată
        ensure_app_initialized()
        
        # Obține datele JSON
        json_data = request.get_json(force=True)
        if not json_data:
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
        
        # Creează update-ul
        update = Update.de_json(json_data, bot)
        if not update:
            return jsonify({'status': 'error', 'message': 'Invalid update'}), 400
        
        # Procesează update-ul complet sincron
        def process_update_sync():
            """Procesează update-ul fără asyncio"""
            try:
                # Procesează manual diferite tipuri de update-uri
                if update.message:
                    process_message_sync(update)
                elif update.callback_query:
                    process_callback_sync(update)
                else:
                    logger.info("Update ignorat - tip nesuportat")
            except Exception as e:
                logger.error(f"Eroare la procesarea sincronă: {e}")
        
        # Rulează procesarea în background și returnează imediat
        import threading
        thread = threading.Thread(target=process_update_sync, daemon=True)
        thread.start()
        
        # Returnează imediat success pentru a evita timeout-urile
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Eroare în webhook: {e}")
        return jsonify({'status': 'error', 'message': 'Webhook error'}), 500

def send_telegram_message(chat_id, text, reply_markup=None):
    """Trimite mesaj prin API-ul Telegram folosind requests"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Eroare la trimiterea mesajului: {e}")
        return False

def process_message_sync(update):
    """Procesează mesajele în mod sincron"""
    try:
        message = update.message
        # Accesează chat_id în mod sigur
        if hasattr(message, 'chat_id'):
            chat_id = message.chat_id
        elif hasattr(message, 'chat') and hasattr(message.chat, 'id'):
            chat_id = message.chat.id
        else:
            logger.error("Nu se poate obține chat_id din mesaj")
            return
            
        text = message.text if hasattr(message, 'text') else None
        
        # Verifică dacă mesajul are text
        if not text:
            return
        
        if text == '/start':
            welcome_text = (
                "🎬 <b>Bun venit la Video Downloader Bot!</b>\n\n"
                "📱 Trimite-mi un link de pe:\n"
                "• YouTube\n"
                "• TikTok\n"
                "• Instagram\n"
                "• Facebook\n\n"
                "🔗 Doar copiază și lipește link-ul aici!"
            )
            send_telegram_message(chat_id, welcome_text)
            
        elif text == '/help':
            help_text = (
                "📋 <b>Cum să folosești bot-ul:</b>\n\n"
                "1️⃣ Copiază link-ul video\n"
                "2️⃣ Lipește-l în chat\n"
                "3️⃣ Alege calitatea dorită\n"
                "4️⃣ Descarcă video-ul\n\n"
                "🎯 <b>Platforme suportate:</b>\n"
                "• YouTube, TikTok, Instagram, Facebook\n\n"
                "❓ Pentru ajutor: /help"
            )
            send_telegram_message(chat_id, help_text)
            
        elif text and ('youtube.com' in text or 'youtu.be' in text or 'tiktok.com' in text or 'instagram.com' in text or 'facebook.com' in text):
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
            send_telegram_message(chat_id, "❌ Link-ul nu este suportat. Încearcă cu YouTube, TikTok, Instagram sau Facebook.")
            return
        
        # Trimite mesaj de procesare
        send_telegram_message(chat_id, "🔄 Procesez și descarc video-ul în 720p... Te rog așteaptă.")
        
        # Descarcă direct în calitate 720p
        download_video_sync(chat_id, url)
        
    except Exception as e:
        logger.error(f"Eroare la procesarea link-ului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la procesarea video-ului. Încearcă din nou.")

def download_video_sync(chat_id, url):
    """Descarcă video-ul în mod sincron în 720p"""
    try:
        send_telegram_message(chat_id, "⬇️ Încep descărcarea în 720p... Poate dura câteva minute.")
        
        # Descarcă video-ul (funcția download_video folosește deja format 720p)
        result = download_video(url)
        
        if result['success']:
            # Trimite fișierul
            send_video_file(chat_id, result['file_path'], result.get('title', 'Video'))
        else:
            send_telegram_message(chat_id, f"❌ Eroare la descărcare: {result.get('error', 'Eroare necunoscută')}")
            
    except Exception as e:
        logger.error(f"Eroare la descărcarea video-ului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la descărcarea video-ului. Încearcă din nou.")

def send_video_file(chat_id, file_path, title):
    """Trimite fișierul video prin Telegram"""
    try:
        import requests
        import os
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
        
        with open(file_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {
                'chat_id': chat_id,
                'caption': f"🎬 {title}\n\n✅ Descărcare completă!"
            }
            
            response = requests.post(url, files=files, data=data, timeout=300)
            
        # Șterge fișierul temporar
        try:
            os.remove(file_path)
        except:
            pass
            
        if response.status_code == 200:
            logger.info(f"Video trimis cu succes pentru chat {chat_id}")
        else:
            logger.error(f"Eroare la trimiterea video-ului: {response.status_code}")
            send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului. Fișierul poate fi prea mare.")
            
    except Exception as e:
        logger.error(f"Eroare la trimiterea fișierului: {e}")
        send_telegram_message(chat_id, "❌ Eroare la trimiterea video-ului.")


@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        # Verifică dacă WEBHOOK_URL este setat
        if not WEBHOOK_URL:
            return jsonify({
                'status': 'error',
                'message': 'WEBHOOK_URL nu este setat în variabilele de mediu'
            }), 400
        
        webhook_url = f"{WEBHOOK_URL}/webhook"
        
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

# Funcție pentru inițializarea în contextul Flask
def ensure_app_initialized():
    """Asigură că aplicația și bot-ul sunt inițializate în contextul Flask"""
    global _app_initialized
    if not _app_initialized:
        try:
            import asyncio
            import threading
            import concurrent.futures
            
            def run_init():
                """Rulează inițializarea într-un thread separat cu propriul event loop"""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async def init_all():
                        # Inițializează bot-ul
                        await bot.initialize()
                        # Inițializează aplicația
                        await application.initialize()
                    
                    loop.run_until_complete(init_all())
                finally:
                    loop.close()
            
            # Rulează inițializarea într-un thread separat
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_init)
                future.result(timeout=30)
            
            _app_initialized = True
            logger.info("✅ Bot-ul și aplicația Telegram au fost inițializate cu succes în contextul Flask")
        except Exception as e:
            logger.error(f"❌ Eroare la inițializarea bot-ului și aplicației în contextul Flask: {e}")
            raise

# Inițializează aplicația la pornirea serverului
def initialize_on_startup():
    """Inițializează aplicația la pornirea serverului Flask"""
    try:
        ensure_app_initialized()
        logger.info("✅ Aplicația Telegram a fost inițializată la pornirea serverului")
    except Exception as e:
        logger.error(f"❌ Eroare la inițializarea aplicației la pornire: {e}")

logger.info("Aplicația Telegram este configurată pentru webhook-uri")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Pornesc serverul Flask pe portul {port}")
    
    # Inițializează aplicația înainte de a porni serverul
    initialize_on_startup()
    
    app.run(host='0.0.0.0', port=port, debug=False)