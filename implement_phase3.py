#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛠️ IMPLEMENTARE FAZA 3 - Optimizarea Cache-ului
Telegram Video Downloader Bot - Cache Thread-Safety

Acest script implementează:
1. Făcarea cache-ului thread-safe
2. Prevenirea race conditions
3. Optimizarea performanței cache-ului
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
        backup_path = f"{file_path}.backup_phase3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print_status(f"Backup creat: {backup_path}", "success")
        return backup_path
    return None

def update_cache_manager():
    """Actualizează cache manager-ul pentru thread-safety"""
    print_status("Actualizez cache manager-ul pentru thread-safety...", "info")
    
    cache_path = "utils/cache.py"
    if not os.path.exists(cache_path):
        print_status(f"Fișierul {cache_path} nu există!", "error")
        return False
    
    # Backup
    backup_file(cache_path)
    
    # Citește conținutul
    with open(cache_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifică dacă threading este deja importat
    if "import threading" not in content:
        # Adaugă import pentru threading
        import_pattern = r"(import [^\n]+\n)+"
        import_match = re.findall(import_pattern, content)
        if import_match:
            last_import_pos = content.rfind(import_match[-1]) + len(import_match[-1])
            content = content[:last_import_pos] + "import threading\n" + content[last_import_pos:]
        print_status("Adăugat import threading", "success")
    
    # Adaugă lock în __init__ dacă nu există
    if "self._lock = threading.Lock()" not in content:
        init_pattern = r"(def __init__\(self[^)]*\):[^\n]*\n)(\s+)"
        init_match = re.search(init_pattern, content)
        if init_match:
            indent = init_match.group(2)
            lock_line = f"{indent}self._lock = threading.Lock()\n"
            content = content[:init_match.end()] + lock_line + content[init_match.end():]
            print_status("Adăugat lock în __init__", "success")
    
    # Actualizează metoda get pentru thread-safety
    get_method_pattern = r"(def get\(self, key: str\)[^:]*:)([^\n]*\n)((?:\s+[^\n]*\n)*)"
    get_match = re.search(get_method_pattern, content, re.MULTILINE)
    if get_match:
        method_signature = get_match.group(1)
        method_body = get_match.group(3)
        
        # Verifică dacă metoda nu este deja thread-safe
        if "with self._lock:" not in method_body:
            # Găsește indentarea
            indent_match = re.search(r"\n(\s+)", method_body)
            indent = indent_match.group(1) if indent_match else "        "
            
            # Creează noua metodă thread-safe
            new_method = f"{method_signature}\n{indent}with self._lock:\n"
            # Re-indentează corpul metodei
            indented_body = "\n".join([f"{indent}    {line}" if line.strip() else line 
                                     for line in method_body.split("\n")])
            new_method += indented_body
            
            content = content.replace(get_match.group(0), new_method)
            print_status("Actualizat metoda get pentru thread-safety", "success")
    
    # Actualizează metoda set pentru thread-safety
    set_method_pattern = r"(def set\(self, key: str, value: Any[^)]*\)[^:]*:)([^\n]*\n)((?:\s+[^\n]*\n)*)"
    set_match = re.search(set_method_pattern, content, re.MULTILINE)
    if set_match:
        method_signature = set_match.group(1)
        method_body = set_match.group(3)
        
        # Verifică dacă metoda nu este deja thread-safe
        if "with self._lock:" not in method_body:
            # Găsește indentarea
            indent_match = re.search(r"\n(\s+)", method_body)
            indent = indent_match.group(1) if indent_match else "        "
            
            # Creează noua metodă thread-safe
            new_method = f"{method_signature}\n{indent}with self._lock:\n"
            # Re-indentează corpul metodei
            indented_body = "\n".join([f"{indent}    {line}" if line.strip() else line 
                                     for line in method_body.split("\n")])
            new_method += indented_body
            
            content = content.replace(set_match.group(0), new_method)
            print_status("Actualizat metoda set pentru thread-safety", "success")
    
    # Actualizează metoda delete pentru thread-safety
    delete_method_pattern = r"(def delete\(self, key: str\)[^:]*:)([^\n]*\n)((?:\s+[^\n]*\n)*)"
    delete_match = re.search(delete_method_pattern, content, re.MULTILINE)
    if delete_match:
        method_signature = delete_match.group(1)
        method_body = delete_match.group(3)
        
        # Verifică dacă metoda nu este deja thread-safe
        if "with self._lock:" not in method_body:
            # Găsește indentarea
            indent_match = re.search(r"\n(\s+)", method_body)
            indent = indent_match.group(1) if indent_match else "        "
            
            # Creează noua metodă thread-safe
            new_method = f"{method_signature}\n{indent}with self._lock:\n"
            # Re-indentează corpul metodei
            indented_body = "\n".join([f"{indent}    {line}" if line.strip() else line 
                                     for line in method_body.split("\n")])
            new_method += indented_body
            
            content = content.replace(delete_match.group(0), new_method)
            print_status("Actualizat metoda delete pentru thread-safety", "success")
    
    # Actualizează metoda clear pentru thread-safety
    clear_method_pattern = r"(def clear\(self\)[^:]*:)([^\n]*\n)((?:\s+[^\n]*\n)*)"
    clear_match = re.search(clear_method_pattern, content, re.MULTILINE)
    if clear_match:
        method_signature = clear_match.group(1)
        method_body = clear_match.group(3)
        
        # Verifică dacă metoda nu este deja thread-safe
        if "with self._lock:" not in method_body:
            # Găsește indentarea
            indent_match = re.search(r"\n(\s+)", method_body)
            indent = indent_match.group(1) if indent_match else "        "
            
            # Creează noua metodă thread-safe
            new_method = f"{method_signature}\n{indent}with self._lock:\n"
            # Re-indentează corpul metodei
            indented_body = "\n".join([f"{indent}    {line}" if line.strip() else line 
                                     for line in method_body.split("\n")])
            new_method += indented_body
            
            content = content.replace(clear_match.group(0), new_method)
            print_status("Actualizat metoda clear pentru thread-safety", "success")
    
    # Salvează fișierul actualizat
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print_status("Cache manager actualizat pentru thread-safety", "success")
    return True

def optimize_cache_performance():
    """Optimizează performanța cache-ului"""
    print_status("Optimizez performanța cache-ului...", "info")
    
    cache_path = "utils/cache.py"
    if not os.path.exists(cache_path):
        print_status(f"Fișierul {cache_path} nu există!", "error")
        return False
    
    # Citește conținutul
    with open(cache_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Adaugă metodă pentru cleanup eficient
    if "def _cleanup_expired" not in content:
        cleanup_method = """
    def _cleanup_expired(self):
        \"\"\"Curăță eficient intrările expirate din cache\"\"
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            # Identifică cheile expirate
            for key, (value, timestamp, ttl) in self.cache.items():
                if ttl and (current_time - timestamp) > ttl:
                    expired_keys.append(key)
            
            # Șterge cheile expirate
            for key in expired_keys:
                del self.cache[key]
                logger.debug(f\"🗑️ Removed expired cache entry: {key}\")
            
            if expired_keys:
                logger.info(f\"🧹 Cleaned {len(expired_keys)} expired cache entries\")
            
            return len(expired_keys)
"""
        
        # Găsește locul unde să inserez metoda (înainte de ultima metodă)
        last_method_pos = content.rfind("def ")
        if last_method_pos != -1:
            content = content[:last_method_pos] + cleanup_method + "\n\n    " + content[last_method_pos:]
            print_status("Adăugat metodă de cleanup eficient", "success")
    
    # Adaugă metodă pentru statistici cache
    if "def get_cache_stats" not in content:
        stats_method = """
    def get_cache_stats(self):
        \"\"\"Returnează statistici despre cache\"\"
        with self._lock:
            current_time = time.time()
            total_entries = len(self.cache)
            expired_entries = 0
            memory_usage = 0
            
            for key, (value, timestamp, ttl) in self.cache.items():
                if ttl and (current_time - timestamp) > ttl:
                    expired_entries += 1
                
                # Estimează memoria folosită
                try:
                    memory_usage += sys.getsizeof(key) + sys.getsizeof(value)
                except:
                    pass
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'active_entries': total_entries - expired_entries,
                'memory_usage_bytes': memory_usage,
                'memory_usage_mb': round(memory_usage / (1024 * 1024), 2)
            }
"""
        
        # Găsește locul unde să inserez metoda
        last_method_pos = content.rfind("def ")
        if last_method_pos != -1:
            content = content[:last_method_pos] + stats_method + "\n\n    " + content[last_method_pos:]
            print_status("Adăugat metodă pentru statistici cache", "success")
    
    # Adaugă import pentru sys dacă nu există
    if "import sys" not in content:
        import_pattern = r"(import [^\n]+\n)+"
        import_match = re.findall(import_pattern, content)
        if import_match:
            last_import_pos = content.rfind(import_match[-1]) + len(import_match[-1])
            content = content[:last_import_pos] + "import sys\n" + content[last_import_pos:]
        print_status("Adăugat import sys", "success")
    
    # Salvează fișierul actualizat
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def reduce_timeouts():
    """Reduce timeout-urile pentru hosting gratuit"""
    print_status("Reduc timeout-urile pentru hosting gratuit...", "info")
    
    # Actualizează config.py
    config_path = "utils/config.py"
    if os.path.exists(config_path):
        backup_file(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Reduce timeout-ul pentru server
        content = re.sub(r"'timeout':\s*\d+", "'timeout': 15", content)
        
        # Reduce timeout-ul pentru download
        content = re.sub(r"'download_timeout':\s*\d+", "'download_timeout': 30", content)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_status("Timeout-uri reduse în config.py", "success")
    
    # Actualizează downloader.py
    downloader_path = "downloader.py"
    if os.path.exists(downloader_path):
        with open(downloader_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Reduce timeout-urile în yt-dlp options
        content = re.sub(r"'socket_timeout':\s*\d+", "'socket_timeout': 15", content)
        content = re.sub(r"'http_chunk_size':\s*\d+", "'http_chunk_size': 1048576", content)  # 1MB chunks
        
        with open(downloader_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_status("Timeout-uri reduse în downloader.py", "success")
    
    return True

def integrate_rate_limiter():
    """Integrează rate limiter-ul în bot"""
    print_status("Integrez rate limiter-ul în bot...", "info")
    
    bot_path = "bot.py"
    if not os.path.exists(bot_path):
        print_status(f"Fișierul {bot_path} nu există!", "error")
        return False
    
    backup_file(bot_path)
    
    # Citește conținutul
    with open(bot_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Adaugă import pentru rate limiter
    if "from utils.rate_limiter import rate_limiter" not in content:
        import_pattern = r"(from utils\.[^\n]+\n)+"
        import_match = re.findall(import_pattern, content)
        if import_match:
            last_import_pos = content.rfind(import_match[-1]) + len(import_match[-1])
            content = content[:last_import_pos] + "from utils.rate_limiter import rate_limiter\n" + content[last_import_pos:]
        else:
            # Găsește primul import și adaugă după el
            first_import = re.search(r"import [^\n]+\n", content)
            if first_import:
                content = content[:first_import.end()] + "from utils.rate_limiter import rate_limiter\n" + content[first_import.end():]
        
        print_status("Adăugat import pentru rate limiter", "success")
    
    # Adaugă verificare rate limit în handle_message
    handle_message_pattern = r"(async def handle_message\([^)]+\):[^\n]*\n)(\s+)"
    handle_message_match = re.search(handle_message_pattern, content)
    if handle_message_match and "rate_limiter.is_allowed" not in content:
        indent = handle_message_match.group(2)
        rate_limit_check = f"""{indent}# Verifică rate limiting
{indent}user_id = str(update.effective_user.id)
{indent}if not rate_limiter.is_allowed(user_id):
{indent}    remaining_time = rate_limiter.get_reset_time(user_id)
{indent}    await update.message.reply_text(
{indent}        f"⏳ Prea multe cereri! Încearcă din nou în {{int(remaining_time)}} secunde.",
{indent}        reply_markup=get_main_menu_keyboard()
{indent}    )
{indent}    return
\n"""
        
        content = content[:handle_message_match.end()] + rate_limit_check + content[handle_message_match.end():]
        print_status("Adăugat verificare rate limit în handle_message", "success")
    
    # Salvează fișierul actualizat
    with open(bot_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def verify_phase3_changes():
    """Verifică că modificările din faza 3 au fost aplicate"""
    print_status("Verific modificările din faza 3...", "info")
    
    issues = []
    
    # Verifică cache manager
    cache_path = "utils/cache.py"
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_content = f.read()
        
        if "import threading" not in cache_content:
            issues.append("Threading import nu a fost adăugat în cache manager")
        
        if "self._lock = threading.Lock()" not in cache_content:
            issues.append("Lock nu a fost adăugat în cache manager")
        
        if "with self._lock:" not in cache_content:
            issues.append("Thread-safety nu a fost implementat în cache manager")
        
        if "def _cleanup_expired" not in cache_content:
            issues.append("Metoda de cleanup nu a fost adăugată")
    else:
        issues.append("Cache manager nu există")
    
    # Verifică bot.py
    bot_path = "bot.py"
    if os.path.exists(bot_path):
        with open(bot_path, 'r', encoding='utf-8') as f:
            bot_content = f.read()
        
        if "from utils.rate_limiter import rate_limiter" not in bot_content:
            issues.append("Rate limiter import nu a fost adăugat în bot")
        
        if "rate_limiter.is_allowed" not in bot_content:
            issues.append("Rate limiting nu a fost implementat în bot")
    
    # Verifică rate limiter
    if not os.path.exists("utils/rate_limiter.py"):
        issues.append("Rate limiter nu există")
    
    if issues:
        print_status("Probleme găsite:", "warning")
        for issue in issues:
            print_status(f"  - {issue}", "error")
        return False
    else:
        print_status("Toate modificările din faza 3 au fost aplicate!", "success")
        return True

def main():
    """Funcția principală de implementare"""
    print_status("🛠️ ÎNCEPE IMPLEMENTAREA FAZEI 3 - Optimizarea Cache-ului", "info")
    print_status("="*60, "info")
    
    # Verifică că suntem în directorul corect
    if not os.path.exists("utils/cache.py"):
        print_status("Nu sunt în directorul corect sau cache nu există!", "error")
        return False
    
    success_count = 0
    total_tasks = 5
    
    # 1. Actualizează cache manager pentru thread-safety
    if update_cache_manager():
        success_count += 1
    
    # 2. Optimizează performanța cache-ului
    if optimize_cache_performance():
        success_count += 1
    
    # 3. Reduce timeout-urile
    if reduce_timeouts():
        success_count += 1
    
    # 4. Integrează rate limiter-ul
    if integrate_rate_limiter():
        success_count += 1
    
    # 5. Verifică modificările
    if verify_phase3_changes():
        success_count += 1
    
    print_status("="*60, "info")
    print_status(f"Implementare completă: {success_count}/{total_tasks} task-uri reușite", "info")
    
    if success_count == total_tasks:
        print_status("✅ FAZA 3 IMPLEMENTATĂ CU SUCCES!", "success")
        print_status("Următorul pas: Testare și validare finală", "info")
        return True
    else:
        print_status("❌ Unele modificări nu au fost aplicate corect", "error")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)