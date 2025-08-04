import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
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
    Comandă /start - mesaj de bun venit
    """
    welcome_message = """
🎬 **Bot Descărcare Video**

Trimite-mi un link de pe:
• YouTube
• TikTok  
• Instagram
• Facebook
• Twitter/X

Și îți voi trimite videoclipul descărcat!

⚠️ **Limitări:**
- Videoclipuri max 15 minute
- Calitate max 720p
- Doar videoclipuri publice

📝 Comenzi disponibile:
/start - Afișează acest mesaj
/help - Ajutor
    """
    update.message.reply_text(welcome_message, parse_mode='Markdown')

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
- Videoclipul este prea lung → Max 15 minute
- Link invalid → Verifică că link-ul este corect
    """
    update.message.reply_text(help_text, parse_mode='Markdown')

def handle_message(update: Update, context: CallbackContext):
    """
    Gestionează mesajele cu link-uri video
    """
    url = update.message.text.strip()
    
    # Verifică dacă este un URL valid
    if not url.startswith(('http://', 'https://')):
        update.message.reply_text(
            "❌ Te rog să trimiți un link valid (care începe cu http:// sau https://)"
        )
        return
    
    # Verifică dacă URL-ul este suportat
    if not is_supported_url(url):
        update.message.reply_text(
            "❌ Această platformă nu este suportată.\n\n"
            "Platforme suportate: YouTube, TikTok, Instagram, Facebook, Twitter/X"
        )
        return
    
    # Trimite mesaj de procesare
    processing_message = update.message.reply_text(
        "⏳ Procesez videoclipul...\nTe rog să aștepți."
    )
    
    try:
        # Descarcă videoclipul
        filepath = download_video(url)
        
        if not filepath or not os.path.exists(filepath):
            raise Exception("Fișierul nu a fost găsit după descărcare")
        
        # Verifică mărimea fișierului (Telegram are limită de 100MB)
        file_size = os.path.getsize(filepath)
        if file_size > 100 * 1024 * 1024:  # 100MB
            raise Exception("Fișierul este prea mare (max 100MB pentru Telegram)")
        
        # Trimite videoclipul
        with open(filepath, 'rb') as video_file:
            update.message.reply_video(
                video=video_file,
                caption="✅ Videoclip descărcat cu succes!"
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
            error_message = "❌ Videoclipul este prea lung (maximum 15 minute)."
        elif "prea mare" in str(e):
            error_message = "❌ Fișierul este prea mare (maximum 100MB)."
        
        update.message.reply_text(error_message)
        
        # Șterge mesajul de procesare
        try:
            processing_message.delete()
        except:
            pass

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
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Adaugă handler-ele
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Adaugă handler pentru erori
    dp.add_error_handler(error_handler)
    
    # Pornește botul
    print("🤖 Botul pornește...")
    updater.start_polling()
    print("✅ Botul rulează! Apasă Ctrl+C pentru a opri.")
    updater.idle()

if __name__ == '__main__':
    main()