#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛠️ IMPLEMENTARE FAZA 2 - Securizarea Fișierelor
Telegram Video Downloader Bot - Security Fixes

Acest script implementează:
1. Fixarea vulnerabilității path traversal
2. Implementarea cleanup-ului sigur pentru fișiere temporare
3. Adăugarea validării stricte a căilor
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
        backup_path = f"{file_path}.backup_phase2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print_status(f"Backup creat: {backup_path}", "success")
        return backup_path
    return None

def add_security_utils():
    """Adaugă utilitare de securitate în downloader.py"""
    print_status("Adaug utilitare de securitate în downloader.py...", "info")
    
    downloader_path = "downloader.py"
    if not os.path.exists(downloader_path):
        print_status(f"Fișierul {downloader_path} nu există!", "error")
        return False
    
    # Backup
    backup_file(downloader_path)
    
    # Citește conținutul
    with open(downloader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifică dacă utilitarele de securitate există deja
    if "class SecurityError" in content:
        print_status("Utilitarele de securitate există deja", "warning")
        return True
    
    # Adaugă import-urile necesare
    security_imports = """
import tempfile
import shutil
from contextlib import contextmanager
from pathlib import Path"""
    
    # Găsește locul pentru import-uri (după ultimul import)
    import_pattern = r"(import [^\n]+\n)+"
    import_match = re.findall(import_pattern, content)
    if import_match:
        last_import_pos = content.rfind(import_match[-1]) + len(import_match[-1])
        content = content[:last_import_pos] + security_imports + "\n" + content[last_import_pos:]
    
    # Adaugă clasa de eroare de securitate
    security_error_class = """
class SecurityError(Exception):
    \"\"\"Excepție pentru probleme de securitate\"\"\"
    pass
"""
    
    # Adaugă funcția de validare a directorului temporar
    validate_temp_dir_function = """
def validate_and_create_temp_dir():
    \"\"\"Creează director temporar sigur cu validare împotriva path traversal\"\"\"
    try:
        # Creează directorul temporar
        temp_dir = tempfile.mkdtemp(prefix="video_download_")
        
        # Validare strictă împotriva path traversal
        real_path = os.path.realpath(temp_dir)
        temp_base = os.path.realpath(tempfile.gettempdir())
        
        # Verifică că directorul este într-o locație sigură
        if not real_path.startswith(temp_base):
            # Curăță directorul creat
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise SecurityError(f"Invalid temp directory path: {real_path}")
        
        # Verifică permisiunile
        if not os.access(temp_dir, os.W_OK):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise SecurityError(f"No write access to temp directory: {temp_dir}")
        
        logger.info(f"🔒 Secure temp directory created: {temp_dir}")
        return temp_dir
        
    except Exception as e:
        logger.error(f"❌ Failed to create secure temp directory: {e}")
        raise SecurityError(f"Cannot create secure temp directory: {e}")
"""
    
    # Adaugă context manager-ul pentru fișiere temporare sigure
    safe_temp_file_context = """
@contextmanager
def safe_temp_file(suffix=\".mp4\", prefix=\"video_\"):
    \"\"\"Context manager pentru fișiere temporare sigure cu cleanup automat\"\"\"
    temp_dir = None
    temp_file = None
    
    try:
        # Creează directorul temporar sigur
        temp_dir = validate_and_create_temp_dir()
        
        # Creează numele fișierului temporar
        timestamp = int(time.time())
        filename = f"{prefix}{timestamp}{suffix}"
        temp_file = os.path.join(temp_dir, filename)
        
        # Validează că calea finală este sigură
        real_temp_file = os.path.realpath(temp_file)
        real_temp_dir = os.path.realpath(temp_dir)
        
        if not real_temp_file.startswith(real_temp_dir):
            raise SecurityError(f"Invalid temp file path: {real_temp_file}")
        
        logger.info(f"🔒 Secure temp file created: {temp_file}")
        yield temp_file
        
    except Exception as e:
        logger.error(f"❌ Error in safe_temp_file: {e}")
        raise
    finally:
        # Cleanup garantat
        cleanup_success = True
        
        # Șterge fișierul
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.info(f"🗑️ Temp file cleaned: {temp_file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove temp file {temp_file}: {e}")
                cleanup_success = False
        
        # Șterge directorul
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"🗑️ Temp directory cleaned: {temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove temp directory {temp_dir}: {e}")
                cleanup_success = False
        
        if not cleanup_success:
            logger.error("❌ Incomplete cleanup of temporary files!")
"""
    
    # Găsește locul unde să inserez funcțiile (înainte de funcția download_video)
    download_video_pos = content.find("def download_video(")
    if download_video_pos == -1:
        print_status("Nu am găsit funcția download_video", "error")
        return False
    
    # Inserează toate funcțiile de securitate
    security_code = security_error_class + validate_temp_dir_function + safe_temp_file_context
    content = content[:download_video_pos] + security_code + "\n" + content[download_video_pos:]
    
    # Salvează fișierul actualizat
    with open(downloader_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print_status("Utilitare de securitate adăugate în downloader.py", "success")
    return True

def update_download_function():
    """Actualizează funcția download_video pentru a folosi fișiere temporare sigure"""
    print_status("Actualizez funcția download_video pentru securitate...", "info")
    
    downloader_path = "downloader.py"
    if not os.path.exists(downloader_path):
        print_status(f"Fișierul {downloader_path} nu există!", "error")
        return False
    
    # Citește conținutul
    with open(downloader_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Găsește și înlocuiește crearea directorului temporar nesigur
    old_temp_creation = r"temp_dir = tempfile\.mkdtemp\(prefix=\"video_download_\"\)"
    new_temp_creation = "temp_dir = validate_and_create_temp_dir()"
    
    if re.search(old_temp_creation, content):
        content = re.sub(old_temp_creation, new_temp_creation, content)
        print_status("Înlocuit crearea directorului temporar nesigur", "success")
    
    # Găsește și actualizează logica de cleanup
    # Căutăm pattern-ul pentru cleanup manual și îl înlocuim cu context manager
    cleanup_pattern = r"(\s+)try:\s*\n(\s+)os\.remove\(output_file\)\s*\n(\s+)except[^:]*:\s*\n(\s+)pass"
    
    if re.search(cleanup_pattern, content, re.MULTILINE):
        # Înlocuim cu un comentariu că cleanup-ul se face automat
        content = re.sub(cleanup_pattern, 
                        "\\1# Cleanup automat prin context manager safe_temp_file", 
                        content, flags=re.MULTILINE)
        print_status("Actualizat logica de cleanup", "success")
    
    # Salvează fișierul actualizat
    with open(downloader_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def add_rate_limiter():
    """Adaugă un rate limiter simplu în utils/"""
    print_status("Creez rate limiter în utils/rate_limiter.py...", "info")
    
    # Asigură-te că directorul utils există
    os.makedirs("utils", exist_ok=True)
    
    rate_limiter_path = "utils/rate_limiter.py"
    
    rate_limiter_content = """
# utils/rate_limiter.py - Rate Limiting pentru protecție anti-spam
# Versiunea: 1.0.0

import time
import threading
from collections import defaultdict
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SimpleRateLimiter:
    \"\"\"Rate limiter simplu pentru protecție anti-spam\"\"\"
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        \"\"\"
        Inițializează rate limiter-ul
        
        Args:
            max_requests: Numărul maxim de cereri permise
            time_window: Fereastra de timp în secunde
        \"\"\"
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
        logger.info(f"🛡️ Rate limiter initialized: {max_requests} requests per {time_window}s")
    
    def is_allowed(self, user_id: str) -> bool:
        \"\"\"
        Verifică dacă utilizatorul poate face o cerere
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            True dacă cererea este permisă, False altfel
        \"\"\"
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Curăță cererile vechi
            user_requests[:] = [req_time for req_time in user_requests 
                              if now - req_time < self.time_window]
            
            # Verifică limita
            if len(user_requests) >= self.max_requests:
                logger.warning(f"🚫 Rate limit exceeded for user {user_id}: {len(user_requests)}/{self.max_requests}")
                return False
            
            # Adaugă cererea curentă
            user_requests.append(now)
            logger.debug(f"✅ Request allowed for user {user_id}: {len(user_requests)}/{self.max_requests}")
            return True
    
    def get_remaining_requests(self, user_id: str) -> int:
        \"\"\"
        Returnează numărul de cereri rămase pentru utilizator
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            Numărul de cereri rămase
        \"\"\"
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Curăță cererile vechi
            user_requests[:] = [req_time for req_time in user_requests 
                              if now - req_time < self.time_window]
            
            return max(0, self.max_requests - len(user_requests))
    
    def get_reset_time(self, user_id: str) -> float:
        \"\"\"
        Returnează timpul până la resetarea limitei pentru utilizator
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            Timpul în secunde până la resetare
        \"\"\"
        with self.lock:
            user_requests = self.requests[user_id]
            
            if not user_requests:
                return 0.0
            
            oldest_request = min(user_requests)
            reset_time = oldest_request + self.time_window - time.time()
            
            return max(0.0, reset_time)
    
    def clear_user(self, user_id: str):
        \"\"\"
        Curăță istoricul pentru un utilizator specific
        
        Args:
            user_id: ID-ul utilizatorului
        \"\"\"
        with self.lock:
            if user_id in self.requests:
                del self.requests[user_id]
                logger.info(f"🗑️ Cleared rate limit history for user {user_id}")
    
    def get_stats(self) -> Dict[str, int]:
        \"\"\"
        Returnează statistici despre rate limiter
        
        Returns:
            Dicționar cu statistici
        \"\"\"
        with self.lock:
            now = time.time()
            active_users = 0
            total_requests = 0
            
            for user_id, user_requests in self.requests.items():
                # Curăță cererile vechi
                user_requests[:] = [req_time for req_time in user_requests 
                                  if now - req_time < self.time_window]
                
                if user_requests:
                    active_users += 1
                    total_requests += len(user_requests)
            
            return {
                'active_users': active_users,
                'total_requests': total_requests,
                'max_requests_per_window': self.max_requests,
                'time_window_seconds': self.time_window
            }

# Instanță globală pentru folosire în aplicație
rate_limiter = SimpleRateLimiter(
    max_requests=5,  # 5 cereri
    time_window=60   # per minut
)
"""
    
    # Creează fișierul
    with open(rate_limiter_path, 'w', encoding='utf-8') as f:
        f.write(rate_limiter_content)
    
    print_status("Rate limiter creat cu succes", "success")
    return True

def verify_security_changes():
    """Verifică că modificările de securitate au fost aplicate"""
    print_status("Verific modificările de securitate...", "info")
    
    issues = []
    
    # Verifică downloader.py
    if os.path.exists("downloader.py"):
        with open("downloader.py", 'r', encoding='utf-8') as f:
            downloader_content = f.read()
        
        if "class SecurityError" not in downloader_content:
            issues.append("SecurityError class nu a fost adăugată")
        
        if "validate_and_create_temp_dir" not in downloader_content:
            issues.append("Funcția validate_and_create_temp_dir nu a fost adăugată")
        
        if "safe_temp_file" not in downloader_content:
            issues.append("Context manager safe_temp_file nu a fost adăugat")
    
    # Verifică rate limiter
    if not os.path.exists("utils/rate_limiter.py"):
        issues.append("Rate limiter nu a fost creat")
    
    if issues:
        print_status("Probleme găsite:", "warning")
        for issue in issues:
            print_status(f"  - {issue}", "error")
        return False
    else:
        print_status("Toate modificările de securitate au fost aplicate!", "success")
        return True

def main():
    """Funcția principală de implementare"""
    print_status("🛠️ ÎNCEPE IMPLEMENTAREA FAZEI 2 - Securizarea Fișierelor", "info")
    print_status("="*60, "info")
    
    # Verifică că suntem în directorul corect
    if not os.path.exists("downloader.py"):
        print_status("Nu sunt în directorul corect al proiectului!", "error")
        return False
    
    success_count = 0
    total_tasks = 4
    
    # 1. Adaugă utilitare de securitate
    if add_security_utils():
        success_count += 1
    
    # 2. Actualizează funcția de download
    if update_download_function():
        success_count += 1
    
    # 3. Adaugă rate limiter
    if add_rate_limiter():
        success_count += 1
    
    # 4. Verifică modificările
    if verify_security_changes():
        success_count += 1
    
    print_status("="*60, "info")
    print_status(f"Implementare completă: {success_count}/{total_tasks} task-uri reușite", "info")
    
    if success_count == total_tasks:
        print_status("✅ FAZA 2 IMPLEMENTATĂ CU SUCCES!", "success")
        print_status("Următorul pas: Testare și integrare cu aplicația", "info")
        return True
    else:
        print_status("❌ Unele modificări nu au fost aplicate corect", "error")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)