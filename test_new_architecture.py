# test_new_architecture.py - Test pentru noua arhitectură modulară
# Versiunea: 2.0.0

import asyncio
import logging
import sys
import os

# Setup logging pentru test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_configuration():
    """Testează modulul de configurație"""
    print("🔧 Testing Configuration Module...")
    
    try:
        from utils.config import config
        
        # Test basic functionality
        app_name = config.get('app.name', 'Unknown')
        print(f"  ✅ App name: {app_name}")
        
        # Test platform configs
        youtube_config = config.get_platform_config('youtube')
        print(f"  ✅ YouTube config: enabled={youtube_config.get('enabled')}, priority={youtube_config.get('priority')}")
        
        # Test enabled platforms
        enabled_platforms = config.get_enabled_platforms()
        print(f"  ✅ Enabled platforms: {enabled_platforms}")
        
        print("  ✅ Configuration module works!")
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

async def test_base_platform():
    """Testează clasa BasePlatform"""
    print("🏗️ Testing Base Platform...")
    
    try:
        from platforms.base import BasePlatform, DownloadResult
        
        # Test DownloadResult
        result = DownloadResult(
            success=True,
            file_path="/tmp/test.mp4",
            metadata={'title': 'Test Video', 'duration': 120},
            platform='test'
        )
        
        print(f"  ✅ DownloadResult created: {result}")
        print(f"  ✅ Result dict: {result.to_dict()}")
        
        print("  ✅ Base Platform classes work!")
        return True
        
    except Exception as e:
        print(f"  ❌ Base Platform test failed: {e}")
        return False

async def test_youtube_platform():
    """Testează platforma YouTube"""
    print("🎬 Testing YouTube Platform...")
    
    try:
        from platforms.youtube import youtube_platform
        
        # Test URL support checking
        youtube_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://m.youtube.com/watch?v=dQw4w9WgXcQ'
        ]
        
        non_youtube_urls = [
            'https://www.tiktok.com/@user/video/123456789',
            'https://www.instagram.com/p/ABC123/',
            'https://www.facebook.com/watch/?v=123456789'
        ]
        
        # Test URL matching
        for url in youtube_urls:
            is_supported = await youtube_platform.is_supported_url(url)
            if is_supported:
                print(f"  ✅ Correctly identified YouTube URL: {url[:50]}...")
            else:
                print(f"  ❌ Failed to identify YouTube URL: {url[:50]}...")
                return False
        
        for url in non_youtube_urls:
            is_supported = await youtube_platform.is_supported_url(url)
            if not is_supported:
                print(f"  ✅ Correctly rejected non-YouTube URL: {url[:50]}...")
            else:
                print(f"  ❌ Incorrectly accepted non-YouTube URL: {url[:50]}...")
                return False
        
        # Test platform health
        health = await youtube_platform.get_platform_health()
        print(f"  ✅ YouTube platform health: {health['status']}")
        
        print("  ✅ YouTube Platform works!")
        return True
        
    except Exception as e:
        print(f"  ❌ YouTube Platform test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_platform_manager():
    """Testează Platform Manager"""
    print("🚀 Testing Platform Manager...")
    
    try:
        from core.platform_manager import platform_manager
        
        # Test platform discovery
        supported_platforms = platform_manager.get_supported_platforms()
        print(f"  ✅ Supported platforms: {supported_platforms}")
        
        # Test URL matching
        test_urls = {
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ': 'youtube',
            'https://youtu.be/dQw4w9WgXcQ': 'youtube',
            'https://www.tiktok.com/@user/video/123': None,  # Nu este implementat încă
            'invalid_url': None
        }
        
        for url, expected_platform in test_urls.items():
            platform = await platform_manager.get_platform_for_url(url)
            platform_name = platform.name if platform else None
            
            if expected_platform:
                if platform_name == expected_platform:
                    print(f"  ✅ URL correctly matched to {platform_name}: {url[:50]}...")
                else:
                    print(f"  ❌ URL match failed. Expected: {expected_platform}, Got: {platform_name}")
                    return False
            else:
                if platform is None:
                    print(f"  ✅ URL correctly rejected: {url[:50]}...")
                else:
                    print(f"  ❌ URL should have been rejected but matched to: {platform_name}")
        
        # Test health status
        health = await platform_manager.get_health_status()
        print(f"  ✅ System health: {health['overall_status']}")
        print(f"  ✅ Enabled platforms: {health['enabled_platforms']}/{health['total_platforms']}")
        
        print("  ✅ Platform Manager works!")
        return True
        
    except Exception as e:
        print(f"  ❌ Platform Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration():
    """Test de integrare completă"""
    print("🔗 Testing Full Integration...")
    
    try:
        from core.platform_manager import platform_manager
        
        # Test cu un URL YouTube real (fără a descărca efectiv)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - sigur că există
        
        print(f"  🔍 Testing integration with URL: {test_url}")
        
        # Test only URL matching and platform detection
        platform = await platform_manager.get_platform_for_url(test_url)
        
        if platform:
            print(f"  ✅ Platform detected: {platform.name}")
            
            # Test rate limiting
            user_id = 12345
            can_download = await platform_manager._check_rate_limit(user_id)
            print(f"  ✅ Rate limiting works: {can_download}")
            
            print("  ✅ Integration test passed!")
            return True
        else:
            print("  ❌ No platform found for test URL")
            return False
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Rulează toate testele"""
    print("🧪 STARTING ARCHITECTURE TESTS")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration()),
        ("Base Platform", test_base_platform()),
        ("YouTube Platform", test_youtube_platform()),
        ("Platform Manager", test_platform_manager()),
        ("Integration", test_integration())
    ]
    
    results = []
    
    for test_name, test_coro in tests:
        print(f"\n🔬 Running {test_name} test...")
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🏆 SUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The new architecture is working correctly!")
        return True
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    try:
        # Rulează testele
        success = asyncio.run(run_all_tests())
        
        if success:
            print("\n✅ ARCHITECTURE VALIDATION SUCCESSFUL!")
            print("🚀 Ready to proceed with implementation!")
            sys.exit(0)
        else:
            print("\n❌ ARCHITECTURE VALIDATION FAILED!")
            print("🔧 Fix the issues above before proceeding.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
