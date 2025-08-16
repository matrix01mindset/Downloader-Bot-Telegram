#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificare că toate fișierele sunt gata pentru deployment
Verifică integritatea și completitudinea proiectului
"""

import os
import sys
import json
import importlib.util

def check_file_exists(filepath, description):
    """Verifică că un fișier există"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✅ {description}: {filepath} ({size} bytes)")
        return True
    else:
        print(f"❌ {description}: {filepath} - LIPSEȘTE!")
        return False

def check_file_content(filepath, required_content, description):
    """Verifică că un fișier conține conținutul necesar"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_content = []
        for item in required_content:
            if item not in content:
                missing_content.append(item)
        
        if not missing_content:
            print(f"✅ {description}: Conținut complet")
            return True
        else:
            print(f"❌ {description}: Lipsește - {', '.join(missing_content)}")
            return False
            
    except Exception as e:
        print(f"❌ {description}: Eroare la citire - {e}")
        return False

def check_python_syntax(filepath, description):
    """Verifică sintaxa Python a unui fișier"""
    try:
        spec = importlib.util.spec_from_file_location("module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✅ {description}: Sintaxă Python validă")
        return True
    except Exception as e:
        print(f"❌ {description}: Eroare sintaxă - {e}")
        return False

def main():
    """Verifică că proiectul este gata pentru deployment"""
    print("🔍 VERIFICARE DEPLOYMENT READY")
    print("=" * 50)
    
    all_checks_passed = True
    
    # 1. Verifică fișierele principale
    print("\n📁 VERIFICARE FIȘIERE PRINCIPALE:")
    required_files = [
        ("app.py", "Server Flask principal"),
        ("bot.py", "Bot Telegram pentru rulare locală"),
        ("downloader.py", "Logica de descărcare"),
        ("requirements.txt", "Dependențe Python"),
        ("Procfile", "Configurație Render"),
        ("runtime.txt", "Versiunea Python"),
        ("README.md", "Documentație principală"),
        (".gitignore", "Excluderi Git")
    ]
    
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # 2. Verifică fișierele de deployment
    print("\n🚀 VERIFICARE FIȘIERE DEPLOYMENT:")
    deployment_files = [
        ("RENDER_DEPLOYMENT.md", "Ghid deployment Render"),
        ("GITHUB_DEPLOYMENT.md", "Ghid deployment GitHub"),
        ("deploy_to_github.py", "Script automat deployment"),
        ("verify_deployment.py", "Script verificare deployment")
    ]
    
    for filepath, description in deployment_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # 3. Verifică fișierele de teste
    print("\n🧪 VERIFICARE FIȘIERE TESTE:")
    test_files = [
        ("test_comprehensive.py", "Suite teste comprehensivă"),
        ("test_render_compatibility.py", "Teste compatibilitate Render")
    ]
    
    for filepath, description in test_files:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # 4. Verifică conținutul fișierelor critice
    print("\n🔧 VERIFICARE CONȚINUT FIȘIERE:")
    
    # Verifică app.py
    app_required = [
        "class BotMetrics",
        "class ErrorHandler", 
        "def create_safe_caption",
        "def is_rate_limited",
        "/metrics",
        "cleanup_temp_files"
    ]
    if os.path.exists("app.py"):
        if not check_file_content("app.py", app_required, "app.py - funcționalități"):
            all_checks_passed = False
    
    # Verifică downloader.py
    downloader_required = [
        "def get_platform_from_url",
        "def get_platform_specific_config",
        "def try_facebook_fallback",
        "def is_supported_url"
    ]
    if os.path.exists("downloader.py"):
        if not check_file_content("downloader.py", downloader_required, "downloader.py - funcționalități"):
            all_checks_passed = False
    
    # Verifică requirements.txt
    requirements_required = [
        "flask>=2.0.0",
        "python-telegram-bot>=21.0",
        "yt-dlp",
        "requests>=2.25.0",
        "psutil>=5.8.0"
    ]
    if os.path.exists("requirements.txt"):
        if not check_file_content("requirements.txt", requirements_required, "requirements.txt - dependențe"):
            all_checks_passed = False
    
    # 5. Verifică sintaxa Python
    print("\n🐍 VERIFICARE SINTAXĂ PYTHON:")
    python_files = ["app.py", "bot.py", "downloader.py"]
    
    for filepath in python_files:
        if os.path.exists(filepath):
            if not check_python_syntax(filepath, f"Sintaxă {filepath}"):
                all_checks_passed = False
    
    # 6. Verifică configurația Git
    print("\n📋 VERIFICARE CONFIGURAȚIE GIT:")
    if os.path.exists(".git"):
        print("✅ Repository Git inițializat")
    else:
        print("⚠️  Repository Git nu este inițializat (se va inițializa automat)")
    
    if os.path.exists(".gitignore"):
        print("✅ .gitignore prezent")
    else:
        print("❌ .gitignore lipsește")
        all_checks_passed = False
    
    # 7. Verifică mărimea totală a proiectului
    print("\n📊 VERIFICARE MĂRIME PROIECT:")
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk("."):
        # Exclude .git și __pycache__
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.kiro']]
        
        for file in files:
            if not file.endswith(('.pyc', '.log', '.tmp')):
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath)
                    total_size += size
                    file_count += 1
                except:
                    pass
    
    total_mb = total_size / (1024 * 1024)
    print(f"📁 Total fișiere: {file_count}")
    print(f"📦 Mărime totală: {total_mb:.2f} MB")
    
    if total_mb > 100:
        print("⚠️  Proiectul este mare (>100MB) - verifică că nu ai fișiere video temporare")
    else:
        print("✅ Mărimea proiectului este OK pentru GitHub")
    
    # Rezultat final
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 PROIECTUL ESTE GATA PENTRU DEPLOYMENT!")
        print("\n📋 Următorii pași:")
        print("  1. Rulează: python deploy_to_github.py")
        print("  2. Configurează Render să se conecteze la GitHub")
        print("  3. Setează Environment Variables în Render")
        print("  4. Testează deployment-ul")
        
        print("\n🔗 Link-uri importante:")
        print("  • GitHub: https://github.com/matrix01mindset/Downloader-Bot-Telegram")
        print("  • Render: https://dashboard.render.com")
        
        return True
    else:
        print("❌ PROIECTUL NU ESTE GATA PENTRU DEPLOYMENT!")
        print("\n💡 Rezolvă problemele de mai sus înainte de deployment.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Eroare neașteptată: {e}")
        sys.exit(1)