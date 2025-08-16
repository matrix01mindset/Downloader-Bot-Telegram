#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test specific pentru compatibilitatea cu Render free tier
Verifică:
- Limitări de memorie și CPU
- Timeout-uri și configurații
- Cleanup fișiere temporare
- Performance webhook-uri
"""

import os
import sys
import time
import tempfile
import threading
import psutil
import requests
from concurrent.futures import ThreadPoolExecutor

def test_memory_usage():
    """Testează utilizarea memoriei"""
    print("🧠 Testez utilizarea memoriei...")
    
    try:
        # Import modulele principale
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import create_safe_caption, ErrorHandler
        from downloader import get_platform_specific_config
        
        # Măsoară memoria înainte
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulează operații intensive
        for i in range(100):
            caption = create_safe_caption(
                title="Test video " * 50,
                description="Test description " * 100,
                uploader="Test uploader",
                duration=1800,
                file_size=50*1024*1024
            )
            
            error_type = ErrorHandler.classify_error("test error message", "test")
            config = get_platform_specific_config("tiktok")
        
        # Măsoară memoria după
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_diff = memory_after - memory_before
        
        print(f"📊 Memorie înainte: {memory_before:.1f}MB")
        print(f"📊 Memorie după: {memory_after:.1f}MB")
        print(f"📊 Diferență: {memory_diff:.1f}MB")
        
        # Render free tier are ~512MB RAM
        if memory_after < 400:  # Păstrează 100MB buffer
            print("✅ Utilizarea memoriei este acceptabilă pentru Render free tier")
            return True
        else:
            print("❌ Utilizarea memoriei este prea mare pentru Render free tier")
            return False
            
    except Exception as e:
        print(f"❌ Eroare la testarea memoriei: {e}")
        return False

def test_file_cleanup():
    """Testează cleanup-ul fișierelor temporare"""
    print("\n🧹 Testez cleanup-ul fișierelor temporare...")
    
    try:
        from app import cleanup_temp_files
        
        # Creează fișiere temporare de test
        temp_dir = tempfile.gettempdir()
        test_files = []
        
        for i in range(5):
            temp_file = os.path.join(temp_dir, f"test_video_{i}.mp4")
            with open(temp_file, 'w') as f:
                f.write("test content")
            test_files.append(temp_file)
            
            # Setează timestamp-ul în trecut pentru a simula fișiere vechi
            old_time = time.time() - 400  # 400 secunde în trecut
            os.utime(temp_file, (old_time, old_time))
        
        files_before = len([f for f in test_files if os.path.exists(f)])
        print(f"📁 Fișiere create: {files_before}")
        
        # Rulează cleanup
        cleanup_temp_files()
        
        files_after = len([f for f in test_files if os.path.exists(f)])
        print(f"📁 Fișiere rămase: {files_after}")
        
        # Curăță fișierele rămase
        for file in test_files:
            if os.path.exists(file):
                os.remove(file)
        
        if files_after < files_before:
            print("✅ Cleanup-ul funcționează corect")
            return True
        else:
            print("❌ Cleanup-ul nu a șters fișierele vechi")
            return False
            
    except Exception as e:
        print(f"❌ Eroare la testarea cleanup-ului: {e}")
        return False

def test_webhook_performance():
    """Testează performanța webhook-urilor"""
    print("\n⚡ Testez performanța webhook-urilor...")
    
    # Verifică dacă serverul local rulează
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Serverul local nu rulează. Pornește cu 'python app.py'")
            return False
    except requests.exceptions.RequestException:
        print("❌ Nu pot conecta la serverul local")
        return False
    
    webhook_url = "http://localhost:5000/webhook"
    success_count = 0
    total_requests = 10
    response_times = []
    
    def send_webhook_request(i):
        """Trimite o cerere webhook"""
        payload = {
            "update_id": i,
            "message": {
                "text": "/start",
                "chat": {"id": 123456 + i, "type": "private"},
                "from": {"id": 123456 + i, "first_name": f"TestUser{i}", "is_bot": False},
                "message_id": i,
                "date": int(time.time())
            }
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # ms
            
            if response.status_code == 200:
                return True, response_time
            else:
                return False, response_time
                
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return False, response_time
    
    # Test secvențial
    print("📊 Test secvențial...")
    for i in range(5):
        success, response_time = send_webhook_request(i)
        if success:
            success_count += 1
        response_times.append(response_time)
        print(f"  Request {i+1}: {'✅' if success else '❌'} {response_time:.0f}ms")
        time.sleep(0.5)  # Pauză între cereri
    
    # Test concurrent (simulează load)
    print("📊 Test concurrent...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_webhook_request, i+5) for i in range(5)]
        for i, future in enumerate(futures):
            success, response_time = future.result()
            if success:
                success_count += 1
            response_times.append(response_time)
            print(f"  Concurrent {i+1}: {'✅' if success else '❌'} {response_time:.0f}ms")
    
    # Analizează rezultatele
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    print(f"\n📊 Rezultate performance:")
    print(f"  Cereri reușite: {success_count}/{total_requests}")
    print(f"  Timp mediu răspuns: {avg_response_time:.0f}ms")
    print(f"  Timp maxim răspuns: {max_response_time:.0f}ms")
    
    # Criterii pentru Render free tier
    success_rate = success_count / total_requests
    if success_rate >= 0.8 and avg_response_time < 5000:  # 80% success, <5s avg
        print("✅ Performanța webhook-urilor este acceptabilă pentru Render")
        return True
    else:
        print("❌ Performanța webhook-urilor este sub așteptări")
        return False

def test_timeout_configurations():
    """Testează configurațiile de timeout"""
    print("\n⏰ Testez configurațiile de timeout...")
    
    try:
        from downloader import get_platform_specific_config
        
        platforms = ['tiktok', 'instagram', 'facebook', 'twitter']
        success_count = 0
        
        for platform in platforms:
            config = get_platform_specific_config(platform)
            
            socket_timeout = config.get('socket_timeout', 0)
            retries = config.get('retries', 0)
            
            print(f"📊 {platform.title()}:")
            print(f"  Socket timeout: {socket_timeout}s")
            print(f"  Retries: {retries}")
            
            # Verifică că timeout-urile sunt optimizate pentru Render
            if socket_timeout <= 20 and retries <= 3:
                print(f"  ✅ Configurații optimizate pentru Render")
                success_count += 1
            else:
                print(f"  ❌ Configurații prea agresive pentru Render free tier")
        
        print(f"\n📊 Platforme cu configurații optime: {success_count}/{len(platforms)}")
        return success_count == len(platforms)
        
    except Exception as e:
        print(f"❌ Eroare la testarea timeout-urilor: {e}")
        return False

def main():
    """Rulează toate testele pentru Render compatibility"""
    print("🚀 Testare compatibilitate Render free tier...")
    print("=" * 60)
    
    results = {
        "memory_usage": test_memory_usage(),
        "file_cleanup": test_file_cleanup(),
        "webhook_performance": test_webhook_performance(),
        "timeout_configurations": test_timeout_configurations()
    }
    
    print("\n" + "=" * 60)
    print("📋 REZULTATE COMPATIBILITATE RENDER:")
    
    all_passed = True
    passed_tests = 0
    
    for test_name, result in results.items():
        status = "✅ TRECUT" if result else "❌ EȘUAT"
        print(f"  {test_name}: {status}")
        if result:
            passed_tests += 1
        else:
            all_passed = False
    
    print(f"\n📊 SCOR COMPATIBILITATE: {passed_tests}/{len(results)} teste trecute")
    
    if all_passed:
        print("\n🎉 BOT-UL ESTE COMPATIBIL CU RENDER FREE TIER!")
        print("💡 Poți proceda cu deployment-ul pe Render.")
    else:
        print(f"\n⚠️  BOT-UL ARE PROBLEME DE COMPATIBILITATE CU RENDER!")
        print("💡 Rezolvă problemele înainte de deployment.")
    
    return all_passed

if __name__ == "__main__":
    main()