import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from downloader import download_video, is_supported_url

# Configurare logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token-ul botului (va fi setat prin variabilă de mediu)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

def start(update: Update, context: CallbackContext):
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
        [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

def help_command(update: Update, context: CallbackContext):
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
- Videoclipul este prea lung → Max 3 ore
- Videoclipul este prea mare → Max 550MB
- Link invalid → Verifică că link-ul este corect
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

def menu_command(update: Update, context: CallbackContext):
    """
    Comandă /menu - afișează meniul principal
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
        [InlineKeyboardButton("❓ Întrebări frecvente", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

def handle_message(update: Update, context: CallbackContext):
    """
    Gestionează mesajele cu link-uri video
    """
    url = update.message.text.strip()
    
    # Verifică dacă este un URL valid
    if not url.startswith(('http://', 'https://')):
        keyboard = [[InlineKeyboardButton("📖 Vezi cum să folosești botul", callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "❌ Te rog să trimiți un link valid (care începe cu http:// sau https://)\n\n"
            "💡 Trimite un link de pe YouTube, TikTok, Instagram, Facebook sau Twitter/X",
            reply_markup=reply_markup
        )
        return
    
    # Verifică dacă URL-ul este suportat
    if not is_supported_url(url):
        keyboard = [[InlineKeyboardButton("🔗 Vezi platformele suportate", callback_data='platforms')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "❌ Această platformă nu este suportată.\n\n"
            "Platforme suportate: YouTube, TikTok, Instagram, Facebook, Twitter/X",
            reply_markup=reply_markup
        )
        return
    
    # Afișează confirmarea cu butoane
    confirmation_text = f"🔗 **Link detectat:**\n`{url}`\n\n📥 Vrei să descarc acest videoclip?"
    
    keyboard = [
        [InlineKeyboardButton("✅ Da, descarcă!", callback_data=f'download_{url}')],
        [InlineKeyboardButton("❌ Anulează", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)

def process_download(update: Update, context: CallbackContext, url: str):
    """
    Procesează descărcarea videoclipului
    """
    query = update.callback_query
    
    # Trimite mesaj de procesare
    processing_message = query.edit_message_text(
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
        
        # Verifică mărimea fișierului (limită crescută la 550MB)
        file_size = os.path.getsize(filepath)
        if file_size > 550 * 1024 * 1024:  # 550MB
            raise Exception("Fișierul este prea mare (max 550MB)")
        
        # Creează caption cu titlu și informații
        caption = f"✅ **{title}**"
        if uploader:
            caption += f"\n👤 De la: {uploader}"
        if description and len(description) > 0:
            # Limitează descrierea la 200 caractere pentru caption
            desc_preview = description[:200]
            if len(description) > 200:
                desc_preview += "..."
            caption += f"\n📝 {desc_preview}"
        
        # Trimite videoclipul cu caption complet
        with open(filepath, 'rb') as video_file:
            query.message.reply_video(
                video=video_file,
                caption=caption,
                parse_mode='Markdown'
            )
        
        # Trimite mesaj cu opțiuni după descărcare
        keyboard = [
            [InlineKeyboardButton("📥 Descarcă alt videoclip", callback_data='new_download')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "✅ **Descărcare completă!**\n\nVideoclipul a fost trimis cu succes.\nCe vrei să faci acum?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Șterge fișierul temporar
        try:
            os.remove(filepath)
        except:
            pass
            
        # Șterge mesajul de procesare
        try:
            processing_message.delete()
        except:
            pass
            
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
            error_message = "❌ Fișierul este prea mare (maximum 550MB)."
        
        # Adaugă butoane pentru a încerca din nou sau a merge la meniu
        keyboard = [
            [InlineKeyboardButton("🔄 Încearcă din nou", callback_data=f'download_{url}')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(error_message, reply_markup=reply_markup)
        
        # Șterge mesajul de procesare
        try:
            processing_message.delete()
        except:
            pass

def button_handler(update: Update, context: CallbackContext):
    """
    Gestionează apăsările pe butoanele inline
    """
    query = update.callback_query
    query.answer()
    
    # Gestionează descărcarea
    if query.data.startswith('download_'):
        url = query.data.replace('download_', '')
        process_download(update, context, url)
        return
    
    # Gestionează cererea pentru descărcare nouă
    elif query.data == 'new_download':
        query.edit_message_text(
            "📥 **Gata pentru o nouă descărcare!**\n\n"
            "Trimite-mi un link de pe YouTube, TikTok, Instagram, Facebook sau Twitter/X"
        )
        return
    
    # Gestionează anularea
    elif query.data == 'cancel':
        keyboard = [[InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Descărcarea a fost anulată.\n\n💡 Trimite un alt link când ești gata!",
            reply_markup=reply_markup
        )
        return
    
    elif query.data == 'help':
        help_text = """
🆘 **Cum să folosești botul:**

1. 📋 Copiază link-ul videoclipului
2. 📤 Trimite-l în acest chat
3. ⏳ Așteaptă să fie procesat
4. 📥 Primești videoclipul descărcat

💡 **Sfaturi:**
- Asigură-te că videoclipul este public
- Link-urile scurte (youtu.be, bit.ly) funcționează
- Poți trimite multiple link-uri consecutive
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    elif query.data == 'platforms':
        platforms_text = """
🔗 **Platforme suportate în detaliu:**

🎥 **YouTube**
- youtube.com, youtu.be
- Videoclipuri publice și unlisted
- Playlist-uri (primul video)

📱 **TikTok**
- tiktok.com
- Videoclipuri publice
- Fără watermark

📸 **Instagram**
- instagram.com/p/
- Postări video publice
- Reels și IGTV

📘 **Facebook**
- facebook.com, fb.watch
- Videoclipuri publice

🐦 **Twitter/X**
- twitter.com, x.com
- Tweet-uri cu video publice
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(platforms_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    elif query.data == 'settings':
        settings_text = """
⚙️ **Setări și limitări:**

📏 **Limitări de timp:**
- Maximum 3 ore per videoclip
- Timeout procesare: 10 minute

💾 **Limitări de mărime:**
- Maximum 550MB (limită crescută)
- Calitate optimizată automat

🎬 **Calitate video:**
- Rezoluție maximă: 720p
- Format: MP4 (compatibil universal)
- Audio inclus automat

🔒 **Restricții:**
- Doar conținut public
- Fără videoclipuri protejate de copyright
- Fără conținut pentru adulți
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(settings_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    elif query.data == 'faq':
        faq_text = """
❓ **Întrebări frecvente:**

**Q: De ce nu funcționează link-ul meu?**
A: Verifică că videoclipul este public și link-ul este corect.

**Q: Cât durează descărcarea?**
A: De obicei 10-60 secunde, depinde de mărimea videoclipului.

**Q: Pot descărca playlist-uri întregi?**
A: Nu, doar videoclipuri individuale.

**Q: De ce calitatea este mai mică?**
A: Pentru a respecta limitele Telegram (100MB).

**Q: Botul păstrează videoclipurile?**
A: Nu, toate fișierele sunt șterse automat după trimitere.

**Q: Pot folosi botul gratuit?**
A: Da, botul este complet gratuit!
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(faq_text, parse_mode='Markdown', reply_markup=reply_markup)
        
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
        
        query.edit_message_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

def error_handler(update: Update, context: CallbackContext):
    """
    Gestionează erorile
    """
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """
    Funcția principală care pornește botul
    """
    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Eroare: Te rog să setezi TELEGRAM_BOT_TOKEN în variabilele de mediu")
        return
    
    # Creează updater-ul
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Adaugă handler-ele
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("menu", menu_command))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Adaugă handler pentru erori
    dispatcher.add_error_handler(error_handler)
    
    # Pornește botul
    print("🤖 Botul pornește...")
    updater.start_polling()
    print("✅ Botul rulează! Apasă Ctrl+C pentru a opri.")
    updater.idle()

if __name__ == '__main__':
    main()