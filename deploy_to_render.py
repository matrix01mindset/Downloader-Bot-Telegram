#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de deployment automat pentru Render.com
Actualizează aplicația cu modificările pentru a rezolva erorile
"""

import os
import sys
import time
import requests
import subprocess
from datetime import datetime

# Configurare
RENDER_URL = "https://telegram-video-downloader-1471.onrender.com"
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

def check_git_status():
    """Verifică statusul Git"""
    print("🔍 Verific statusul Git...")
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                               capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print("📝 Modificări detectate:")
            for line in result.stdout.strip().split('\n'):
                print(f"   {line}")
            return True
        else:
            print("✅ Nu există modificări uncommitted")
            return False
    except subprocess.CalledProcessError:
        print("❌ Eroare la verificarea Git")
        return False
    except FileNotFoundError:
        print("❌ Git nu este instalat sau nu este în PATH")
        return False

def commit_and_push_changes():
    """Commit și push modificările"""
    print("\n📤 Commit și push modificări...")
    try:
        # Add toate fișierele modificate
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Commit cu mesaj descriptiv
        commit_message = f"Fix webhook errors - Update to python-telegram-bot 20.8 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        # Push la repository
        subprocess.run(['git', 'push'], check=True)
        
        print("✅ Modificările au fost push-uite cu succes")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Eroare la commit/push: {e}")
        return False

def wait_for_deployment():
    """Așteaptă ca deployment-ul să se finalizeze"""
    print("\n⏳ Aștept finalizarea deployment-ului...")
    print("   (Render va detecta automat modificările și va redeployă)")
    
    max_attempts = 30  # 15 minute
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{RENDER_URL}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Aplicația este online: {data}")
                return True
        except requests.RequestException:
            pass
        
        attempt += 1
        print(f"   Încercare {attempt}/{max_attempts}...")
        time.sleep(30)  # Așteaptă 30 secunde
    
    print("❌ Timeout - deployment-ul durează prea mult")
    return False

def test_webhook_after_deployment():
    """Testează webhook-ul după deployment"""
    print("\n🔗 Testez webhook-ul după deployment...")
    
    try:
        # Verifică webhook-ul curent
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                webhook_info = data['result']
                print(f"📋 Webhook URL: {webhook_info.get('url', 'Nu este setat')}")
                print(f"📊 Pending updates: {webhook_info.get('pending_update_count', 0)}")
                
                if webhook_info.get('last_error_message'):
                    print(f"⚠️ Ultima eroare: {webhook_info['last_error_message']}")
                    print(f"📅 Data erorii: {webhook_info.get('last_error_date', 'N/A')}")
                    return False
                else:
                    print("✅ Webhook funcționează fără erori")
                    return True
        
        print("❌ Nu s-au putut obține informații despre webhook")
        return False
        
    except Exception as e:
        print(f"❌ Eroare la testarea webhook-ului: {e}")
        return False

def main():
    """Funcția principală de deployment"""
    print("🚀 DEPLOYMENT AUTOMAT RENDER.COM")
    print("=" * 50)
    print(f"📍 Target: {RENDER_URL}")
    print(f"🤖 Bot: @matrixdownload_bot")
    print("=" * 50)
    
    # Pas 1: Verifică Git
    if not check_git_status():
        print("\n💡 Nu există modificări de commit. Verific aplicația actuală...")
    else:
        # Pas 2: Commit și push
        if not commit_and_push_changes():
            print("❌ Nu s-au putut push modificările")
            return
    
    # Pas 3: Așteaptă deployment
    if not wait_for_deployment():
        print("❌ Deployment-ul nu s-a finalizat în timp util")
        print("💡 Verifică manual statusul pe Render Dashboard")
        return
    
    # Pas 4: Testează webhook
    if test_webhook_after_deployment():
        print("\n🎉 DEPLOYMENT REUȘIT!")
        print("✅ Aplicația este online și webhook-ul funcționează")
        print(f"🔗 URL aplicație: {RENDER_URL}")
        print(f"🔗 Health check: {RENDER_URL}/health")
        print("\n📱 Testează bot-ul în Telegram:")
        print("1. Caută @matrixdownload_bot")
        print("2. Trimite /start")
        print("3. Trimite un link YouTube pentru test")
    else:
        print("\n⚠️ DEPLOYMENT PARȚIAL")
        print("✅ Aplicația este online")
        print("❌ Webhook-ul încă are erori")
        print("💡 Verifică logs-urile pe Render pentru detalii")

if __name__ == "__main__":
    main()