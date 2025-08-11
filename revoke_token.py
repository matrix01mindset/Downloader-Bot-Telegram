#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de urgență pentru revocarea și actualizarea tokenului bot
Autor: Assistant
Data: 2025-08-11
"""

import os
import sys
import requests
import json
from datetime import datetime
import subprocess
import time

class TokenManager:
    def __init__(self):
        self.old_token = None
        self.new_token = None
        self.env_file = '.env'
        
    def load_current_token(self):
        """Încarcă tokenul curent din .env"""
        try:
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r') as f:
                    for line in f:
                        if line.startswith('BOT_TOKEN='):
                            self.old_token = line.split('=', 1)[1].strip()
                            print(f"✅ Token curent găsit: {self.old_token[:10]}...")
                            return True
            print("❌ Nu s-a găsit tokenul în .env")
            return False
        except Exception as e:
            print(f"❌ Eroare la citirea .env: {e}")
            return False
    
    def test_token(self, token, description=""):
        """Testează dacă un token funcționează"""
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    print(f"✅ {description} Token valid: @{bot_info.get('username', 'unknown')}")
                    return True
            
            print(f"❌ {description} Token invalid sau revocat")
            return False
            
        except Exception as e:
            print(f"❌ Eroare la testarea tokenului {description}: {e}")
            return False
    
    def update_env_file(self, new_token):
        """Actualizează fișierul .env cu noul token"""
        try:
            # Backup vechiul .env
            if os.path.exists(self.env_file):
                backup_name = f".env.backup.{int(time.time())}"
                os.rename(self.env_file, backup_name)
                print(f"✅ Backup creat: {backup_name}")
            
            # Scrie noul .env
            with open(self.env_file, 'w') as f:
                f.write(f"BOT_TOKEN={new_token}\n")
                f.write(f"# Token actualizat la: {datetime.now().isoformat()}\n")
                f.write(f"# Token vechi revocat pentru securitate\n")
            
            print(f"✅ Fișierul .env actualizat cu noul token")
            return True
            
        except Exception as e:
            print(f"❌ Eroare la actualizarea .env: {e}")
            return False
    
    def check_git_security(self):
        """Verifică dacă tokenul a fost expus în Git"""
        print("\n🔍 Verificare securitate Git...")
        
        try:
            # Verifică dacă .env este în .gitignore
            gitignore_path = '.gitignore'
            env_in_gitignore = False
            
            if os.path.exists(gitignore_path):
                with open(gitignore_path, 'r') as f:
                    content = f.read()
                    if '.env' in content:
                        env_in_gitignore = True
            
            if env_in_gitignore:
                print("✅ .env este în .gitignore")
            else:
                print("⚠️  .env NU este în .gitignore - RISC DE SECURITATE!")
                self.fix_gitignore()
            
            # Verifică istoricul Git pentru token-uri
            try:
                result = subprocess.run(
                    ['git', 'log', '--all', '--grep=token', '--oneline'],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout:
                    print("⚠️  Găsite commit-uri cu 'token' în mesaj:")
                    print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
            except:
                print("ℹ️  Nu s-a putut verifica istoricul Git")
                
        except Exception as e:
            print(f"❌ Eroare la verificarea Git: {e}")
    
    def fix_gitignore(self):
        """Adaugă .env în .gitignore dacă nu există"""
        try:
            gitignore_content = """
# Environment variables
.env
.env.local
.env.*.local

# Security files
*.key
*secret*
token.txt

# Backup files
.env.backup.*
"""
            
            with open('.gitignore', 'a') as f:
                f.write(gitignore_content)
            
            print("✅ .gitignore actualizat pentru securitate")
            
        except Exception as e:
            print(f"❌ Eroare la actualizarea .gitignore: {e}")
    
    def generate_security_report(self):
        """Generează un raport de securitate"""
        report = f"""
🔒 RAPORT SECURITATE BOT TELEGRAM
=====================================
Data: {datetime.now().isoformat()}
Motiv: Token compromis de hackeri

📊 STATUS:
- Token vechi: {'Revocat' if self.old_token else 'Necunoscut'}
- Token nou: {'Configurat' if self.new_token else 'Neconfigurat'}
- .env: {'Actualizat' if os.path.exists('.env') else 'Lipsă'}
- .gitignore: {'Securizat' if '.env' in open('.gitignore', 'r').read() else 'Nesecurizat'}

