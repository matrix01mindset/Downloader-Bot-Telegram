#!/usr/bin/env python3
import os

print("=== VERIFICARE VARIABILE DE MEDIU ===")
print(f"TELEGRAM_BOT_TOKEN: {'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET'}")
print(f"WEBHOOK_URL: {os.getenv('WEBHOOK_URL', 'NOT SET')}")
print(f"PORT: {os.getenv('PORT', 'NOT SET')}")

if os.getenv('TELEGRAM_BOT_TOKEN'):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    print(f"Token length: {len(token)}")
    print(f"Token starts with: {token[:10]}...")
else:
    print("❌ TELEGRAM_BOT_TOKEN nu este setat!")

print("\n=== TOATE VARIABILELE DE MEDIU ===")
for key, value in os.environ.items():
    if 'TOKEN' in key.upper() or 'WEBHOOK' in key.upper() or 'PORT' in key.upper():
        print(f"{key}: {value}")