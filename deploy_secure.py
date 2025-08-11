
#!/usr/bin/env python3
# Script automat pentru deployment cu noul token
# Generat la: 2025-08-12T01:27:06.044398

import subprocess
import sys
import os

def deploy_with_new_token():
    print("🚀 Deployment automat cu noul token...")
    
    try:
        # Verifică dacă avem modificări
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            print("📝 Commit modificări locale...")
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', 
                          'SECURITY: Update bot token after compromise - 2025-08-12 01:27'], 
                          check=True)
        
        # Push la repository
        print("📤 Push la GitHub...")
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print("✅ Deployment complet!")
        print("\n🔄 Render va redeployă automat în ~2-3 minute")
        print("\n📊 Verifică status la:")
        print("https://dashboard.render.com/web/srv-telegram-video-downloader-1471")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Eroare deployment: {e}")
        return False
    except Exception as e:
        print(f"❌ Eroare neașteptată: {e}")
        return False

if __name__ == "__main__":
    deploy_with_new_token()
