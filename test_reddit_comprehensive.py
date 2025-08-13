#!/usr/bin/env python3
"""
Comprehensive Reddit Video Download Test
Tests multiple Reddit URL formats and scenarios
"""

import requests
import os
import tempfile
import time
import json
from urllib.parse import urlparse

# Test URLs for different Reddit scenarios
test_urls = [
    # Direct v.redd.it URLs
    'https://v.redd.it/92567y9qsmif1/DASH_480.mp4?source=fallback',
    
    # Reddit post URLs (these would need JSON extraction)
    'https://www.reddit.com/r/funny/comments/abc123/test_video/',
    'https://old.reddit.com/r/videos/comments/def456/another_test/',
    
    # Mobile Reddit URLs
    'https://m.reddit.com/r/gifs/comments/ghi789/mobile_test/',
    
    # Short Reddit URLs
    'https://redd.it/jkl012',
]

def test_direct_video_download(video_url):
    """Test direct video download from v.redd.it"""
    print(f"\n🔍 Testing direct download: {video_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.reddit.com/',
        'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
        'Accept-Language': 'en-US,en;q=0.5',
        'Range': 'bytes=0-'
    }
    
    try:
        response = requests.get(video_url, headers=headers, stream=True, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type')}")
        print(f"  Content-Length: {response.headers.get('content-length')}")
        
        if response.status_code in [200, 206]:
            print(f"  ✅ Video accessible (Status: {response.status_code})")
            
            # Test small download
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                print(f"  📊 File size: {size_mb:.2f} MB")
                
                if size_mb > 50:  # Telegram limit
                    print(f"  ⚠️ Warning: File too large for Telegram ({size_mb:.2f} MB > 50 MB)")
                else:
                    print(f"  ✅ File size OK for Telegram")
            
            return True
        else:
            print(f"  ❌ Video not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_reddit_json_extraction(reddit_url):
    """Test Reddit JSON extraction strategies"""
    print(f"\n🔍 Testing JSON extraction: {reddit_url}")
    
    strategies = [
        {
            'name': 'Reddit JSON Direct',
            'url_transform': lambda url: url.rstrip('/') + '.json'
        },
        {
            'name': 'Old Reddit JSON',
            'url_transform': lambda url: url.replace('www.reddit.com', 'old.reddit.com').replace('m.reddit.com', 'old.reddit.com').rstrip('/') + '.json'
        },
        {
            'name': 'Mobile Reddit',
            'url_transform': lambda url: url.replace('www.reddit.com', 'm.reddit.com').replace('old.reddit.com', 'm.reddit.com').rstrip('/') + '.json'
        }
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.reddit.com/'
    }
    
    for strategy in strategies:
        try:
            target_url = strategy['url_transform'](reddit_url)
            print(f"  📡 Trying {strategy['name']}: {target_url}")
            
            response = requests.get(target_url, headers=headers, timeout=10)
            print(f"    Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    ✅ JSON parsed successfully")
                    
                    # Look for video URLs in the JSON
                    video_urls = extract_video_urls_from_json(data)
                    if video_urls:
                        print(f"    🎬 Found {len(video_urls)} video URL(s):")
                        for i, url in enumerate(video_urls[:3]):  # Show first 3
                            print(f"      {i+1}. {url}")
                        return video_urls[0]  # Return first video URL
                    else:
                        print(f"    ⚠️ No video URLs found in JSON")
                        
                except json.JSONDecodeError as e:
                    print(f"    ❌ JSON decode error: {e}")
            else:
                print(f"    ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    return None

def extract_video_urls_from_json(data):
    """Extract video URLs from Reddit JSON data"""
    video_urls = []
    
    try:
        # Handle Reddit JSON structure
        if isinstance(data, list) and len(data) > 0:
            data = data[0]  # First element is usually the post data
        
        if 'data' in data and 'children' in data['data']:
            for child in data['data']['children']:
                post_data = child.get('data', {})
                
                # Check secure_media
                if 'secure_media' in post_data and post_data['secure_media']:
                    reddit_video = post_data['secure_media'].get('reddit_video', {})
                    if 'fallback_url' in reddit_video:
                        video_urls.append(reddit_video['fallback_url'])
                
                # Check media
                if 'media' in post_data and post_data['media']:
                    reddit_video = post_data['media'].get('reddit_video', {})
                    if 'fallback_url' in reddit_video:
                        video_urls.append(reddit_video['fallback_url'])
                
                # Check direct URL
                url = post_data.get('url', '')
                if url and ('v.redd.it' in url or '.mp4' in url):
                    video_urls.append(url)
    
    except Exception as e:
        print(f"    ⚠️ JSON parsing error: {e}")
    
    return list(set(video_urls))  # Remove duplicates

def test_reddit_comprehensive():
    """Run comprehensive Reddit download tests"""
    print("🧪 COMPREHENSIVE REDDIT VIDEO DOWNLOAD TEST")
    print("=" * 50)
    
    results = {
        'direct_downloads': 0,
        'json_extractions': 0,
        'total_tests': 0,
        'errors': []
    }
    
    # Test direct video downloads
    print("\n📹 TESTING DIRECT VIDEO DOWNLOADS")
    print("-" * 30)
    
    direct_video_urls = [url for url in test_urls if 'v.redd.it' in url]
    for url in direct_video_urls:
        results['total_tests'] += 1
        if test_direct_video_download(url):
            results['direct_downloads'] += 1
    
    # Test JSON extraction
    print("\n🔍 TESTING JSON EXTRACTION")
    print("-" * 30)
    
    reddit_post_urls = [url for url in test_urls if 'reddit.com' in url and 'v.redd.it' not in url]
    for url in reddit_post_urls:
        results['total_tests'] += 1
        video_url = test_reddit_json_extraction(url)
        if video_url:
            results['json_extractions'] += 1
            # Test the extracted video URL
            print(f"\n🎬 Testing extracted video URL: {video_url}")
            if test_direct_video_download(video_url):
                print(f"  ✅ Extracted video download successful")
            else:
                print(f"  ❌ Extracted video download failed")
    
    # Print summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total tests: {results['total_tests']}")
    print(f"Direct downloads successful: {results['direct_downloads']}")
    print(f"JSON extractions successful: {results['json_extractions']}")
    
    if results['total_tests'] > 0:
        success_rate = ((results['direct_downloads'] + results['json_extractions']) / results['total_tests']) * 100
        print(f"Overall success rate: {success_rate:.1f}%")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 30)
    
    if results['direct_downloads'] > 0:
        print("✅ Direct video downloads are working well")
    else:
        print("❌ Direct video downloads need improvement")
    
    if results['json_extractions'] > 0:
        print("✅ JSON extraction is working")
    else:
        print("⚠️ JSON extraction may need fallback strategies")
    
    print("\n🔧 SUGGESTED IMPROVEMENTS:")
    print("1. Add more user agents for better anti-detection")
    print("2. Implement proxy rotation for rate limiting")
    print("3. Add audio track merging for DASH videos")
    print("4. Implement caching for repeated requests")
    print("5. Add quality selection (480p, 720p, 1080p)")
    print("6. Improve error handling with specific error codes")

if __name__ == "__main__":
    test_reddit_comprehensive()