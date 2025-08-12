#!/usr/bin/env python3
"""
🧹 SCRIPT CURĂȚARE SECURITATE - Telegram Video Downloader Bot
Versiunea: 1.0.0
Data: 2025-01-12

Curăță fișierele vulnerabile și optimizează structura proiectului.
"""

import os
import shutil
import sys
from pathlib import Path
import logging

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_vulnerable_files():
    """Elimină fișierele cu vulnerabilități de securitate."""
    print("🔥 Eliminare fișiere vulnerabile...")
    
    vulnerable_files = [
        'RENDER_SERVICE_SETUP.txt',
        'RENDER_UPDATE_INSTRUCTIONS.txt',
        'monitor_bot.py.bak',
        'setup_webhook.py.bak',
        'debug_webhook_url.py.bak'
    ]
    
    removed_count = 0
    
    for file_path in vulnerable_files:
        if Path(file_path).exists():
            try:
                os.remove(file_path)
                print(f"✅ Eliminat: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Eroare la eliminarea {file_path}: {e}")
        else:
            print(f"ℹ️  Nu există: {file_path}")
    
    print(f"📊 Total fișiere eliminate: {removed_count}")
    return removed_count > 0

def clean_temp_directories():
    """Curăță directoarele temporare."""
    print("\n🗂️ Curățare directoare temporare...")
    
    temp_dirs = [
        'temp_downloads',
        'tmp',
        'temp',
        'cache',
        '__pycache__',
        '.pytest_cache',
        'logs'
    ]
    
    cleaned_count = 0
    
    for dir_path in temp_dirs:
        if Path(dir_path).exists():
            try:
                if Path(dir_path).is_dir():
                    shutil.rmtree(dir_path)
                    print(f"✅ Eliminat director: {dir_path}")
                    cleaned_count += 1
            except Exception as e:
                print(f"❌ Eroare la eliminarea {dir_path}: {e}")
        else:
            print(f"ℹ️  Nu există: {dir_path}")
    
    print(f"📊 Total directoare curățate: {cleaned_count}")
    return cleaned_count > 0

def clean_media_files():
    """Elimină fișierele media temporare."""
    print("\n🎬 Curățare fișiere media temporare...")
    
    media_extensions = [
        '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv',
        '.wmv', '.m4v', '.3gp', '.mp3', '.wav', '.aac',
        '.ogg', '.flac'
    ]
    
    cleaned_count = 0
    current_dir = Path('.')
    
    for file_path in current_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in media_extensions:
            try:
                file_path.unlink()
                print(f"✅ Eliminat media: {file_path}")
                cleaned_count += 1
            except Exception as e:
                print(f"❌ Eroare la eliminarea {file_path}: {e}")
    
    print(f"📊 Total fișiere media eliminate: {cleaned_count}")
    return cleaned_count > 0

