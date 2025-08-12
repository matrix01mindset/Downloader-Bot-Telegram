#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛠️ IMPLEMENTARE FAZA 1 - Remedieri Critice Imediate
Telegram Video Downloader Bot - Security Fixes

Acest script implementează remedierea problemelor critice:
1. Standardizarea limitelor de mărime fișiere
2. Eliminarea token-ului default nesigur
3. Dezactivarea forțată a debug mode
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
        backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print_status(f"Backup creat: {backup_path}", "success")
        return backup_path
    return None

def update_config_file():
    """Actualizează config.py cu limite standardizate"""
    print_status("Actualizez config.py cu limite standardizate...", "info")
    
    config_path = "utils/config.py"
    if not os.path.exists(config_path):
        print_status(f"Fișierul {config_path} nu există!", "error")
        return False
    
    # Backup
    backup_file(config_path)
    
    # Citește conținutul
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Găsește secțiunea platforms și actualizează limitele
    platforms_section = re.search(r"'platforms':\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}", content, re.DOTALL)
    
    if platforms_section:
        # Înlocuiește limitele în toate platformele
        new_content = content
        
        # Actualizează limitele pentru fiecare platformă
        platform_updates = {
            'youtube': "'max_file_size_mb': 45",
            'instagram': "'max_file_size_mb': 45", 
            'tiktok': "'max_file_size_mb': 45",
            'facebook': "'max_file_size_mb': 45",
            'twitter': "'max_file_size_mb': 45"
        }
        
        for platform, new_limit in platform_updates.items():
            # Găsește și înlocuiește limita pentru fiecare platformă
            pattern = f"('{platform}':\s*\{{[^}}]*)'max_file_size_mb':\s*\d+([^}}]*\}})"
            replacement = f"\\1{new_limit}\\2"
            new_content = re.sub(pattern, replacement, new_content)
        
        # Adaugă secțiunea file_limits dacă nu există
        if "'file_limits'" not in new_content:
            # Găsește sfârșitul secțiunii platforms
            platforms_end = new_content.find("}", new_content.find("'platforms'"))
            if platforms_end != -1:
                # Găsește sfârșitul secțiunii complete
                brace_count = 0
                pos = new_content.find("'platforms'")
                while pos < len(new_content):
                    if new_content[pos] == '{':
                        brace_count += 1
                    elif new_content[pos] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            break
                    pos += 1
                
                # Inserează secțiunea file_limits după platforms
                file_limits_section = """,
            'file_limits': {
                'telegram_bot_max_mb': 45,  # Limita sigură pentru bot-uri Telegram
                'download_max_mb': 50,      # Limita pentru descărcare
                'platform_fallback_mb': 45, # Fallback pentru platforme
                'max_duration_seconds': 3600 # Limita de durată (1 oră)
            }"""
                new_content = new_content[:pos+1] + file_limits_section + new_content[pos+1:]
        
        # Salvează fișierul actualizat
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print_status("config.py actualizat cu limite standardizate", "success")
        return True
    else:
        print_status("Nu am găsit secțiunea platforms în config.py", "error")
        return False

