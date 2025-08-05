import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from downloader import download_video, is_supported_url
import tempfile
import asyncio

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

# Funcții pentru comenzi cu meniu interactiv
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Trimite un ping către server pentru a-l menține activ
    """
    try:
        import requests
        import time
        
        # Trimite mesaj de confirmare
        update.message.reply_text("🔄 **Ping în curs...**\n\nVerific starea serverului...", parse_mode='Markdown')
        
        start_time = time.time()
        
        # Trimite ping către propriul server
        response = requests.get(f"{WEBHOOK_URL}/health", timeout=10)
        
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        if response.status_code == 200:
            keyboard = [
                [InlineKeyboardButton("🔄 Ping din nou", callback_data='ping_again')],
                [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                f"✅ **Server activ!**\n\n"
                f"📡 Timp de răspuns: {response_time}ms\n"
                f"🌐 Status: Online\n"
                f"⏰ Ultima verificare: {time.strftime('%H:%M:%S')}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            update.message.reply_text(
                f"⚠️ **Server răspunde cu erori**\n\n"
                f"📡 Status Code: {response.status_code}\n"
                f"⏰ Timp: {time.strftime('%H:%M:%S')}",
                parse_mode='Markdown'
            )
            
    except requests.exceptions.Timeout:
        update.message.reply_text(
            "⏰ **Timeout**\n\n"
            "Serverul nu răspunde în timp util. Poate fi în modul sleep.",
            parse_mode='Markdown'
        )
    except Exception as e:
        update.message.reply_text(
            f"❌ **Eroare la ping**\n\n"
            f"Detalii: {str(e)}",
            parse_mode='Markdown'
        )

def wakeup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Trezește serverul din modul sleep cu multiple ping-uri
    """
    try:
        import requests
        import time
        
        # Trimite mesaj de confirmare
        message = update.message.reply_text(
            "🌅 **Trezire server în curs...**\n\n"
            "📡 Trimit multiple ping-uri pentru a trezi serverul...\n"
            "⏳ Te rog așteaptă...",
            parse_mode='Markdown'
        )
        
        success_count = 0
        total_attempts = 3
        
        for i in range(total_attempts):
            try:
                start_time = time.time()
                response = requests.get(f"{WEBHOOK_URL}/health", timeout=15)
                end_time = time.time()
                response_time = round((end_time - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    success_count += 1
                    
                # Actualizează mesajul cu progresul
                progress = "🟢" * (i + 1) + "⚪" * (total_attempts - i - 1)
                message.edit_text(
                    f"🌅 **Trezire server în curs...**\n\n"
                    f"📡 Progres: {progress}\n"
                    f"✅ Ping {i + 1}/{total_attempts}: {response_time}ms\n"
                    f"⏳ Te rog așteaptă...",
                    parse_mode='Markdown'
                )
                
                if i < total_attempts - 1:
                    time.sleep(2)  # Pauză între ping-uri
                    
            except Exception as ping_error:
                # Actualizează cu eroarea
                progress = "🟢" * i + "🔴" + "⚪" * (total_attempts - i - 1)
                message.edit_text(
                    f"🌅 **Trezire server în curs...**\n\n"
                    f"📡 Progres: {progress}\n"
                    f"❌ Ping {i + 1}/{total_attempts}: Eroare\n"
                    f"⏳ Te rog așteaptă...",
                    parse_mode='Markdown'
                )
                time.sleep(3)  # Pauză mai lungă după eroare
        
        # Mesaj final
        if success_count > 0:
            keyboard = [
                [InlineKeyboardButton("🔄 Verifică din nou", callback_data='ping_again')],
                [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message.edit_text(
                f"✅ **Server trezit cu succes!**\n\n"
                f"📊 Ping-uri reușite: {success_count}/{total_attempts}\n"
                f"🌐 Status: Online\n"
                f"⏰ Completat la: {time.strftime('%H:%M:%S')}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            message.edit_text(
                f"❌ **Nu s-a putut trezi serverul**\n\n"
                f"📊 Toate ping-urile au eșuat: 0/{total_attempts}\n"
                f"🔧 Încearcă din nou peste câteva minute.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        update.message.reply_text(
            f"❌ **Eroare la trezirea serverului**\n\n"
            f"Detalii: {str(e)}",
            parse_mode='Markdown'
        )

def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionează mesajele text (link-uri) cu confirmare înainte de descărcare
    """
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        keyboard = [[InlineKeyboardButton("📖 Cum să folosesc botul", callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "❌ Te rog să trimiți un link valid (care începe cu http:// sau https://)",
            reply_markup=reply_markup
        )
        return
    
    if not is_supported_url(url):
        update.message.reply_text(
            "❌ Această platformă nu este suportată.\n\n"
            "Platforme suportate: YouTube, TikTok, Instagram, Facebook, Twitter/X"
        )
        return
    
    # Afișează preview cu butoane de confirmare
    keyboard = [
        [InlineKeyboardButton("✅ Da, descarcă!", callback_data=f'download_{url}')],
        [InlineKeyboardButton("❌ Anulează", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"🔗 **Link detectat:**\n{url}\n\n📥 Vrei să descarc acest videoclip?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """
    Procesează descărcarea efectivă a videoclipului
    """
    query = update.callback_query
    query.answer()
    
    processing_message = query.edit_message_text(
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
            context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption="✅ Videoclip descărcat cu succes!"
            )
        
        # Mesaj de succes cu opțiuni
        keyboard = [
            [InlineKeyboardButton("📥 Descarcă alt videoclip", callback_data='back_to_menu')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🎉 **Descărcare finalizată cu succes!**\n\nCe vrei să faci acum?",
            parse_mode='Markdown',
            reply_markup=reply_markup
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
            error_message = "❌ Videoclipul este prea lung (maximum 15 minute)."
        elif "prea mare" in str(e):
            error_message = "❌ Fișierul este prea mare (maximum 50MB)."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Încearcă din nou", callback_data='back_to_menu')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(error_message, reply_markup=reply_markup)
        
        try:
            processing_message.delete()
        except:
            pass

def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionează toate callback-urile de la butoanele inline
    """
    query = update.callback_query
    query.answer()
    
    if query.data == 'help':
        help_text = """
🆘 **Cum să folosești botul:**

1. Copiază link-ul videoclipului
2. Trimite-l în acest chat
3. Confirmă descărcarea
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
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == 'platforms':
        platforms_text = """
🔗 **Platforme Suportate:**

✅ **YouTube**
- youtube.com
- youtu.be
- Videoclipuri publice și unlisted

✅ **TikTok**
- tiktok.com
- Videoclipuri publice

✅ **Instagram**
- instagram.com
- Reels și videoclipuri publice

✅ **Facebook**
- facebook.com
- fb.watch
- Videoclipuri publice

✅ **Twitter/X**
- twitter.com
- x.com
- Videoclipuri publice

⚠️ **Limitări:**
- Doar conținut public
- Max 15 minute durată
- Max 50MB mărime fișier
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(platforms_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == 'settings':
        settings_text = """
⚙️ **Setări și Limitări:**

📏 **Limitări de durată:**
- Maximum 15 minute per videoclip
- Videoclipuri mai lungi vor fi respinse

📦 **Limitări de mărime:**
- Maximum 50MB per fișier
- Telegram nu permite fișiere mai mari

🎥 **Calitate video:**
- Calitate maximă: 720p
- Format: MP4 (compatibil universal)

🔒 **Restricții de conținut:**
- Doar videoclipuri publice
- Nu funcționează cu conținut privat
- Nu funcționează cu live streams

⚡ **Performanță:**
- Timp mediu de procesare: 30-60 secunde
- Depinde de mărimea videoclipului
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Înapoi la meniu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(settings_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data == 'faq':
        faq_text = """
❓ **Întrebări Frecvente:**

**Q: De ce nu funcționează link-ul meu?**
A: Verifică că videoclipul este public și că platforma este suportată.

**Q: Cât timp durează descărcarea?**
A: De obicei 30-60 secunde, depinde de mărimea videoclipului.

**Q: Pot descărca videoclipuri private?**
A: Nu, doar videoclipuri publice sunt suportate.

**Q: De ce calitatea este limitată la 720p?**
A: Pentru a respecta limitele de mărime ale Telegram.

**Q: Funcționează cu live streams?**
A: Nu, doar videoclipuri înregistrate.

**Q: Este sigur să folosesc botul?**
A: Da, nu stocăm videoclipurile sau datele tale.

**Q: Pot descărca playlist-uri întregi?**
A: Nu, doar videoclipuri individuale.
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
        
        query.edit_message_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif query.data.startswith('download_'):
        url = query.data[9:]  # Elimină 'download_' din început
        process_download(update, context, url)
    
    elif query.data == 'cancel':
        keyboard = [
            [InlineKeyboardButton("🔄 Încearcă din nou", callback_data='back_to_menu')],
            [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ **Descărcare anulată**\n\nCe vrei să faci acum?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == 'ping_again':
        # Simulează comanda /ping
        import requests
        import time
        
        try:
            query.edit_message_text("🔄 **Ping în curs...**\n\nVerific starea serverului...", parse_mode='Markdown')
            
            start_time = time.time()
            response = requests.get(f"{WEBHOOK_URL}/health", timeout=10)
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                keyboard = [
                    [InlineKeyboardButton("🔄 Ping din nou", callback_data='ping_again')],
                    [InlineKeyboardButton("🌅 Wakeup server", callback_data='wakeup_server')],
                    [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    f"✅ **Server activ!**\n\n"
                    f"📡 Timp de răspuns: {response_time}ms\n"
                    f"🌐 Status: Online\n"
                    f"⏰ Ultima verificare: {time.strftime('%H:%M:%S')}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("🔄 Încearcă din nou", callback_data='ping_again')],
                    [InlineKeyboardButton("🌅 Wakeup server", callback_data='wakeup_server')],
                    [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    f"⚠️ **Server răspunde cu erori**\n\n"
                    f"📡 Status Code: {response.status_code}\n"
                    f"⏰ Timp: {time.strftime('%H:%M:%S')}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
        except requests.exceptions.Timeout:
            keyboard = [
                [InlineKeyboardButton("🔄 Încearcă din nou", callback_data='ping_again')],
                [InlineKeyboardButton("🌅 Wakeup server", callback_data='wakeup_server')],
                [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "⏰ **Timeout**\n\n"
                "Serverul nu răspunde în timp util. Poate fi în modul sleep.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            query.edit_message_text(
                f"❌ **Eroare la ping**\n\n"
                f"Detalii: {str(e)}",
                parse_mode='Markdown'
            )
    
    elif query.data == 'wakeup_server':
        # Simulează comanda /wakeup
        import requests
        import time
        
        try:
            query.edit_message_text(
                "🌅 **Trezire server în curs...**\n\n"
                "📡 Trimit multiple ping-uri pentru a trezi serverul...\n"
                "⏳ Te rog așteaptă...",
                parse_mode='Markdown'
            )
            
            success_count = 0
            total_attempts = 3
            
            for i in range(total_attempts):
                try:
                    start_time = time.time()
                    response = requests.get(f"{WEBHOOK_URL}/health", timeout=15)
                    end_time = time.time()
                    response_time = round((end_time - start_time) * 1000, 2)
                    
                    if response.status_code == 200:
                        success_count += 1
                        
                    # Actualizează mesajul cu progresul
                    progress = "🟢" * (i + 1) + "⚪" * (total_attempts - i - 1)
                    query.edit_message_text(
                        f"🌅 **Trezire server în curs...**\n\n"
                        f"📡 Progres: {progress}\n"
                        f"✅ Ping {i + 1}/{total_attempts}: {response_time}ms\n"
                        f"⏳ Te rog așteaptă...",
                        parse_mode='Markdown'
                    )
                    
                    if i < total_attempts - 1:
                        time.sleep(2)  # Pauză între ping-uri
                        
                except Exception as ping_error:
                    # Actualizează cu eroarea
                    progress = "🟢" * i + "🔴" + "⚪" * (total_attempts - i - 1)
                    query.edit_message_text(
                        f"🌅 **Trezire server în curs...**\n\n"
                        f"📡 Progres: {progress}\n"
                        f"❌ Ping {i + 1}/{total_attempts}: Eroare\n"
                        f"⏳ Te rog așteaptă...",
                        parse_mode='Markdown'
                    )
                    time.sleep(3)  # Pauză mai lungă după eroare
            
            # Mesaj final
            if success_count > 0:
                keyboard = [
                    [InlineKeyboardButton("🔄 Verifică din nou", callback_data='ping_again')],
                    [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    f"✅ **Server trezit cu succes!**\n\n"
                    f"📊 Ping-uri reușite: {success_count}/{total_attempts}\n"
                    f"🌐 Status: Online\n"
                    f"⏰ Completat la: {time.strftime('%H:%M:%S')}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("🔄 Încearcă din nou", callback_data='wakeup_server')],
                    [InlineKeyboardButton("🏠 Meniu principal", callback_data='back_to_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    f"❌ **Nu s-a putut trezi serverul**\n\n"
                    f"📊 Toate ping-urile au eșuat: 0/{total_attempts}\n"
                    f"🔧 Încearcă din nou peste câteva minute.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            query.edit_message_text(
                f"❌ **Eroare la trezirea serverului**\n\n"
                f"Detalii: {str(e)}",
                parse_mode='Markdown'
            )

# Adaugă handler-ele
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("menu", menu_command))
application.add_handler(CommandHandler("ping", ping_command))
application.add_handler(CommandHandler("wakeup", wakeup_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(button_handler))

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