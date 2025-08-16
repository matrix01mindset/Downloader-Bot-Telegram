import os
from utils.rate_limiter import rate_limiter
import sys
import logging
import re
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from downloader import download_video, is_supported_url

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

# Funcție pentru crearea caption-urilor sigure (versiunea pentru bot.py)
def create_safe_caption_bot(title, uploader=None, description=None, max_length=1000):
    """
    Creează un caption sigur pentru Telegram în bot.py, respectând limitele de caractere.
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
            caption += f"👤 <b>De la:</b> {uploader_clean}\n"
        
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

# Token-ul botului (va fi setat prin variabilă de mediu)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu!")
    print("❌ EROARE: TELEGRAM_BOT_TOKEN nu este setat!")
    print("💡 Setează token-ul în fișierul .env sau ca variabilă de mediu")
    sys.exit(1)

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
        [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /help - informații de ajutor
    """
    help_text = """🤖 **Telegram Video Downloader Bot**

📱 **Platforme Suportate:**
• TikTok
• Instagram (Reels, IGTV, Stories)
• Facebook (Videos)
• Twitter/X (Videos)
• Threads (Videos)
• Pinterest (Videos)
• Reddit (Videos)
• Vimeo
• Dailymotion

❌ **Nu este suportat:** YouTube (din cauza limitărilor API)

📋 **Cum să folosești:**
1. Trimite-mi un link de la una din platformele suportate
2. Așteptă să procesez videoclipul
3. Descarcă videoclipul direct în Telegram

⚠️ **Limite:**
• Mărimea maximă: 45MB
• Durată maximă: 10 minute
• Rate limit: 5 cereri per minut

🔧 **Comenzi:**
/start - Pornește botul
/help - Afișează acest mesaj
/menu - Meniul principal"""
    
    help_text += """🆘 <b>Cum să folosești botul:</b>

1. Copiază link-ul videoclipului
2. Trimite-l în acest chat
3. Așteaptă să fie procesat
4. Primești videoclipul descărcat

🔗 <b>Platforme suportate:</b>
- TikTok (tiktok.com, vm.tiktok.com)
- Instagram (instagram.com)
- Facebook (facebook.com, fb.watch, fb.me)
- Twitter/X (twitter.com, x.com)
- Threads (threads.net, threads.com)
- Pinterest (pinterest.com, pin.it)
- Reddit (reddit.com, redd.it, v.redd.it)
- Vimeo (vimeo.com, player.vimeo.com)
- Dailymotion (dailymotion.com, dai.ly)

⚠️ <b>Probleme frecvente:</b>
- Videoclipul este privat → Nu poate fi descărcat
- Videoclipul este prea lung → Max 3 ore
- Videoclipul este prea mare → Max 550MB
- Link invalid → Verifică că link-ul este corect
        """
    
    keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=reply_markup)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comandă /menu - afișează meniul principal
    """
    welcome_message = """
🎬 <b>Bot Descărcare Video</b>

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 <b>Platforme suportate:</b>
• TikTok  
• Instagram
• Facebook
• Twitter/X

⚠️ <b>Notă:</b> YouTube nu este suportat momentan din cauza complexității tehnice.