def update_bot_file():
    """Actualizează bot.py pentru eliminarea token-ului default"""
    print_status("Actualizez bot.py pentru eliminarea token-ului default...", "info")
    
    bot_path = "bot.py"
    if not os.path.exists(bot_path):
        print_status(f"Fișierul {bot_path} nu există!", "error")
        return False
    
    # Backup
    backup_file(bot_path)
    
    # Citește conținutul
    with open(bot_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Înlocuiește linia cu token-ul
    old_token_line = "TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')"
    new_token_section = """TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN nu este setat în variabilele de mediu!")
    print("❌ EROARE: TELEGRAM_BOT_TOKEN nu este setat!")
    print("💡 Setează token-ul în fișierul .env sau ca variabilă de mediu")
    sys.exit(1)"""
    
    if old_token_line in content:
        content = content.replace(old_token_line, new_token_section)
        
        # Adaugă import sys dacă nu există
        if "import sys" not in content:
            content = content.replace("import os", "import os\nimport sys")
        
        # Salvează fișierul actualizat
        with open(bot_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_status("bot.py actualizat - token default eliminat", "success")
        return True
    else:
        print_status("Nu am găsit linia cu token-ul default în bot.py", "warning")
        return False

def update_app_file():
    """Actualizează app.py pentru dezactivarea forțată a debug mode"""
    print_status("Actualizez app.py pentru dezactivarea debug mode...", "info")
    
    app_path = "app.py"
    if not os.path.exists(app_path):
        print_status(f"Fișierul {app_path} nu există!", "error")
        return False
    
    # Backup
    backup_file(app_path)
    
    # Citește conținutul
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Adaugă verificarea pentru debug mode după inițializarea app
    debug_check = """
# 🛡️ SECURITATE: Forțează dezactivarea debug mode în producție
if os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER'):
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    logger.info("🔒 Debug mode forțat dezactivat pentru producție")
else:
    logger.info("🔧 Rulare în modul development")"""
    
    # Găsește locul unde să inserez verificarea
    app_creation_pattern = r"(app = Flask\(__name__\)[^\n]*\n)"
    match = re.search(app_creation_pattern, content)
    
    if match and debug_check not in content:
        # Inserează verificarea după crearea app-ului
        insertion_point = match.end()
        content = content[:insertion_point] + debug_check + "\n" + content[insertion_point:]
        
        # Salvează fișierul actualizat
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_status("app.py actualizat - debug mode securizat", "success")
        return True
    else:
        if debug_check in content:
            print_status("Verificarea debug mode există deja în app.py", "warning")
        else:
            print_status("Nu am găsit locul pentru inserarea verificării debug", "error")
        return False

def update_file_size_limits():
    """Actualizează limitele de mărime în toate fișierele relevante"""
    print_status("Standardizez limitele de mărime în toate fișierele...", "info")
    
    files_to_update = {
        "app.py": [
            (r"file_size > \d+ \* 1024 \* 1024", "file_size > 45 * 1024 * 1024"),
            (r"\d+MB pentru bot-uri", "45MB pentru bot-uri"),
            (r"Limita Telegram: \d+MB", "Limita Telegram: 45MB")
        ],
        "bot.py": [
            (r"file_size > \d+ \* 1024 \* 1024", "file_size > 45 * 1024 * 1024"),
            (r"\d+MB \(buffer pentru limita Telegram", "45MB (buffer pentru limita Telegram")
        ],
        "downloader.py": [
            (r"'filesize': '\d+M'", "'filesize': '45M'"),
            (r"format.*best.*\d+M", "format=best[filesize<45M][height<=720]")
        ]
    }
    
    success_count = 0
    
    for file_path, replacements in files_to_update.items():
        if os.path.exists(file_path):
            backup_file(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print_status(f"Limite actualizate în {file_path}", "success")
                success_count += 1
            else:
                print_status(f"Nu am găsit limite de actualizat în {file_path}", "warning")
    
    return success_count > 0

def verify_changes():
    """Verifică că modificările au fost aplicate corect"""
    print_status("Verific modificările aplicate...", "info")
    
    issues = []
    
    # Verifică bot.py
    if os.path.exists("bot.py"):
        with open("bot.py", 'r', encoding='utf-8') as f:
            bot_content = f.read()
        
        if "YOUR_BOT_TOKEN_HERE" in bot_content:
            issues.append("Token default încă prezent în bot.py")
        
        if "sys.exit(1)" not in bot_content:
            issues.append("Verificarea token-ului nu a fost adăugată în bot.py")
    
    # Verifică app.py
    if os.path.exists("app.py"):
        with open("app.py", 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        if "app.config['DEBUG'] = False" not in app_content:
            issues.append("Verificarea debug mode nu a fost adăugată în app.py")
    
    # Verifică config.py
    if os.path.exists("utils/config.py"):
        with open("utils/config.py", 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        if "'file_limits'" not in config_content:
            issues.append("Secțiunea file_limits nu a fost adăugată în config.py")
    
    if issues:
        print_status("Probleme găsite:", "warning")
        for issue in issues:
            print_status(f"  - {issue}", "error")
        return False
    else:
        print_status("Toate modificările au fost aplicate cu succes!", "success")
        return True

def main():
    """Funcția principală de implementare"""
    print_status("🛠️ ÎNCEPE IMPLEMENTAREA FAZEI 1 - Remedieri Critice Imediate", "info")
    print_status("="*60, "info")
    
    # Verifică că suntem în directorul corect
    if not os.path.exists("app.py") or not os.path.exists("bot.py"):
        print_status("Nu sunt în directorul corect al proiectului!", "error")
        return False
    
    success_count = 0
    total_tasks = 4
    
    # 1. Actualizează config.py
    if update_config_file():
        success_count += 1
    
    # 2. Actualizează bot.py
    if update_bot_file():
        success_count += 1
    
    # 3. Actualizează app.py
    if update_app_file():
        success_count += 1
    
    # 4. Standardizează limitele în toate fișierele
    if update_file_size_limits():
        success_count += 1
    
    print_status("="*60, "info")
    print_status(f"Implementare completă: {success_count}/{total_tasks} task-uri reușite", "info")
    
    # Verifică modificările
    if verify_changes():
        print_status("✅ FAZA 1 IMPLEMENTATĂ CU SUCCES!", "success")
        print_status("Următorul pas: Rulează 'python test_local.py' pentru testare", "info")
        return True
    else:
        print_status("❌ Unele modificări nu au fost aplicate corect", "error")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)