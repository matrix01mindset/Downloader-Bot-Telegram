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

# Inițializare bot și application
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

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
- Videoclipuri max 15 minute
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
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

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
    
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

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
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /ping - verifică dacă botul funcționează
    """
    start_time = time.time()
    message = await update.message.reply_text("🏓 Pinging...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 2)
    
    await message.edit_text(f"🏓 Pong!\n⏱️ Timp răspuns: {ping_time}ms")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesează mesajele text (link-uri pentru descărcare)
    """
    message_text = update.message.text
    user_id = update.effective_user.id
    
    logger.info(f"Mesaj primit de la {user_id}: {message_text}")
    
    # Verifică dacă mesajul conține un URL suportat
    if is_supported_url(message_text):
        # Trimite mesaj de confirmare
        status_message = await update.message.reply_text(
            "🔄 Procesez videoclipul...\n⏳ Te rog să aștepți..."
        )
        
        try:
            # Descarcă videoclipul
            result = download_video(message_text)
            
            if result['success']:
                await status_message.edit_text("📤 Trimit videoclipul...")
                
                # Trimite videoclipul
                with open(result['file_path'], 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=f"✅ Videoclip descărcat cu succes!\n🎬 Titlu: {result.get('title', 'N/A')}",
                        supports_streaming=True
                    )
                
                # Șterge fișierul temporar
                try:
                    os.remove(result['file_path'])
                except:
                    pass
                    
                await status_message.delete()
                
            else:
                await status_message.edit_text(
                    f"❌ Eroare la descărcarea videoclipului:\n{result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Eroare la procesarea videoclipului: {e}")
            await status_message.edit_text(
                f"❌ Eroare neașteptată:\n{str(e)}"
            )
    else:
        # Mesaj pentru URL-uri nesuportate
        await update.message.reply_text(
            "❌ Link-ul nu este suportat sau nu este valid.\n\n"
            "🔗 Platforme suportate:\n"
            "• YouTube\n"
            "• TikTok\n"
            "• Instagram\n"
            "• Facebook\n"
            "• Twitter/X\n\n"
            "💡 Trimite un link valid pentru a descărca videoclipul."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionează callback-urile de la butoanele inline
    """
    query = update.callback_query
    await query.answer()
    
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
        
        await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
        
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
        
        await query.edit_message_text(platforms_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    elif query.data == 'settings':
        settings_text = """
⚙️ **Setări și limitări:**

📏 **Limitări de dimensiune:**
- Durată maximă: 15 minute
- Calitate maximă: 720p
- Dimensiune maximă: 50MB

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
        
        await query.edit_message_text(settings_text, parse_mode='Markdown', reply_markup=reply_markup)
        
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
        
        await query.edit_message_text(faq_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    elif query.data == 'ping_again':
        start_time = time.time()
        await query.edit_message_text("🏓 Pinging...")
        end_time = time.time()
        ping_time = round((end_time - start_time) * 1000, 2)
        
        keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏓 Pong!\n⏱️ Timp răspuns: {ping_time}ms",
            reply_markup=reply_markup
        )
        
    elif query.data == 'wakeup_server':
        await query.edit_message_text("🌅 Server trezit! Botul este activ și gata de utilizare.")
        
        keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await asyncio.sleep(2)
        await query.edit_message_text(
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
        
        await query.edit_message_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

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

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Asigură că aplicația este inițializată
        ensure_app_initialized()
        
        update = Update.de_json(request.get_json(force=True), bot)
        
        # Verifică dacă există deja un loop asyncio în thread-ul curent
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            # Creează un nou loop doar dacă nu există unul valid
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Procesează update-ul în mod sigur
        try:
            if loop.is_running():
                # Dacă loop-ul rulează deja, folosește create_task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, application.process_update(update))
                    future.result(timeout=30)
            else:
                # Dacă loop-ul nu rulează, folosește run_until_complete
                loop.run_until_complete(application.process_update(update))
        except Exception as process_error:
            logger.error(f"Eroare la procesarea update-ului: {process_error}")
            raise
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Eroare în webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        # Pentru versiunea 20.8, folosim loop manual
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(bot.set_webhook(url=webhook_url))
        finally:
            loop.close()
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Webhook setat la: {webhook_url}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Nu s-a putut seta webhook-ul'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Eroare la setarea webhook-ului: {str(e)}'
        })

@app.route('/health', methods=['GET'])
def health_check():
    try:
        import time
        return jsonify({
            'status': 'healthy',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'server': 'online'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
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
            # Folosește asyncio.run pentru inițializare
            import asyncio
            
            async def init_all():
                # Inițializează bot-ul
                await bot.initialize()
                # Inițializează aplicația
                await application.initialize()
            
            asyncio.run(init_all())
            _app_initialized = True
            logger.info("✅ Bot-ul și aplicația Telegram au fost inițializate cu succes în contextul Flask")
        except Exception as e:
            logger.error(f"❌ Eroare la inițializarea bot-ului și aplicației în contextul Flask: {e}")
            raise

# Aplicația este deja inițializată mai sus
logger.info("Aplicația Telegram este configurată pentru webhook-uri")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Pornesc serverul Flask pe portul {port}")
    app.run(host='0.0.0.0', port=port, debug=False)