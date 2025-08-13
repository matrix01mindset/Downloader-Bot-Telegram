#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test pentru funcționalitatea de procesare a multiplelor linkuri
"""

import re
from urllib.parse import urlparse

def extract_urls_from_text(text):
    """
    Extrage toate URL-urile dintr-un text și le returnează ca listă.
    Detectează URL-uri cu http/https și fără protocol.
    """
    if not text:
        return []
    
    # Pattern pentru URL-uri cu protocol
    url_pattern_with_protocol = r'https?://[^\s]+'
    
    # Pattern pentru URL-uri fără protocol (domenii cunoscute)
    url_pattern_without_protocol = r'(?:^|\s)((?:www\.|m\.|mobile\.)?(?:tiktok\.com|instagram\.com|facebook\.com|twitter\.com|x\.com|threads\.net|pinterest\.com|reddit\.com|vimeo\.com|dailymotion\.com)/[^\s]+)'
    
    urls = []
    
    # Găsește URL-uri cu protocol
    urls_with_protocol = re.findall(url_pattern_with_protocol, text, re.IGNORECASE)
    urls.extend(urls_with_protocol)
    
    # Găsește URL-uri fără protocol
    urls_without_protocol = re.findall(url_pattern_without_protocol, text, re.IGNORECASE)
    for url in urls_without_protocol:
        if not url.startswith('http'):
            urls.append('https://' + url)
        else:
            urls.append(url)
    
    # Elimină duplicatele și returnează lista
    return list(set(urls))

def test_url_extraction():
    """
    Testează funcția de extragere a URL-urilor
    """
    print("🧪 TESTARE EXTRAGERE URL-URI")
    print("=" * 50)
    
    test_cases = [
        {
            "text": "https://www.tiktok.com/@user/video/123456789",
            "expected_count": 1,
            "description": "Un singur link TikTok cu protocol"
        },
        {
            "text": "Uite videoclipurile: https://www.instagram.com/p/ABC123/ și https://www.tiktok.com/@user/video/123",
            "expected_count": 2,
            "description": "Două linkuri cu protocol"
        },
        {
            "text": "www.instagram.com/p/ABC123/ tiktok.com/@user/video/123",
            "expected_count": 2,
            "description": "Două linkuri fără protocol"
        },
        {
            "text": "Mixte: https://facebook.com/video/123 și www.twitter.com/user/status/456 plus reddit.com/r/videos/comments/789",
            "expected_count": 3,
            "description": "Linkuri mixte (cu și fără protocol)"
        },
        {
            "text": "Nu conține linkuri valide, doar text normal.",
            "expected_count": 0,
            "description": "Text fără linkuri"
        },
        {
            "text": "https://youtube.com/watch?v=123 https://google.com",
            "expected_count": 2,
            "description": "Linkuri nesuportate (ar trebui să le detecteze, dar nu le va procesa)"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"📄 Text: {test_case['text']}")
        
        urls = extract_urls_from_text(test_case['text'])
        
        print(f"🔍 URL-uri găsite ({len(urls)}):")
        for url in urls:
            print(f"   • {url}")
        
        if len(urls) == test_case['expected_count']:
            print(f"✅ SUCCES: Găsite {len(urls)} URL-uri (așteptat: {test_case['expected_count']})")
        else:
            print(f"❌ EȘEC: Găsite {len(urls)} URL-uri (așteptat: {test_case['expected_count']})")

def simulate_supported_url_check(url):
    """
    Simulează funcția is_supported_url pentru test
    """
    supported_domains = [
        'tiktok.com', 'instagram.com', 'facebook.com', 
        'twitter.com', 'x.com', 'threads.net', 
        'pinterest.com', 'reddit.com', 'vimeo.com', 'dailymotion.com'
    ]
    
    for domain in supported_domains:
        if domain in url.lower():
            return True
    return False

def filter_supported_urls(urls):
    """
    Filtrează doar URL-urile suportate din lista dată.
    """
    supported_urls = []
    for url in urls:
        if simulate_supported_url_check(url):
            supported_urls.append(url)
    return supported_urls

def test_complete_workflow():
    """
    Testează workflow-ul complet de procesare
    """
    print("\n\n🔄 TESTARE WORKFLOW COMPLET")
    print("=" * 50)
    
    test_messages = [
        "Uite videoclipurile mele: https://www.tiktok.com/@user1/video/123 https://www.instagram.com/p/ABC123/ https://youtube.com/watch?v=456",
        "www.facebook.com/video/789 și reddit.com/r/videos/comments/101112",
        "Un singur link: https://vimeo.com/123456789",
        "Text fără linkuri valide"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📱 Mesaj {i}: {message[:60]}{'...' if len(message) > 60 else ''}")
        
        # Extrage toate URL-urile
        all_urls = extract_urls_from_text(message)
        print(f"🔍 URL-uri detectate: {len(all_urls)}")
        
        # Filtrează URL-urile suportate
        supported_urls = filter_supported_urls(all_urls)
        print(f"✅ URL-uri suportate: {len(supported_urls)}")
        
        if supported_urls:
            if len(supported_urls) > 1:
                print(f"🎯 Procesare multiplă: {len(supported_urls)} videoclipuri")
                print(f"⏱️ Timp estimat: ~{len(supported_urls) * 10} secunde")
            else:
                print(f"📱 Procesare simplă: 1 videoclip")
            
            for j, url in enumerate(supported_urls, 1):
                print(f"   {j}. {url}")
        else:
            if all_urls:
                print(f"❌ URL-uri nesuportate găsite: {len(all_urls)}")
            else:
                print(f"❌ Niciun URL găsit")

if __name__ == "__main__":
    test_url_extraction()
    test_complete_workflow()
    
    print("\n\n🎉 TESTARE COMPLETĂ!")
    print("\n💡 Pentru a testa cu bot-ul real:")
    print("   1. Trimite un mesaj cu multiple linkuri")
    print("   2. Bot-ul va detecta automat toate linkurile")
    print("   3. Va procesa fiecare cu o pauză de 3 secunde")
    print("   4. Va afișa progresul și raportul final")