⚠️ <b>Limitări:</b>
- Videoclipuri max 15 minute
- Calitate max 720p
- Doar videoclipuri publice
    """
    
    keyboard = [
        [InlineKeyboardButton("📖 Cum să folosesc botul", callback_data='help')],
        [InlineKeyboardButton("🔗 Platforme suportate", callback_data='platforms')],
        [InlineKeyboardButton("⚙️ Setări și limitări", callback_data='settings')],
        [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Verifică rate limiting
    user_id = str(update.effective_user.id)
    if not rate_limiter.is_allowed(user_id):
        remaining_time = rate_limiter.get_reset_time(user_id)
        await update.message.reply_text(
            f"⏳ Prea multe cereri! Încearcă din nou în {int(remaining_time)} secunde.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Gestionează mesajele cu link-uri video
    url = update.message.text.strip()
    
    # Verifică dacă este un URL valid
    if not url.startswith(('http://', 'https://')):
        keyboard = [[InlineKeyboardButton("📖 Vezi cum să folosești botul", callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Te rog să trimiți un link valid (care începe cu http:// sau https://)\n\n"
            "💡 Trimite un link de pe TikTok, Instagram, Facebook, Twitter/X, Threads, Pinterest, Reddit, Vimeo sau Dailymotion",
            reply_markup=reply_markup
        )
        return
    
    # Verifică dacă URL-ul este suportat
    if not is_supported_url(url):
        keyboard = [[InlineKeyboardButton("🔗 Vezi platformele suportate", callback_data='platforms')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Această platformă nu este suportată.\n\n"
            "Platforme suportate: TikTok, Instagram, Facebook, Twitter/X, Threads, Pinterest, Reddit, Vimeo, Dailymotion",
            reply_markup=reply_markup
        )
        return
    
    # Afișează confirmarea cu butoane
    confirmation_text = f"🔗 <b>Link detectat:</b>\n`{url}`\n\n📥 Vrei să descarc acest videoclip?"
    
    keyboard = [
        [InlineKeyboardButton("✅ Da, descarcă!", callback_data=f'download_{url}')],
        [InlineKeyboardButton("❌ Anulează", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(confirmation_text, parse_mode='HTML', reply_markup=reply_markup)

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """
    Procesează descărcarea videoclipului
    """
    query = update.callback_query
    
    # Trimite mesaj de procesare
    processing_message = await query.edit_message_text(
        "✅ Procesez și descarc video-ul în 720p te rog asteapta"
    )
    
    try:
        # Descarcă videoclipul
        result = download_video(url)
        
        if not result['success']:
            raise Exception(result['error'])
        
        filepath = result['file_path']
        title = result.get('title', 'Video')
        description = result.get('description', '')
        uploader = result.get('uploader', '')
        
        if not filepath or not os.path.exists(filepath):
            raise Exception("Fișierul nu a fost găsit după descărcare")
        
        # Verifică mărimea fișierului (Telegram Bot API are limită strictă de 50MB)
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size > 45 * 1024 * 1024:  # 45MB (buffer pentru limita Telegram de 50MB)
            raise Exception(f"Fișierul este prea mare ({file_size_mb:.1f}MB). Limita Telegram: 50MB pentru bot-uri.")
        
        # Creează caption sigur cu retry logic
        caption_strategies = [
            # Strategia 1: Caption complet
            lambda: create_safe_caption_bot(title, uploader, description, 1000),
            # Strategia 2: Fără descriere
            lambda: create_safe_caption_bot(title, uploader, None, 800),
            # Strategia 3: Doar titlu și creator
            lambda: create_safe_caption_bot(title, uploader, None, 500),
            # Strategia 4: Doar titlu
            lambda: create_safe_caption_bot(title, None, None, 200),
            # Strategia 5: Caption minimal
            lambda: f"✅ <b>{escape_html(str(title)[:50]) if title else 'Video'}</b>\n\n🎬 Descărcare completă!"
        ]
        
        # Încearcă să trimită videoclipul cu retry pentru caption-uri prea lungi
        video_sent = False
        for attempt in range(3):
            try:
                caption_strategy = caption_strategies[min(attempt, len(caption_strategies) - 1)]
                caption = caption_strategy()
                
                with open(filepath, 'rb') as video_file:
                    await query.message.reply_video(
                        video=video_file,
                        caption=caption,
                        parse_mode='HTML'
                    )
                video_sent = True
                break
                
            except Exception as video_error:
                if "caption too long" in str(video_error).lower() or "message too long" in str(video_error).lower():
                    logger.warning(f"Caption prea lung la încercarea {attempt + 1}, încerc cu caption mai scurt")
                    continue
                else:
                    raise video_error
        
        if not video_sent:
            raise Exception("Nu s-a putut trimite videoclipul după multiple încercări")
        
        # Trimite mesaj cu opțiuni după descărcare
        keyboard = [
            [InlineKeyboardButton("📥 Descarcă alt videoclip", callback_data='new_download')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ <b>Descărcare completă!</b>\n\nVideoclipul a fost trimis cu succes.\nCe vrei să faci acum?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        # Șterge fișierul temporar
        try:
            os.remove(filepath)
        except Exception as e:
            logger.debug(f"Nu s-a putut șterge fișierul temporar {filepath}: {e}")
            
        # Șterge mesajul de procesare
        try:
            await processing_message.delete()
        except Exception as e:
            logger.debug(f"Nu s-a putut șterge mesajul de procesare: {e}")
            
    except Exception as e:
        error_message = f"❌ Eroare: {str(e)}"
        
        # Mesaje de eroare mai prietenoase
        if "private" in str(e).lower():
            error_message = "❌ Videoclipul este privat și nu poate fi descărcat."
        elif "not available" in str(e).lower():
            error_message = "❌ Videoclipul nu este disponibil în regiunea ta."
        elif "prea lung" in str(e):
            error_message = "❌ Videoclipul este prea lung (maximum 3 ore)."
        elif "prea mare" in str(e):
            error_message = (
                "❌ **Fișierul este prea mare pentru Telegram**\n\n"
                "⚠️ **Limita Telegram:** 50MB (pentru bot-uri)\n\n"
                "💡 **Soluții:**\n"
                "• Încearcă un clip mai scurt\n"
                "• Folosește o calitate mai mică\n"
                "• Împarte clipul în segmente mai mici"
            )
        
        # Adaugă butoane pentru a încerca din nou sau a merge la meniu
        keyboard = [
            [InlineKeyboardButton("🔄 Încearcă din nou", callback_data=f'download_{url}')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(error_message, reply_markup=reply_markup)
        
        # Șterge mesajul de procesare
        try:
            await processing_message.delete()
        except Exception as e:
            logger.debug(f"Nu s-a putut șterge mesajul de procesare în cazul de eroare: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionează apăsările pe butoanele inline
    """
    query = update.callback_query
    await query.answer()
    
    # Gestionează descărcarea
    if query.data.startswith('download_'):
        url = query.data.replace('download_', '')
        await process_download(update, context, url)
        return
    
    # Gestionează cererea pentru descărcare nouă
    elif query.data == 'new_download':
        await query.edit_message_text(
<<<<<<< HEAD
            "📥 **Gata pentru o nouă descărcare!**\n\n"
            "Trimite-mi un link de pe TikTok, Instagram, Facebook, Twitter/X, Threads, Pinterest, Reddit, Vimeo sau Dailymotion"
=======
            "📥 <b>Gata pentru o nouă descărcare!</b>\n\n"
            "Trimite-mi un link de pe TikTok, Instagram, Facebook sau Twitter/X"
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
        )
        return
    
    # Gestionează anularea
    elif query.data == 'cancel':
        keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ Descărcarea a fost anulată.\n\n💡 Trimite un alt link când ești gata!",
            reply_markup=reply_markup
        )
        return
    
    elif query.data == 'help':
