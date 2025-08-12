#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛠️ IMPLEMENTARE FAZA 4 - Clarificarea Suportului YouTube
Telegram Video Downloader Bot - YouTube Support Clarification

Acest script implementează:
1. Dezactivarea completă a suportului YouTube
2. Mesaje clare pentru utilizatori despre platformele suportate
3. Actualizarea documentației și help-ului
"""

import os
import sys
import shutil
import re
from datetime import datetime
from pathlib import Path

def print_status(message, status="info"):
    """Printează mesaje cu status colorat"""
    emoji = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{emoji.get(status, 'ℹ️')} {message}")

def backup_file(file_path):
    """Creează backup pentru un fișier"""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup_phase4_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print_status(f"Backup creat: {backup_path}", "success")
        return backup_path
    return None

def disable_youtube_support():
    """Dezactivează complet suportul YouTube"""
    print_status("Dezactivez complet suportul YouTube...", "info")
    
    # Actualizează config.py
    config_path = "config.py"
    if os.path.exists(config_path):
        backup_file(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Elimină YouTube din platformele activate
        content = re.sub(r"'youtube':\s*True", "'youtube': False", content)
        content = re.sub(r"'youtube':\s*true", "'youtube': false", content)
        
        # Adaugă comentariu explicativ
        if "# YouTube support disabled" not in content:
            youtube_pattern = r"('youtube':\s*False[^,\n]*)"
            youtube_match = re.search(youtube_pattern, content)
            if youtube_match:
                replacement = youtube_match.group(1) + "  # YouTube support disabled due to API limitations"
                content = content.replace(youtube_match.group(1), replacement)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_status("YouTube dezactivat în config.py", "success")
    
    return True

def update_downloader_youtube_handling():
    """Actualizează downloader-ul pentru a gestiona YouTube"""
    print_status("Actualizez gestionarea YouTube în downloader...", "info")
    
    downloader_path = "downloader.py"
    if not os.path.exists(downloader_path):
        print_status(f"Fișierul {downloader_path} nu există!", "error")
        return False
    
    backup_file(downloader_path)
    
    # Citește conținutul
    with open(downloader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Adaugă funcție pentru verificarea YouTube
    if "def is_youtube_url" not in content:
        youtube_check_function = """
def is_youtube_url(url):
    \"\"\"Verifică dacă URL-ul este de la YouTube\"\"\"
    youtube_domains = [
        'youtube.com', 'www.youtube.com', 'm.youtube.com',
        'youtu.be', 'www.youtu.be'
    ]
    
    for domain in youtube_domains:
        if domain in url.lower():
            return True
    return False
