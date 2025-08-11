#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script de monitorizare bot după actualizarea tokenului

import requests
import time
import json
from datetime import datetime

BOT_TOKEN = "8253089686:AAGbSnyOKFYt36_cjZdG5AaecRPCytvBDmI"
CHECK_INTERVAL = 30  # secunde

def check_bot_status():
    """Verifică statusul botului"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Bot activ: @{bot_info.get('username', 'unknown')}")
                return True
        
        print(f"❌ {datetime.now().strftime('%H:%M:%S')} - Bot inactiv")
        return False
        
    except Exception as e:
        print(f"❌ {datetime.now().strftime('%H:%M:%S')} - Eroare: {e}")
        return False

def main():
    print("🔍 MONITORIZARE BOT TELEGRAM")
    print("============================\n")
    print(f"Token: {BOT_TOKEN[:15]}...")
    print(f"Interval verificare: {CHECK_INTERVAL} secunde")
    print("Apasă Ctrl+C pentru a opri\n")
    
    try:
        while True:
            if check_bot_status():
                print("🟢 Bot funcționează\n")
            else:
                print("🔴 Bot inactiv\n")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n👋 Monitorizare oprită")
    except Exception as e:
        print(f"\n💥 Eroare: {e}")

if __name__ == "__main__":
    main()
