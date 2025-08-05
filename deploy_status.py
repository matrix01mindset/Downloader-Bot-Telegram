#!/usr/bin/env python3
"""
Script pentru verificarea statusului deployment-ului
"""

import requests
import time

def check_github_repo():
    """Verifică dacă repository-ul GitHub există"""
    repo_url = "https://api.github.com/repos/matrix01mindset/Downloader-Bot-Telegram"
    
    try:
        response = requests.get(repo_url, timeout=10)
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ Repository GitHub găsit:")
            print(f"   Nume: {repo_data['name']}")
            print(f"   URL: {repo_data['html_url']}")
            print(f"   Ultima actualizare: {repo_data['updated_at']}")
            print(f"   Branch principal: {repo_data['default_branch']}")
            return True
        elif response.status_code == 404:
            print("❌ Repository-ul GitHub nu există sau nu este public")
            return False
        else:
            print(f"❌ Eroare la verificarea repository-ului: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Eroare la conectarea la GitHub: {e}")
        return False

def check_render_services():
    """Verifică serviciile Render comune"""
    common_names = [
        "downloader-bot-telegram",
        "telegram-video-downloader", 
        "video-downloader-bot",
        "telegram-video-downloader-bot",
        "matrixdownload-bot",
        "matrix-downloader-bot",
        "telegram-downloader-bot"
    ]
    
    print("\n🔍 Verific serviciile Render comune...")
    
    for name in common_names:
        url = f"https://{name}.onrender.com/health"
        print(f"   Testez: {name}")
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ GĂSIT: {url}")
                print(f"   Răspuns: {response.json()}")
                return name, url
        except:
            pass
    
    print("   ❌ Nu am găsit niciun serviciu Render activ")
    return None, None

def main():
    print("🔍 VERIFICARE STATUS DEPLOYMENT")
    print("=" * 40)
    
    print("\n1️⃣ Verific repository-ul GitHub...")
    github_exists = check_github_repo()
    
    print("\n2️⃣ Verific serviciile Render...")
    service_name, service_url = check_render_services()
    
    print("\n📋 REZUMAT:")
    print("=" * 20)
    
    if github_exists:
        print("✅ Repository GitHub: EXISTĂ")
        print("   URL: https://github.com/matrix01mindset/Downloader-Bot-Telegram")
    else:
        print("❌ Repository GitHub: NU EXISTĂ")
        print("   Trebuie să încarci codul pe GitHub mai întâi!")
    
    if service_name:
        print(f"✅ Serviciu Render: GĂSIT ({service_name})")
        print(f"   URL: {service_url}")
        print("\n🎯 URMĂTORUL PAS: Setează webhook-ul")
        print(f"   Accesează: {service_url.replace('/health', '/set_webhook')}")
    else:
        print("❌ Serviciu Render: NU EXISTĂ")
        
        if github_exists:
            print("\n🚀 URMĂTORUL PAS: Deploy pe Render")
            print("   1. Mergi pe https://render.com")
            print("   2. Login cu GitHub")
            print("   3. Click 'New' → 'Web Service'")
            print("   4. Conectează repository-ul GitHub")
            print("   5. Urmează ghidul din RENDER_QUICK_SETUP.md")
        else:
            print("\n📤 PRIMUL PAS: Încarcă pe GitHub")
            print("   1. Rulează: fix_git_upload.bat")
            print("   2. Sau urmează ghidul din GIT_COMMANDS.md")
            print("   3. Apoi deploy pe Render")
    
    print("\n📚 GHIDURI DISPONIBILE:")
    print("   - RENDER_QUICK_SETUP.md (setup rapid Render)")
    print("   - GIT_COMMANDS.md (comenzi Git)")
    print("   - RENDER_FIX.md (rezolvare probleme)")

if __name__ == "__main__":
    main()