def clean_log_files():
    """Elimină fișierele de log vechi."""
    print("\n📋 Curățare fișiere log...")
    
    log_patterns = ['*.log', '*.log.*']
    cleaned_count = 0
    current_dir = Path('.')
    
    for pattern in log_patterns:
        for file_path in current_dir.rglob(pattern):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    print(f"✅ Eliminat log: {file_path}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"❌ Eroare la eliminarea {file_path}: {e}")
    
    print(f"📊 Total fișiere log eliminate: {cleaned_count}")
    return cleaned_count > 0

def clean_backup_files():
    """Elimină fișierele de backup."""
    print("\n💾 Curățare fișiere backup...")
    
    backup_extensions = ['.bak', '.backup', '.old', '.orig', '.tmp', '.temp']
    cleaned_count = 0
    current_dir = Path('.')
    
    for file_path in current_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in backup_extensions:
            try:
                file_path.unlink()
                print(f"✅ Eliminat backup: {file_path}")
                cleaned_count += 1
            except Exception as e:
                print(f"❌ Eroare la eliminarea {file_path}: {e}")
    
    print(f"📊 Total fișiere backup eliminate: {cleaned_count}")
    return cleaned_count > 0

def create_necessary_directories():
    """Creează directoarele necesare cu permisiuni corecte."""
    print("\n📁 Creare directoare necesare...")
    
    necessary_dirs = [
        'temp_downloads',
        'logs'
    ]
    
    created_count = 0
    
    for dir_path in necessary_dirs:
        try:
            Path(dir_path).mkdir(exist_ok=True)
            print(f"✅ Director creat/verificat: {dir_path}")
            created_count += 1
        except Exception as e:
            print(f"❌ Eroare la crearea {dir_path}: {e}")
    
    print(f"📊 Total directoare create/verificate: {created_count}")
    return created_count > 0

def verify_security_files():
    """Verifică că fișierele de securitate sunt în regulă."""
    print("\n🔐 Verificare fișiere securitate...")
    
    security_checks = []
    
    # Verifică .env.example
    if Path('.env.example').exists():
        print("✅ .env.example există")
        security_checks.append(True)
    else:
        print("❌ .env.example lipsește")
        security_checks.append(False)
    
    # Verifică .gitignore
    if Path('.gitignore').exists():
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
            if '.env' in gitignore_content:
                print("✅ .env este în .gitignore")
                security_checks.append(True)
            else:
                print("❌ .env nu este în .gitignore")
                security_checks.append(False)
    else:
        print("❌ .gitignore lipsește")
        security_checks.append(False)
    
    # Verifică că nu există .env în repository
    if Path('.env').exists():
        print("⚠️  .env există - asigură-te că nu este în git")
        security_checks.append(False)
    else:
        print("✅ .env nu există în repository")
        security_checks.append(True)
    
    return all(security_checks)

def scan_for_hardcoded_secrets():
    """Scanează pentru secrete hardcodate în cod."""
    print("\n🔍 Scanare secrete hardcodate...")
    
    python_files = list(Path('.').rglob('*.py'))
    issues_found = []
    
    dangerous_patterns = [
        'BOT_TOKEN = "',
        'TOKEN = "',
        'API_KEY = "',
        'SECRET = "',
        'PASSWORD = "',
        '8253089686:',  # Token-ul specific găsit anterior
    ]
    
    for file_path in python_files:
        if file_path.name in ['cleanup_security.py', 'test_local.py']:
            continue  # Skip fișierele de utilitate
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in dangerous_patterns:
                    if pattern in content:
                        issues_found.append(f"{file_path}: {pattern}")
                        print(f"⚠️  Posibil secret în {file_path}: {pattern}")
        except Exception as e:
            print(f"❌ Eroare la scanarea {file_path}: {e}")
    
    if not issues_found:
        print("✅ Nu au fost găsite secrete hardcodate")
        return True
    else:
        print(f"❌ Găsite {len(issues_found)} probleme potențiale")
        return False

def main():
    """Funcția principală de curățare."""
    print("🧹 CURĂȚARE SECURITATE - Telegram Video Downloader Bot")
    print("=" * 70)
    
    operations = [
        ("Eliminare fișiere vulnerabile", remove_vulnerable_files),
        ("Curățare directoare temporare", clean_temp_directories),
        ("Curățare fișiere media", clean_media_files),
        ("Curățare fișiere log", clean_log_files),
        ("Curățare fișiere backup", clean_backup_files),
        ("Creare directoare necesare", create_necessary_directories),
        ("Verificare fișiere securitate", verify_security_files),
        ("Scanare secrete hardcodate", scan_for_hardcoded_secrets)
    ]
    
    results = []
    
    for operation_name, operation_func in operations:
        try:
            result = operation_func()
            results.append((operation_name, result))
        except Exception as e:
            print(f"❌ Eroare în operația '{operation_name}': {e}")
            results.append((operation_name, False))
    
    # Sumar rezultate
    print("\n" + "=" * 70)
    print("📊 SUMAR CURĂȚARE:")
    
    all_passed = True
    for operation_name, result in results:
        status = "✅ SUCCES" if result else "❌ PROBLEME"
        print(f"  {operation_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 CURĂȚAREA A FOST COMPLETĂ! Proiectul este securizat.")
        print("\n📋 Pași următori:")
        print("1. Verifică că .env este configurat corect")
        print("2. Rulează python test_local.py pentru verificare")
        print("3. Commit modificările și deploy pe Render")
    else:
        print("⚠️ UNELE OPERAȚII AU EȘUAT! Verifică problemele de mai sus.")
        print("\n💡 Rezolvă problemele înainte de deploy.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)