"""
        
        # Găsește locul unde să inserez funcția (înainte de download_video)
        download_video_pos = content.find("def download_video(")
        if download_video_pos != -1:
            content = content[:download_video_pos] + youtube_check_function + "\n\n" + content[download_video_pos:]
            print_status("Adăugat funcția de verificare YouTube", "success")
    
    # Adaugă verificare YouTube la începutul funcției download_video
    download_function_pattern = r"(def download_video\([^)]+\):[^\n]*\n)(\s+)"
    download_match = re.search(download_function_pattern, content)
    if download_match and "is_youtube_url(url)" not in content:
        indent = download_match.group(2)
        youtube_check = f"""{indent}# Verifică dacă este URL YouTube (nu este suportat)
{indent}if is_youtube_url(url):
{indent}    logger.warning(f\"🚫 YouTube URL detected and blocked: {{url}}\")
{indent}    return {{
{indent}        'success': False,
{indent}        'error': 'YouTube nu este suportat din cauza limitărilor API. Platformele suportate: TikTok, Instagram, Facebook, Twitter/X, Threads, Pinterest, Reddit, Vimeo, Dailymotion.',
{indent}        'file_path': None,
{indent}        'file_size': 0,
{indent}        'duration': 0,
{indent}        'title': 'YouTube - Nu este suportat'
{indent}    }}
\n"""
        
        content = content[:download_match.end()] + youtube_check + content[download_match.end():]
        print_status("Adăugat verificare YouTube în download_video", "success")
    
    # Salvează fișierul actualizat
    with open(downloader_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def update_bot_help_messages():
    """Actualizează mesajele de help din bot"""
    print_status("Actualizez mesajele de help...", "info")
    
    bot_path = "bot.py"
    if not os.path.exists(bot_path):
        print_status(f"Fișierul {bot_path} nu există!", "error")
        return False
    
    backup_file(bot_path)
    
    # Citește conținutul
    with open(bot_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Actualizează mesajul de help
    new_help_text = """🤖 **Telegram Video Downloader Bot**

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
    
    # Caută și înlocuiește mesajul de help
    help_patterns = [
        r"help_text\s*=\s*f?[\"\'][^\"\']*(platformele suportate[^\"\']*)[\"\']",
        r"help_text\s*=\s*f?[\"\'][^\"\']*(Telegram Video Downloader Bot[^\"\']*)[\"\']",
        r"help_text\s*=\s*f?[\"\'][^\"\']*(🤖[^\"\']*)[\"\']"
    ]
    
    help_updated = False
    for pattern in help_patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, f'help_text = """{new_help_text}"""', content, flags=re.DOTALL)
            help_updated = True
            break
    
    if not help_updated:
        # Dacă nu găsește pattern-ul, caută orice help_text și îl înlocuiește
        help_text_pattern = r"help_text\s*=\s*f?[\"\'][^\"\']*(.*?)[\"\']"  
        if re.search(help_text_pattern, content, re.DOTALL):
            content = re.sub(help_text_pattern, f'help_text = """{new_help_text}"""', content, flags=re.DOTALL)
            help_updated = True
    
    if help_updated:
        print_status("Actualizat mesajul de help", "success")
    else:
        print_status("Nu am găsit help_text pentru actualizare", "warning")
    
    # Salvează fișierul actualizat
    with open(bot_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def verify_phase4_implementation():
    """Verifică dacă toate modificările din Faza 4 au fost aplicate"""
    print_status("Verificarea implementării Fazei 4...", "info")
    
    checks = {
        "YouTube dezactivat în config": False,
        "Funcție verificare YouTube adăugată": False,
        "Verificare YouTube în download_video": False,
        "Mesaj help actualizat": False
    }
    
    # Verifică config.py sau config.yaml
    config_files = ["config.py", "config.yaml"]
    for config_file in config_files:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_content = f.read()
            if ("'youtube': False" in config_content or "'youtube':False" in config_content or 
                "enabled: false" in config_content):
                checks["YouTube dezactivat în config"] = True
                break
    
    # Verifică downloader.py
    if os.path.exists("downloader.py"):
        with open("downloader.py", 'r', encoding='utf-8') as f:
            downloader_content = f.read()
        if "def is_youtube_url" in downloader_content:
            checks["Funcție verificare YouTube adăugată"] = True
        if "is_youtube_url(url)" in downloader_content:
            checks["Verificare YouTube în download_video"] = True
    
    # Verifică bot.py
    if os.path.exists("bot.py"):
        with open("bot.py", 'r', encoding='utf-8') as f:
            bot_content = f.read()
        if "Nu este suportat:** YouTube" in bot_content:
            checks["Mesaj help actualizat"] = True
    
    # Afișează rezultatele
    all_passed = True
    for check, passed in checks.items():
        status = "success" if passed else "error"
        print_status(f"{check}: {'✅' if passed else '❌'}", status)
        if not passed:
            all_passed = False
    
    return all_passed

def main():
    """Funcția principală pentru implementarea Fazei 4"""
    print_status("🚀 Începerea implementării Fazei 4 - Clarificarea Suportului YouTube", "info")
    print_status("Această fază va dezactiva complet suportul YouTube și va clarifica platformele suportate.", "info")
    
    # Verifică dacă suntem în directorul corect
    if not os.path.exists("bot.py") or not os.path.exists("downloader.py"):
        print_status("❌ Nu sunt în directorul corect sau fișierele bot nu există!", "error")
        return False
    
    tasks = [
        ("Dezactivarea suportului YouTube", disable_youtube_support),
        ("Actualizarea gestionării YouTube în downloader", update_downloader_youtube_handling),
        ("Actualizarea mesajelor de help", update_bot_help_messages)
    ]
    
    completed_tasks = 0
    
    for task_name, task_func in tasks:
        print_status(f"\n📋 {task_name}...", "info")
        try:
            if task_func():
                completed_tasks += 1
                print_status(f"✅ {task_name} - COMPLETAT", "success")
            else:
                print_status(f"❌ {task_name} - EȘUAT", "error")
        except Exception as e:
            print_status(f"❌ {task_name} - EROARE: {str(e)}", "error")
    
    # Verificarea finală
    print_status("\n🔍 Verificarea finală...", "info")
    if verify_phase4_implementation():
        print_status(f"\n🎉 FAZA 4 COMPLETATĂ CU SUCCES! ({completed_tasks}/{len(tasks)} task-uri)", "success")
        print_status("YouTube a fost dezactivat complet și utilizatorii vor primi mesaje clare despre platformele suportate.", "success")
        return True
    else:
        print_status(f"\n⚠️ FAZA 4 PARȚIAL COMPLETATĂ ({completed_tasks}/{len(tasks)} task-uri)", "warning")
        print_status("Unele modificări nu au fost aplicate corect. Verificați manual fișierele.", "warning")
        return False

if __name__ == "__main__":
    main()