<<<<<<< HEAD
        help_text = """🤖 **Telegram Video Downloader Bot**

📱 **Platforme Suportate:**
• TikTok
• Instagram (Reels, IGTV, Stories)
• Facebook (Videos)
• Twitter/X (Videos)
• Threads (Videos)
• Pinterest (Videos)
• Reddit (Videos)
• Vimeo
• Dailymotion

❌ **Nu este suportat:** YouTube (din cauza limitărilor API)

📋 **Cum să folosești:**
1. Trimite-mi un link de la una din platformele suportate
2. Așteptă să procesez videoclipul
3. Descarcă videoclipul direct în Telegram

⚠️ **Limite:**
• Mărimea maximă: 45MB
• Durată maximă: 10 minute
• Rate limit: 5 cereri per minut

🔧 **Comenzi:**
/start - Pornește botul
/help - Afișează acest mesaj
/menu - Meniul principal"""
    
        help_text += """🆘 **Cum să folosești botul:**
=======
        help_text = """
🆘 <b>Cum să folosești botul:</b>
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e

1. 📋 Copiază link-ul videoclipului
2. 📤 Trimite-l în acest chat
3. ⏳ Așteaptă să fie procesat
4. 📥 Primești videoclipul descărcat

💡 <b>Sfaturi:</b>
- Asigură-te că videoclipul este public
- Link-urile scurte (youtu.be, bit.ly) funcționează
- Poți trimite multiple link-uri consecutive
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, parse_mode='HTML', reply_markup=reply_markup)

    elif query.data == 'platforms':
        platforms_text = """
🔗 <b>Platforme suportate în detaliu:</b>

<<<<<<< HEAD
📱 **TikTok**
- tiktok.com, vm.tiktok.com
- Videoclipuri publice
- Fără watermark

📸 **Instagram**
- instagram.com
- Postări video publice
- Reels și IGTV

📘 **Facebook**
- facebook.com, fb.watch, fb.me
=======
📱 <b>TikTok</b>
- tiktok.com
- Videoclipuri publice
- Fără watermark

📸 <b>Instagram</b>
- instagram.com/p/
- Postări video publice
- Reels și IGTV

📘 <b>Facebook</b>
- facebook.com, fb.watch
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
- Videoclipuri publice
- URL normalization

🐦 <b>Twitter/X</b>
- twitter.com, x.com
- Tweet-uri cu video publice

<<<<<<< HEAD
🧵 **Threads**
- threads.net, threads.com
- Postări video publice
- Platforma Meta

📌 **Pinterest**
- pinterest.com, pin.it
- Video pins
- Conținut multimedia

🔴 **Reddit**
- reddit.com, redd.it, v.redd.it
- Videoclipuri publice
- Subreddit-uri

🎬 **Vimeo**
- vimeo.com, player.vimeo.com
- Videoclipuri publice și premium

📺 **Dailymotion**
- dailymotion.com, dai.ly
- Videoclipuri publice
- Suport geo-restricții
=======
⚠️ <b>Notă:</b> YouTube nu este suportat momentan din cauza complexității tehnice și a restricțiilor platformei.
>>>>>>> f16d7f6b7f14800a43ce30bdb7d8cce6bda7096e
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(platforms_text, parse_mode='HTML', reply_markup=reply_markup)
        
    elif query.data == 'settings':
        settings_text = """
