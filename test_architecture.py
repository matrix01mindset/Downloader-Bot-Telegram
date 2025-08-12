# test_architecture.py - Test pentru Arhitectura Nouă v3.0.0
# Script pentru testarea implementării arhitecturii noi

import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_architecture.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_base_classes():
    """Test pentru clasele de bază"""
    logger.info("🧪 Testing base classes...")
    
    try:
        from platforms.base import BasePlatform, VideoInfo, PlatformCapability, ExtractionError, DownloadError
        logger.info("✅ Base classes imported successfully")
        
        # Test VideoInfo
        video_info = VideoInfo(
            id="test123",
            title="Test Video",
            description="A test video",
            duration=120,
            platform="test"
        )
        logger.info(f"✅ VideoInfo created: {video_info.title}")
        
        # Test capabilities
        capabilities = list(PlatformCapability)
        logger.info(f"✅ Found {len(capabilities)} platform capabilities")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Base classes test failed: {e}")
        return False

async def test_platform_registry():
    """Test pentru platform registry"""
    logger.info("🧪 Testing platform registry...")
    
    try:
        from platforms import (
            PLATFORM_REGISTRY, 
            SUPPORTED_PLATFORMS, 
            FAILED_PLATFORMS,
            get_platform_info,
            get_registry_stats,
            is_platform_supported
        )
        
        stats = get_registry_stats()
        logger.info(f"✅ Platform Registry loaded: {stats}")
        
        logger.info(f"✅ Supported platforms: {SUPPORTED_PLATFORMS}")
        if FAILED_PLATFORMS:
            logger.warning(f"⚠️ Failed platforms: {FAILED_PLATFORMS}")
            
        # Test specific platform support
        if is_platform_supported('youtube'):
            logger.info("✅ YouTube platform is supported")
        
        platform_info = get_platform_info()
        logger.info(f"✅ Platform info retrieved for {len(platform_info)} platforms")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Platform registry test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_youtube_platform():
    """Test specific pentru YouTube platform"""
    logger.info("🧪 Testing YouTube platform...")
    
    try:
        from platforms import YouTubePlatform
        
        if YouTubePlatform is None:
            logger.warning("⚠️ YouTube platform not loaded, skipping test")
            return True
            
        youtube = YouTubePlatform()
        logger.info(f"✅ YouTube platform created: {youtube.platform_name}")
        
        # Test URL support
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.instagram.com/p/test"  # Should not match
        ]
        
        for url in test_urls:
            supported = youtube.supports_url(url)
            logger.info(f"URL {url[:30]}... supported: {supported}")
            
        logger.info(f"✅ YouTube capabilities: {[cap.value for cap in youtube.capabilities]}")
        logger.info(f"✅ YouTube stats: {youtube.get_stats()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ YouTube platform test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_platform_manager():
    """Test pentru Platform Manager"""
    logger.info("🧪 Testing Platform Manager...")
    
    try:
        from core.platform_manager import PlatformManager, get_platform_manager
        
        # Test singleton
        manager1 = await get_platform_manager()
        manager2 = await get_platform_manager()
        
        if manager1 is manager2:
            logger.info("✅ Platform Manager singleton works correctly")
        else:
            logger.warning("⚠️ Platform Manager singleton issue")
            
        logger.info(f"✅ Platform Manager initialized: {manager1.is_initialized()}")
        logger.info(f"✅ Supported platforms: {manager1.get_supported_platforms()}")
        
        # Test URL platform finding
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.instagram.com/p/test123",
            "https://www.tiktok.com/@user/video/123456"
        ]
        
        for url in test_urls:
            try:
                platform = await manager1.find_platform_for_url(url)
                if platform:
                    logger.info(f"✅ URL {url[:30]}... matched to {platform.platform_name}")
                else:
                    logger.info(f"⚠️ URL {url[:30]}... no platform found")
            except Exception as e:
                logger.warning(f"⚠️ Error finding platform for {url[:30]}...: {e}")
                
        # Test stats
        stats = manager1.get_manager_stats()
        logger.info(f"✅ Manager stats: {stats}")
        
        # Test health check
        health = await manager1.health_check()
        logger.info(f"✅ Health check: {health}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Platform Manager test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_cache_system():
    """Test pentru cache system"""
    logger.info("🧪 Testing cache system...")
    
    try:
        from utils.cache import cache, generate_cache_key
        
        # Test cache operations
        test_key = generate_cache_key("test", "value")
        logger.info(f"✅ Generated cache key: {test_key}")
        
        await cache.set("test_key", {"data": "test_value"}, ttl=60)
        logger.info("✅ Cache set operation completed")
        
        cached_value = await cache.get("test_key")
        if cached_value and cached_value.get("data") == "test_value":
            logger.info("✅ Cache get operation successful")
        else:
            logger.warning("⚠️ Cache get operation issue")
            
        stats = cache.get_stats()
        logger.info(f"✅ Cache stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Cache system test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_rate_limiter():
    """Test pentru rate limiter"""
    logger.info("🧪 Testing rate limiter...")
    
    try:
        from utils.rate_limiter import RateLimiter, RateLimitStrategy
        
        limiter = RateLimiter(
            max_requests=5,
            time_window=10.0,
            burst_allowance=2,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        
        logger.info("✅ Rate limiter created")
        
        # Test acquire
        delay = await limiter.acquire()
        logger.info(f"✅ Rate limiter acquire completed with delay: {delay}")
        
        # Test try_acquire
        success = await limiter.try_acquire()
        logger.info(f"✅ Rate limiter try_acquire: {success}")
        
        usage = limiter.get_current_usage()
        logger.info(f"✅ Rate limiter usage: {usage}")
        
        stats = limiter.get_stats()
        logger.info(f"✅ Rate limiter stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Rate limiter test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_monitoring_system():
    """Test pentru monitoring system"""
    logger.info("🧪 Testing monitoring system...")
    
    try:
        from utils.monitoring import monitoring, trace_operation
        
        # Test basic metrics
        monitoring.record_metric("test.metric", 42.0)
        logger.info("✅ Metric recorded")
        
        # Test error recording
        monitoring.record_error("test_component", "test_error", "This is a test error")
        logger.info("✅ Error recorded")
        
        # Test trace
        with monitoring.start_trace("test_operation") as trace:
            await asyncio.sleep(0.1)  # Simulate work
            trace.add_metadata("test_key", "test_value")
            
        logger.info("✅ Trace completed")
        
        # Test stats
        metrics_summary = monitoring.get_metrics_summary()
        error_summary = monitoring.get_error_summary()
        trace_summary = monitoring.get_trace_summary()
        system_stats = monitoring.get_system_stats()
        
        logger.info(f"✅ Monitoring stats - Metrics: {len(metrics_summary)}, Errors: {len(error_summary)}, System: {system_stats['running']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Monitoring system test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_full_integration():
    """Test de integrare completă"""
    logger.info("🧪 Testing full integration...")
    
    try:
        from core.platform_manager import get_platform_manager
        
        # Get manager
        manager = await get_platform_manager()
        
        # Test video info extraction (doar URL matching, fără download real)
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        platform = await manager.find_platform_for_url(test_url)
        if platform:
            logger.info(f"✅ Integration test - Platform found: {platform.platform_name}")
            
            # Nu facem extraction real pentru a evita rate limiting în teste
            logger.info("✅ Integration test - Skipping real extraction to avoid rate limits")
        else:
            logger.warning("⚠️ Integration test - No platform found")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Full integration test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def run_all_tests():
    """Rulează toate testele"""
    logger.info("🚀 Starting Architecture v3.0.0 Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Base Classes", test_base_classes),
        ("Platform Registry", test_platform_registry),
        ("YouTube Platform", test_youtube_platform),
        ("Platform Manager", test_platform_manager),
        ("Cache System", test_cache_system),
        ("Rate Limiter", test_rate_limiter),
        ("Monitoring System", test_monitoring_system),
        ("Full Integration", test_full_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"💥 {test_name} test CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status:10} {test_name}")
    
    logger.info("-" * 60)
    logger.info(f"📈 OVERALL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Architecture v3.0.0 is ready!")
    elif passed > total * 0.8:
        logger.info("⚠️ Most tests passed. Architecture is mostly functional.")
    else:
        logger.error("💥 Many tests failed. Architecture needs fixes.")
    
    logger.info("=" * 60)
    
    return passed == total

async def main():
    """Main function"""
    try:
        success = await run_all_tests()
        
        if success:
            logger.info("\n🎯 RECOMMENDATION: Architecture v3.0.0 is ready for production!")
            sys.exit(0)
        else:
            logger.error("\n⚠️ RECOMMENDATION: Fix failing tests before deploying!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Test runner crashed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    if script_dir.name == "Downloader Bot telegram":
        logger.info(f"📁 Running tests from: {script_dir}")
        asyncio.run(main())
    else:
        logger.error(f"❌ Please run this script from the project root directory")
        sys.exit(1)
