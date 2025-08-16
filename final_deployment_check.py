#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificare finală înainte de deployment pe Render
Confirmă că toate fișierele și configurațiile sunt corecte
"""

import os
import sys

def check_critical_files():
    """Verifică fișierele critice pentru deployment"""
    print("🔍 VERIFICARE FIȘIERE CRITICE PENTRU RENDER:")
    
    critical_files = {
        'Dockerfile': 'Configurație Docker pentru Render',
        'app.py': 'Aplicația Flask principală',
        'requirements.txt': 'Dependențe Python',
        'Procfile': 'Configurație Render (backup)',
        'runtime.txt': 'Versiunea Python',
        '.dockerignore': 'Excluderi Docker'
    }
    
    all_present = True
    for file, description in critical_files.items():
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {description}: {file} ({size} bytes)")
        else:
            print(f"❌ {description}: {file} - LIPSEȘTE!")
            all_present = False
    
    return all_present

def check_dockerfile_content():
    """Verifică conținutul Dockerfile"""
    print("\n🐳 VERIFICARE DOCKERFILE:")
    
    if not os.path.exists('Dockerfile'):
        print("❌ Dockerfile lipsește!")
        return False
    
    with open('Dockerfile', 'r') as f:
        content = f.read()
    
    required_elements = [
        'FROM python:3.11',
        'WORKDIR /app',
        'COPY requirements.txt',
        'RUN pip install',
        'COPY . .',
        'EXPOSE 10000',
        'CMD ["python", "app.py"]'
    ]
    
    missing = []
    for element in required_elements:
        if element not in content:
            missing.append(element)
    
    if not missing:
        print("✅ Dockerfile conține toate elementele necesare")
        return True
    else:
        print(f"❌ Dockerfile lipsește: {', '.join(missing)}")
        return False

def check_requirements():
    """Verifică requirements.txt"""
    print("\n📦 VERIFICARE REQUIREMENTS:")
    
    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt lipsește!")
        return False
    
    with open('requirements.txt', 'r') as f:
        content = f.read()
    
    required_packages = [
        'flask',
        'python-telegram-bot',
        'yt-dlp',
        'requests',
        'psutil'
    ]
    
    missing = []
    for package in required_packages:
        if package not in content.lower():
            missing.append(package)
    
    if not missing:
        print("✅ Toate pachetele necesare sunt în requirements.txt")
        return True
    else:
        print(f"❌ Pachete lipsă din requirements.txt: {', '.join(missing)}")
        return False

def check_app_configuration():
    """Verifică configurația app.py"""
    print("\n⚙️ VERIFICARE CONFIGURAȚIE APP:")
    
    if not os.path.exists('app.py'):
        print("❌ app.py lipsește!")
        return False
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_configs = [
        "port = int(os.environ.get('PORT'",
        "app.run(host='0.0.0.0', port=port",
        "@app.route('/health'",
        "@app.route('/metrics'",
        "TELEGRAM_BOT_TOKEN"
    ]
    
    missing = []
    for config in required_configs:
        if config not in content:
            missing.append(config)
    
    if not missing:
        print("✅ app.py este configurat corect pentru Render")
        return True
    else:
        print(f"❌ Configurații lipsă din app.py: {', '.join(missing)}")
        return False

def check_git_status():
    """Verifică statusul Git"""
    print("\n📋 VERIFICARE GIT STATUS:")
    
    if not os.path.exists('.git'):
        print("❌ Repository Git nu este inițializat!")
        return False
    
    # Verifică dacă avem modificări uncommitted
    import subprocess
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            if result.stdout.strip():
                print("⚠️  Există modificări uncommitted:")
                print(result.stdout)
                return False
            else:
                print("✅ Toate modificările sunt committed")
                return True
        else:
            print(f"❌ Eroare Git: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Nu pot verifica statusul Git: {e}")
        return False

def main():
    """Verificare finală pentru deployment"""
    print("🚀 VERIFICARE FINALĂ DEPLOYMENT RENDER")
    print("=" * 50)
    
    checks = [
        ("Fișiere critice", check_critical_files),
        ("Dockerfile", check_dockerfile_content),
        ("Requirements", check_requirements),
        ("Configurație App", check_app_configuration),
        ("Git Status", check_git_status)
    ]
    
    all_passed = True
    results = {}
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results[check_name] = result
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ Eroare la {check_name}: {e}")
            results[check_name] = False
            all_passed = False
    
    # Rezultate finale
    print("\n" + "=" * 50)
    print("📊 REZULTATE VERIFICARE:")
    
    for check_name, result in results.items():
        status = "✅ TRECUT" if result else "❌ EȘUAT"
        print(f"  {check_name}: {status}")
    
    passed_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    
    print(f"\n📈 SCOR: {passed_count}/{total_count} verificări trecute")
    
    if all_passed:
        print("\n🎉 TOATE VERIFICĂRILE AU TRECUT!")
        print("\n🚀 DEPLOYMENT READY:")
        print("  1. Codul este push-at pe GitHub")
        print("  2. Dockerfile este configurat corect")
        print("  3. Toate dependențele sunt specificate")
        print("  4. Configurația pentru Render este completă")
        
        print("\n📋 URMĂTORII PAȘI:")
        print("  1. Mergi pe dashboard.render.com")
        print("  2. Serviciul ar trebui să facă redeploy automat")
        print("  3. Urmărește logs-urile pentru progres")
        print("  4. Testează endpoint-urile după deployment")
        
        print("\n🔗 LINK-URI IMPORTANTE:")
        print("  • GitHub: https://github.com/matrix01mindset/Downloader-Bot-Telegram")
        print("  • Render: https://dashboard.render.com")
        
        return True
        
    else:
        print(f"\n❌ {total_count - passed_count} VERIFICĂRI AU EȘUAT!")
        print("\n💡 Rezolvă problemele de mai sus înainte de deployment.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Verificare întreruptă")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Eroare neașteptată: {e}")
        sys.exit(1)