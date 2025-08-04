import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from downloader import download_video, is_supported_url
import tempfile

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

# Funcții pentru comenzi (aceleași ca în bot.py)
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
- Videoclipuri max 10 minute
- Calitate max 720p
- Doar videoclipuri publice

📝 Comenzi disponibile:
/start - Afișează acest mesaj
/help - Ajutor
    """
    update.message.reply_text(welcome_message, parse_mode='Markdown')

def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
- Videoclipul este prea lung → Max 10 minute
- Link invalid → Verifică că link-ul este corect
    """
    update.message.reply_text(help_text, parse_mode='Markdown')

def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        update.message.reply_text(
            "❌ Te rog să trimiți un link valid (care începe cu http:// sau https://)"
        )
        return
    
    if not is_supported_url(url):
        update.message.reply_text(
            "❌ Această platformă nu este suportată.\n\n"
            "Platforme suportate: YouTube, TikTok, Instagram, Facebook, Twitter/X"
        )
        return
    
    processing_message = update.message.reply_text(
        "⏳ Procesez videoclipul...\nTe rog să aștepți."
    )
    
    try:
        filepath = download_video(url)
        
        if not filepath or not os.path.exists(filepath):
            raise Exception("Fișierul nu a fost găsit după descărcare")
        
        file_size = os.path.getsize(filepath)
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise Exception("Fișierul este prea mare (max 50MB pentru Telegram)")
        
        with open(filepath, 'rb') as video_file:
            update.message.reply_video(
                video=video_file,
                caption="✅ Videoclip descărcat cu succes!"
            )
        
        try:
            os.remove(filepath)
        except:
            pass
            
        try:
            processing_message.delete()
        except:
            pass
            
    except Exception as e:
        error_message = f"❌ Eroare: {str(e)}"
        
        if "private" in str(e).lower():
            error_message = "❌ Videoclipul este privat și nu poate fi descărcat."
        elif "not available" in str(e).lower():
            error_message = "❌ Videoclipul nu este disponibil în regiunea ta."
        elif "prea lung" in str(e):
            error_message = "❌ Videoclipul este prea lung (maximum 10 minute)."
        elif "prea mare" in str(e):
            error_message = "❌ Fișierul este prea mare (maximum 50MB)."
        
        update.message.reply_text(error_message)
        
        try:
            processing_message.delete()
        except:
            pass

# Adaugă handler-ele
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Rute Flask
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'Bot is running',
        'message': 'Telegram Video Downloader Bot is active'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        # Pentru webhook sincron, folosim direct bot-ul
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Eroare în webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        result = bot.set_webhook(url=webhook_url)
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
    return jsonify({
        'status': 'healthy',
        'bot_info': bot.get_me().to_dict()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)