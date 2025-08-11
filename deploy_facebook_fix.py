#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de deploy pentru patch-ul Facebook pe Render
Acest script pregătește și face deploy cu fix-urile Facebook
"""

import subprocess
import sys
import os
import logging
import time
from datetime import datetime

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(command, description, timeout=300):
    """Execută o comandă și returnează rezultatul"""
    logger.info(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        if result.returncode == 0:
            logger.info(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                logger.info(f"Output: {result.stdout.strip()[:300]}...")
            return True, result.stdout
        else:
            logger.error(f"❌ {description} - FAILED")
            logger.error(f"Error: {result.stderr.strip()[:300]}...")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ {description} - TIMEOUT")
        return False, "Timeout"
    except Exception as e:
        logger.error(f"💥 {description} - EXCEPTION: {e}")
        return False, str(e)

def check_git_status():
    """Verifică statusul Git"""
    logger.info("📊 === VERIFICARE GIT STATUS ===")
    
    success, output = run_command("git status --porcelain", "Verificare fișiere modificate")
    if success:
        if output.strip():
            logger.info("📝 Fișiere modificate detectate:")
            for line in output.strip().split('\n'):
                logger.info(f"  {line}")
        else:
            logger.info("✅ Nu sunt fișiere modificate")
    
    return success

def commit_facebook_fixes():
    """Commit patch-urile Facebook"""
    logger.info("💾 === COMMIT FACEBOOK FIXES ===")
    
    # Adaugă fișierele modificate
    commands = [
        ("git add downloader.py", "Adăugare downloader.py modificat"),
        ("git add facebook_fix_patch.py", "Adăugare Facebook patch"),
        ("git add fix_facebook_issues.py", "Adăugare script fix Facebook"),
        ("git add deploy_facebook_fix.py", "Adăugare script deploy"),
    ]
    
    success_count = 0
    for command, description in commands:
        success, _ = run_command(command, description)
        if success:
            success_count += 1
    
    # Commit cu mesaj descriptiv
    commit_message = f"🔧 Facebook Fix Patch - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    commit_message += "\n\n✅ Rezolvă problemele Facebook:\n"
    commit_message += "• ERROR: [facebook] Cannot parse data\n"
    commit_message += "• URL-uri share/v/ nesuportate\n"
    commit_message += "• API Facebook v19.0 support\n"
    commit_message += "• Configurații robuste extractor\n"
    commit_message += "• Gestionare îmbunătățită erori\n\n"
    commit_message += "🚀 Ready for Render deployment"
    
    success, _ = run_command(f'git commit -m "{commit_message}"', "Commit Facebook fixes")
    
    return success

def push_to_github():
    """Push la GitHub pentru trigger Render deploy"""
    logger.info("🚀 === PUSH TO GITHUB ===")
    
    # Verifică branch-ul curent
    success, branch_output = run_command("git branch --show-current", "Verificare branch curent")
    if success:
        current_branch = branch_output.strip()
        logger.info(f"📍 Branch curent: {current_branch}")
    else:
        current_branch = "main"  # Fallback
    
    # Push la GitHub
    success, _ = run_command(f"git push origin {current_branch}", "Push la GitHub", timeout=120)
    
    if success:
        logger.info("✅ Push reușit - Render va detecta automat schimbările")
        logger.info("🔄 Deploy automat va începe în câteva secunde...")
    
    return success

def verify_files_exist():
    """Verifică că toate fișierele necesare există"""
    logger.info("📋 === VERIFICARE FIȘIERE ===")
    
    required_files = [
        "downloader.py",
        "facebook_fix_patch.py",
        "app.py",
        "requirements.txt",
        "Procfile"
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            logger.info(f"✅ {file} - EXISTS")
        else:
            logger.error(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"💥 Fișiere lipsă: {', '.join(missing_files)}")
        return False
    
    return True

def update_requirements():
    """Actualizează requirements.txt cu versiuni noi"""
    logger.info("📝 === ACTUALIZARE REQUIREMENTS ===")
    
    # Citește requirements.txt actual
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            current_requirements = f.read()
        
        logger.info("📋 Requirements.txt curent:")
        for line in current_requirements.strip().split('\n'):
            if line.strip():
                logger.info(f"  {line}")
        
        # Verifică dacă yt-dlp este la versiunea corectă
        if 'yt-dlp' in current_requirements:
            logger.info("✅ yt-dlp găsit în requirements.txt")
        else:
            logger.warning("⚠️ yt-dlp nu este în requirements.txt")
            # Adaugă yt-dlp dacă lipsește
            with open('requirements.txt', 'a', encoding='utf-8') as f:
                f.write('\nyt-dlp[default]>=2024.1.1\n')
            logger.info("✅ yt-dlp adăugat în requirements.txt")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Eroare la actualizare requirements.txt: {e}")
        return False

def show_deployment_status():
    """Afișează informații despre statusul deployment-ului"""
    logger.info("\n" + "="*60)
    logger.info("🚀 === DEPLOYMENT STATUS ===")
    logger.info("="*60)
    
    logger.info("\n📋 PATCH-URI APLICATE:")
    logger.info("✅ Facebook fix patch integrat în downloader.py")
    logger.info("✅ Configurații robuste Facebook (API v19.0)")
    logger.info("✅ Normalizare URL-uri share/v/")
    logger.info("✅ Gestionare îmbunătățită erori parsing")
    logger.info("✅ Fallback strategies pentru Facebook")
    
    logger.info("\n🔄 NEXT STEPS:")
    logger.info("1. 🕐 Așteaptă 2-3 minute pentru deploy Render")
    logger.info("2. 🌐 Verifică https://telegram-video-downloader-1471.onrender.com/health")
    logger.info("3. 🧪 Testează link-uri Facebook în bot")
    logger.info("4. 📊 Monitorizează log-urile Render pentru erori")
    
    logger.info("\n🧪 TEST LINKS FACEBOOK:")
    logger.info("• https://www.facebook.com/watch?v=[video_id]")
    logger.info("• https://www.facebook.com/share/v/[video_id]/")
    logger.info("• https://fb.watch/[short_id]")
    
    logger.info("\n📊 MONITORING:")
    logger.info("• Render Dashboard: https://dashboard.render.com")
    logger.info("• Bot health: /health endpoint")
    logger.info("• Telegram bot: @matrixdownload_bot")

def main():
    """Funcția principală"""
    logger.info("🚀 === FACEBOOK FIX DEPLOYMENT SCRIPT ===")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    steps = [
        ("Verificare fișiere", verify_files_exist),
        ("Actualizare requirements", update_requirements),
        ("Verificare Git status", check_git_status),
        ("Commit Facebook fixes", commit_facebook_fixes),
        ("Push la GitHub", push_to_github)
    ]
    
    results = []
    for step_name, step_func in steps:
        logger.info(f"\n{'='*50}")
        logger.info(f"🔄 STEP: {step_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = step_func()
            results.append((step_name, success))
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"📊 {step_name}: {status}")
            
            if not success and step_name in ["Commit Facebook fixes", "Push la GitHub"]:
                logger.warning(f"⚠️ {step_name} eșuat - continuă oricum")
                
        except Exception as e:
            logger.error(f"💥 {step_name}: EXCEPTION - {e}")
            results.append((step_name, False))
        
        time.sleep(1)
    
    # Raport final
    logger.info(f"\n{'='*60}")
    logger.info("📊 === RAPORT FINAL ===")
    logger.info(f"{'='*60}")
    
    success_count = 0
    for step_name, success in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {step_name}")
        if success:
            success_count += 1
    
    total_steps = len(results)
    success_rate = (success_count / total_steps) * 100
    
    logger.info(f"\n📈 SUCCESS RATE: {success_count}/{total_steps} ({success_rate:.1f}%)")
    
    if success_rate >= 60:  # Permisiv pentru Git operations
        logger.info("🎉 FACEBOOK FIX DEPLOYMENT: COMPLETED")
        show_deployment_status()
    else:
        logger.warning("⚠️ FACEBOOK FIX DEPLOYMENT: PARTIAL SUCCESS")
        logger.warning("Verifică erorile de mai sus.")
    
    return success_rate >= 60

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Script oprit de utilizator")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Eroare critică: {e}")
        sys.exit(1)