⚙️ <b>Setări și limitări:</b>

📏 <b>Limitări de timp:</b>
- Maximum 3 ore per videoclip
- Timeout procesare: 10 minute

💾 <b>Limitări de mărime:</b>
- Maximum 550MB (limită crescută)
- Calitate optimizată automat

🎬 <b>Calitate video:</b>
- Rezoluție maximă: 720p
- Format: MP4 (compatibil universal)
- Audio inclus automat

🔒 <b>Restricții:</b>
- Doar conținut public
- Fără videoclipuri protejate de copyright
- Fără conținut pentru adulți
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, parse_mode='HTML', reply_markup=reply_markup)
        
    elif query.data == 'faq':
        faq_text = """
❓ <b>Întrebări frecvente:</b>

<b>Q: De ce nu funcționează link-ul meu?</b>
A: Verifică că videoclipul este public și link-ul este corect.

<b>Q: Cât durează descărcarea?</b>
A: De obicei 10-60 secunde, depinde de mărimea videoclipului.

<b>Q: Pot descărca playlist-uri întregi?</b>
A: Nu, doar videoclipuri individuale.

<b>Q: De ce calitatea este mai mică?</b>
A: Pentru a respecta limitele Telegram (100MB).

<b>Q: Botul păstrează videoclipurile?</b>
A: Nu, toate fișierele sunt șterse automat după trimitere.

<b>Q: Pot folosi botul gratuit?</b>
A: Da, botul este complet gratuit!
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(faq_text, parse_mode='HTML', reply_markup=reply_markup)
        
    elif query.data == 'back_to_menu':
        welcome_message = """
🎬 <b>Bot Descărcare Video</b>

Bun venit! Sunt aici să te ajut să descarci videoclipuri de pe diverse platforme.

🔗 <b>Platforme suportate:</b>
• TikTok
• Instagram
• Facebook
• Twitter/X

⚠️ <b>Notă:</b> YouTube nu este suportat momentan din cauza complexității tehnice.

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
            [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionează erorile
    """
    logger.warning('Update "%s" caused error "%s"', update, context.error)

async def main():
    """
    Funcția principală care pornește botul
    """
    # TOKEN-ul este deja verificat la începutul fișierului
    # Dacă ajungem aici, token-ul este valid
    
    # Creează aplicația
    app = Application.builder().token(TOKEN).build()
    
    # Adaugă handler-ele
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Adaugă handler pentru erori
    app.add_error_handler(error_handler)
    
    # Pornește botul
    print("🤖 Botul pornește...")
    await app.run_polling()
    print("✅ Botul rulează! Apasă Ctrl+C pentru a opri.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
