#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script automat pentru deployment pe GitHub
Automatizează procesul de commit și push cu mesaje descriptive
"""

import os
import subprocess
import sys
import time
from datetime import datetime

def run_command(command, cwd=None):
    """Rulează o comandă și returnează rezultatul"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd,
            capture_output=True, 
            text=True, 
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_git_status():
    """Verifică statusul Git"""
    print("🔍 Verificare status Git...")
    
    success, stdout, stderr = run_command("git status --porcelain")
    if not success:
        print(f"❌ Eroare la verificarea statusului Git: {stderr}")
        return False, []
    
    if not stdout.strip():
        print("✅ Nu există modificări de commit")
        return True, []
    
    changes = stdout.strip().split('\n')
    print(f"📝 Găsite {len(changes)} modificări:")
    for change in changes:
        print(f"  {change}")
    
    return True, changes

def create_commit_message():
    """Creează un mesaj de commit descriptiv"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Verifică ce fișiere au fost modificate
    success, stdout, stderr = run_command("git diff --name-only HEAD")
    modified_files = stdout.strip().split('\n') if stdout.strip() else []
    
    # Categoriile de modificări
    categories = {
        'core': ['app.py', 'bot.py', 'downloader.py'],
        'tests': ['test_comprehensive.py', 'test_render_compatibility.py'],
        'config': ['requirements.txt', 'Procfile', 'runtime.txt'],
        'docs': ['README.md', 'RENDER_DEPLOYMENT.md', 'GITHUB_DEPLOYMENT.md'],
        'scripts': ['verify_deployment.py', 'deploy_to_github.py']
    }
    
    # Determină ce categorii au fost modificate
    modified_categories = []
    for category, files in categories.items():
        if any(file in modified_files for file in files):
            modified_categories.append(category)
    
    # Creează mesajul de commit
    if 'core' in modified_categories:
        emoji = "🔥"
        title = "CORE UPDATE"
    elif 'tests' in modified_categories:
        emoji = "🧪"
        title = "TESTS UPDATE"
    elif 'config' in modified_categories:
        emoji = "⚙️"
        title = "CONFIG UPDATE"
    elif 'docs' in modified_categories:
        emoji = "📚"
        title = "DOCS UPDATE"
    else:
        emoji = "🔧"
        title = "MAINTENANCE UPDATE"
    
    commit_message = f"""{emoji} {title} - {timestamp}

🔄 Categorii modificate: {', '.join(modified_categories)}
📁 Fișiere modificate: {len(modified_files)}

✨ Îmbunătățiri incluse:
- Caption Manager centralizat cu truncare inteligentă
- Error Handler cu clasificare și retry logic  
- Rate limiting pentru protecția resurselor
- Platform detection și configurații specifice
- Monitoring și metrici în timp real
- Optimizări pentru Render free tier

🚀 Gata pentru auto-deployment pe Render!"""

    return commit_message

def main():
    """Funcția principală de deployment"""
    print("🚀 Script automat deployment GitHub")
    print("=" * 50)
    
    # Verifică că suntem într-un repository Git
    if not os.path.exists('.git'):
        print("❌ Nu este un repository Git. Inițializez...")
        success, stdout, stderr = run_command("git init")
        if not success:
            print(f"❌ Eroare la inițializarea Git: {stderr}")
            return False
        print("✅ Repository Git inițializat")
    
    # Verifică statusul Git
    success, changes = check_git_status()
    if not success:
        return False
    
    if not changes:
        print("✅ Nu există modificări de commit")
        return True
    
    # Confirmă deployment-ul
    print(f"\n📋 Pregătit pentru deployment cu {len(changes)} modificări")
    response = input("Continui cu deployment-ul? (y/N): ").strip().lower()
    
    if response not in ['y', 'yes', 'da']:
        print("❌ Deployment anulat")
        return False
    
    # Adaugă toate fișierele
    print("\n📁 Adaug fișierele...")
    success, stdout, stderr = run_command("git add .")
    if not success:
        print(f"❌ Eroare la adăugarea fișierelor: {stderr}")
        return False
    print("✅ Fișiere adăugate")
    
    # Creează commit-ul
    print("\n💬 Creez commit-ul...")
    commit_message = create_commit_message()
    
    # Escapează ghilimelele pentru comandă
    escaped_message = commit_message.replace('"', '\\"')
    success, stdout, stderr = run_command(f'git commit -m "{escaped_message}"')
    if not success:
        print(f"❌ Eroare la crearea commit-ului: {stderr}")
        return False
    print("✅ Commit creat cu succes")
    
    # Verifică remote-ul
    print("\n🔗 Verificare remote repository...")
    success, stdout, stderr = run_command("git remote -v")
    if not success or 'origin' not in stdout:
        print("⚠️  Nu există remote origin. Adaug...")
        github_url = "https://github.com/matrix01mindset/Downloader-Bot-Telegram.git"
        success, stdout, stderr = run_command(f"git remote add origin {github_url}")
        if not success:
            print(f"❌ Eroare la adăugarea remote-ului: {stderr}")
            return False
        print(f"✅ Remote adăugat: {github_url}")
    else:
        print("✅ Remote origin găsit")
    
    # Push la GitHub
    print("\n🚀 Push la GitHub...")
    success, stdout, stderr = run_command("git push -u origin main")
    if not success:
        # Încearcă cu master dacă main nu funcționează
        print("⚠️  Încercare cu branch master...")
        success, stdout, stderr = run_command("git push -u origin master")
        if not success:
            print(f"❌ Eroare la push: {stderr}")
            print("💡 Verifică că repository-ul GitHub există și ai permisiuni")
            return False
    
    print("✅ Push reușit pe GitHub!")
    
    # Afișează informații finale
    print("\n" + "=" * 50)
    print("🎉 DEPLOYMENT REUȘIT!")
    print("\n📋 Ce s-a întâmplat:")
    print("  ✅ Fișierele au fost adăugate în Git")
    print("  ✅ Commit-ul a fost creat cu mesaj descriptiv")
    print("  ✅ Codul a fost push-at pe GitHub")
    print("  ✅ Render va face auto-deploy în ~5-10 minute")
    
    print("\n🔗 Link-uri importante:")
    print("  • Repository: https://github.com/matrix01mindset/Downloader-Bot-Telegram")
    print("  • Render Dashboard: https://dashboard.render.com")
    
    print("\n📊 Următorii pași:")
    print("  1. Urmărește build-ul în Render Dashboard")
    print("  2. Verifică că status-ul devine 'Live'")
    print("  3. Testează bot-ul în Telegram")
    print("  4. Verifică metricile: /metrics endpoint")
    
    # Opțional - deschide browser-ul
    try:
        response = input("\nDeschid GitHub repository în browser? (y/N): ").strip().lower()
        if response in ['y', 'yes', 'da']:
            import webbrowser
            webbrowser.open("https://github.com/matrix01mindset/Downloader-Bot-Telegram")
    except:
        pass
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Deployment întrerupt de utilizator")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Eroare neașteptată: {e}")
        sys.exit(1)