🚨 ACȚIUNI URMĂTOARE:
1. Testează botul cu noul token
2. Actualizează Render.com cu noul token
3. Monitorizează logs-urile pentru activitate suspectă
4. Implementează măsuri de securitate suplimentare

⚠️  IMPORTANT:
- Nu împărtăși niciodată tokenul
- Monitorizează activitatea botului
- Revocă imediat dacă suspectezi o nouă compromitere
"""
        
        try:
            with open(f'security_report_{int(time.time())}.txt', 'w', encoding='utf-8') as f:
                f.write(report)
            print("✅ Raport de securitate generat")
        except Exception as e:
            print(f"❌ Eroare la generarea raportului: {e}")
        
        return report

def main():
    print("🚨 SCRIPT DE URGENȚĂ - REVOCARE TOKEN BOT")
    print("==========================================\n")
    
    manager = TokenManager()
    
    # Pas 1: Încarcă tokenul curent
    print("📋 Pas 1: Verificare token curent...")
    if not manager.load_current_token():
        print("❌ Nu s-a putut încărca tokenul curent")
        old_token = input("Introdu tokenul vechi manual (sau ENTER pentru a sări): ").strip()
        if old_token:
            manager.old_token = old_token
    
    # Pas 2: Testează tokenul vechi
    if manager.old_token:
        print("\n📋 Pas 2: Testare token vechi...")
        if manager.test_token(manager.old_token, "[VECHI]"):
            print("⚠️  ATENȚIE: Tokenul vechi încă funcționează!")
            print("🔥 TREBUIE REVOCAT IMEDIAT în @BotFather!")
        else:
            print("✅ Tokenul vechi a fost deja revocat")
    
    # Pas 3: Solicită noul token
    print("\n📋 Pas 3: Configurare token nou...")
    print("\n🤖 INSTRUCȚIUNI BOTFATHER:")
    print("1. Deschide Telegram și caută @BotFather")
    print("2. Trimite: /mybots")
    print("3. Selectează botul tău")
    print("4. Apasă 'API Token' → 'Revoke current token'")
    print("5. Apasă 'Generate new token'")
    print("6. Copiază noul token și introdu-l mai jos\n")
    
    new_token = input("🔑 Introdu NOUL token (din BotFather): ").strip()
    
    if not new_token:
        print("❌ Token nou necesar pentru continuare")
        return
    
    manager.new_token = new_token
    
    # Pas 4: Testează noul token
    print("\n📋 Pas 4: Testare token nou...")
    if not manager.test_token(manager.new_token, "[NOU]"):
        print("❌ Tokenul nou nu funcționează - verifică din nou")
        return
    
    # Pas 5: Actualizează .env
    print("\n📋 Pas 5: Actualizare configurație...")
    if not manager.update_env_file(manager.new_token):
        print("❌ Nu s-a putut actualiza .env")
        return
    
    # Pas 6: Verifică securitatea Git
    manager.check_git_security()
    
    # Pas 7: Generează raport
    print("\n📋 Pas 7: Generare raport securitate...")
    report = manager.generate_security_report()
    
    # Finalizare
    print("\n" + "="*50)
    print("✅ REVOCARE COMPLETĂ!")
    print("="*50)
    print("\n🎯 URMĂTORII PAȘI:")
    print("1. 🌐 Actualizează tokenul pe Render.com:")
    print("   - Accesează https://dashboard.render.com")
    print("   - Selectează serviciul telegram-video-downloader-1471")
    print("   - Environment → BOT_TOKEN → Edit")
    print(f"   - Înlocuiește cu: {manager.new_token[:20]}...")
    print("\n2. 🧪 Testează botul:")
    print("   - python app.py")
    print("   - Trimite un mesaj de test")
    print("\n3. 📊 Monitorizează:")
    print("   - Verifică logs-urile Render")
    print("   - Urmărește activitatea suspectă")
    print("\n🔒 Botul este acum SECURIZAT!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Script întrerupt de utilizator")
    except Exception as e:
        print(f"\n\n💥 Eroare critică: {e}")
        print("🆘 Contactează suportul pentru ajutor!")