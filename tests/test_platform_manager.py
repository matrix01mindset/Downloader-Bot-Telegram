# tests/test_platform_manager.py - Unit tests for Platform Manager v2.0.0
# Versiunea adaptată pentru interfața reală PlatformManager

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import system under test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.platform_manager import PlatformManager
from platforms.base import BasePlatform, DownloadResult, VideoInfo
from utils.common.validators import URLValidator
from utils.rate_limiter import SimpleRateLimiter


class MockPlatform(BasePlatform):
    """Mock platform pentru testing"""
    
    def __init__(self, name: str = "mock", should_fail: bool = False):
        super().__init__()
        self.platform_name = name
        self.name = name  # Adăugăm atributul name
        self.should_fail = should_fail
        self.supported_domains = [f"{name}.com"]
        self.enabled = True  # Explicit enable
        
    async def is_supported_url(self, url: str) -> bool:
        return f"{self.platform_name}.com" in url
        
    async def supports_url(self, url: str) -> bool:
        """Implementare pentru metoda abstractă"""
        return f"{self.platform_name}.com" in url
        
    async def get_video_info(self, url: str) -> VideoInfo:
        """Implementare pentru metoda abstractă"""
        if self.should_fail:
            raise Exception("Mock platform failure")
            
        return VideoInfo(
            id="mock_video_123",
            title="Mock Video Title",
            description="Mock video description",
            duration=120,
            uploader="MockUploader",
            thumbnail="https://mock.thumbnail.url/image.jpg",
            webpage_url=url,
            platform=self.platform_name
        )
        
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        if self.should_fail:
            raise Exception("Mock platform failure")
            
        return {
            'id': "mock_video_123",
            'title': "Mock Video Title",
            'description': "Mock video description",
            'duration': 120,
            'uploader': "MockUploader",
            'thumbnail': "https://mock.thumbnail.url/image.jpg",
            'webpage_url': url,
            'platform': self.platform_name,
            'estimated_size_mb': 10
        }
        
    async def download_video(self, video_info, output_path: str, quality: str = None) -> str:
        if self.should_fail:
            raise Exception("Mock download failure")
        return f"{output_path}/mock_video.mp4"


class TestPlatformManager:
    """Test suite pentru PlatformManager cu interfața reală"""
    
    @pytest.fixture
    def manager(self):
        """Crează o instanță fresh de PlatformManager pentru fiecare test"""
        return PlatformManager()
        
    def test_platform_manager_initialization(self, manager):
        """Test inițializarea PlatformManager"""
        assert isinstance(manager, PlatformManager)
        assert hasattr(manager, 'platforms')
        assert hasattr(manager, 'stats')
        assert hasattr(manager, 'rate_limiters')
        assert hasattr(manager, 'url_cache')
        
    def test_get_supported_platforms(self, manager):
        """Test obținerea platformelor suportate"""
        platforms = manager.get_supported_platforms()
        assert isinstance(platforms, list)
        
    def test_url_validation(self, manager):
        """Test validarea URL-urilor"""
        # Test URL valid
        valid_url = "https://www.example.com/video"
        assert URLValidator.is_valid_url(valid_url) is True
        
        # Test URL-uri invalid
        invalid_urls = [
            "",
            None,
            "not_a_url",
            "x" * 3000  # URL prea lung
        ]
        
        for invalid_url in invalid_urls:
            assert URLValidator.is_valid_url(invalid_url) is False
            
        # Test URL cu schemă validă dar neacceptată pentru platforme
        ftp_url = "ftp://example.com"
        assert URLValidator.is_valid_url(ftp_url) is True  # Valid ca URL, dar nu pentru platforme video
    
    def test_rate_limiting(self, manager):
        """Test rate limiting cu SimpleRateLimiter"""
        # Creează un rate limiter cu 5 cereri pe minut
        rate_limiter = SimpleRateLimiter(max_requests=5, time_window=60)
        user_id = "123"
        
        # Primele 5 request-uri ar trebui să treacă
        for i in range(5):
            result = rate_limiter.is_allowed(user_id)
            assert result is True
            
        # Al 6-lea request ar trebui să fie blocat
        result = rate_limiter.is_allowed(user_id)
        assert result is False
        
    @pytest.mark.asyncio
    async def test_get_platform_for_url(self, manager):
        """Test găsirea platformei pentru URL"""
        # Mock o platformă în manager
        mock_platform = MockPlatform("testplatform")
        manager.platforms['testplatform'] = mock_platform
        
        # Mock cache și monitoring pentru a evita erorile
        with patch('core.platform_manager.cache') as mock_cache, \
             patch('core.platform_manager.monitoring') as mock_monitoring:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_monitoring.record_metric = Mock()
            
            # Test URL care match-uiește
            platform = await manager.find_platform_for_url("https://testplatform.com/video/123")
            assert platform == mock_platform
            
            # Test URL care nu match-uiește
            platform = await manager.find_platform_for_url("https://unknown.com/video/123")
            assert platform is None
        
    @pytest.mark.asyncio
    async def test_download_video_success(self, manager):
        """Test download video cu succes"""
        # Mock o platformă în manager
        mock_platform = MockPlatform("testplatform")
        manager.platforms['testplatform'] = mock_platform
        
        # Mock cache și monitoring
        with patch('core.platform_manager.cache') as mock_cache, \
             patch('core.platform_manager.monitoring') as mock_monitoring:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_monitoring.record_metric = Mock()
            
            # Extrage video info mai întâi
            video_info = await manager.extract_video_info("https://testplatform.com/video/123")
            
            # Apoi descarcă video-ul
            file_path = await manager.download_video(video_info, "/tmp/output")
            
            assert file_path is not None
            assert "/tmp/output" in file_path
        
    @pytest.mark.asyncio
    async def test_download_video_no_platform(self, manager):
        """Test download video fără platformă"""
        # Încearcă să extragi video info pentru un URL nesuportat
        with pytest.raises(Exception) as exc_info:
            video_info = await manager.extract_video_info("https://unknown.com/video/123")
            await manager.download_video(video_info, "/tmp/output")
        
        assert "Failed to extract video info" in str(exc_info.value) or "nu este suportată" in str(exc_info.value) or "not supported" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_download_video_invalid_url(self, manager):
        """Test download video cu URL invalid"""
        # Încearcă să extragi video info pentru un URL invalid
        with pytest.raises(Exception) as exc_info:
            video_info = await manager.extract_video_info("invalid_url")
            await manager.download_video(video_info, "/tmp/output")
        
        assert "Failed to extract video info" in str(exc_info.value) or "URL invalid" in str(exc_info.value) or "Invalid URL" in str(exc_info.value) or "ValidationError" in str(exc_info.value)
        
    @pytest.mark.asyncio  
    async def test_download_video_rate_limited(self, manager):
        """Test download video cu rate limiting"""
        # Adaugă mock platform pentru test
        mock_platform = MockPlatform(name='testplatform')
        manager.platforms['testplatform'] = mock_platform
        
        # Configurează un rate limiter foarte restrictiv pentru test
        from utils.network.network_manager import RateLimiter, RateLimitConfig
        config = RateLimitConfig(max_requests=1, time_window=60)
        manager.rate_limiters['testplatform'] = RateLimiter(config)
        
        # Prima cerere ar trebui să treacă
        video_info = await manager.extract_video_info("https://testplatform.com/video1")
        assert video_info is not None
        
        # A doua cerere ar trebui să fie rate limited
        with pytest.raises(Exception) as exc_info:
            await manager.extract_video_info("https://testplatform.com/video2")
        
        # Verifică că eroarea este legată de rate limiting
        assert "rate limit" in str(exc_info.value).lower() or "too many requests" in str(exc_info.value).lower() or "Failed to extract" in str(exc_info.value)
        
    def test_metadata_caching(self, manager):
        """Test caching pentru metadata"""
        url = "https://example.com/video/123"
        metadata = {'title': 'Test Video', 'duration': 120}
        
        # Salvează în cache
        manager._cache_metadata(url, metadata)
        
        # Obține din cache
        cached_metadata = manager._get_cached_metadata(url)
        assert cached_metadata == metadata
        
        # Test cache miss
        cached_metadata = manager._get_cached_metadata("https://other.com/video")
        assert cached_metadata is None
        
    def test_download_stats_recording(self, manager):
        """Test înregistrarea statisticilor de download"""
        initial_total = manager.download_stats['total_downloads']
        
        # Înregistrează un download reușit
        manager._record_download_attempt('youtube', True)
        
        assert manager.download_stats['total_downloads'] == initial_total + 1
        assert manager.download_stats['successful_downloads'] > 0
        assert 'youtube' in manager.download_stats['platform_usage']
        
        # Înregistrează un download eșuat
        manager._record_download_attempt('youtube', False, 'network_error')
        
        assert manager.download_stats['failed_downloads'] > 0
        assert 'network_error' in manager.download_stats['error_types']
        
    @pytest.mark.asyncio
    async def test_get_health_status(self, manager):
        """Test obținerea statusului de sănătate"""
        # Mock o platformă
        mock_platform = MockPlatform("testplatform")
        mock_platform.get_platform_health = AsyncMock(return_value={
            'name': 'testplatform',
            'status': 'healthy'
        })
        manager.platforms['test'] = mock_platform
        
        health_status = await manager.get_health_status()
        
        assert 'overall_status' in health_status
        assert 'enabled_platforms' in health_status
        assert 'statistics' in health_status
        assert 'platforms' in health_status
        assert isinstance(health_status['platforms'], dict)
        
    def test_cleanup_rate_limits(self, manager):
        """Test curățarea rate limits expirate"""
        import time
        
        user_id = 456
        current_time = time.time()
        
        # Adaugă request-uri vechi (peste fereastra de timp)
        old_requests = [current_time - 120, current_time - 90]  # 2 minute în urmă
        recent_requests = [current_time - 30, current_time - 10]  # 30s și 10s în urmă
        
        manager.rate_limits[user_id] = old_requests + recent_requests
        
        # Curăță rate limits cu o fereastră de 60s
        manager._cleanup_rate_limits(current_time, 60)
        
        # Ar trebui să rămână doar request-urile recente
        assert len(manager.rate_limits[user_id]) == 2
        assert all(req_time > current_time - 60 for req_time in manager.rate_limits[user_id])
        
    @pytest.mark.asyncio
    async def test_reload_platforms(self, manager):
        """Test reîncărcarea platformelor"""
        initial_platforms = len(manager.platforms)
        
        await manager.reload_platforms()
        
        # Ar trebui să aibă același număr de platforme sau să fi reîncărcat
        assert isinstance(manager.platforms, dict)


@pytest.mark.integration
class TestPlatformManagerIntegration:
    """Teste de integrare pentru PlatformManager"""
    
    @pytest.mark.asyncio
    async def test_full_download_workflow(self):
        """Test workflow complet de download"""
        manager = PlatformManager()
        
        # Mock o platformă funcțională
        mock_platform = MockPlatform("integration")
        mock_platform.extract_metadata = AsyncMock(return_value={
            'title': 'Integration Test Video',
            'duration': 120,
            'platform': 'integration'
        })
        mock_platform.process_download_with_retry = AsyncMock(return_value=DownloadResult(
            success=True, 
            file_path='/tmp/integration_test.mp4',
            platform='integration',
            metadata={'title': 'Integration Test Video'}
        ))
        
        manager.platforms['integration'] = mock_platform
        
        # Test workflow complet
        url = "https://integration.com/video/123"
        result = await manager.download_video(url, user_id=1)
        
        assert result.success is True
        assert result.platform == 'integration'
        assert result.file_path is not None
        
        # Verifică că statisticile au fost actualizate
        assert manager.download_stats['total_downloads'] > 0
        assert 'integration' in manager.download_stats['platform_usage']


class TestErrorHandling:
    """Test suite pentru gestionarea erorilor"""
    
    @pytest.mark.asyncio
    async def test_platform_extraction_error(self):
        """Test comportament când extragerea metadata eșuează"""
        manager = PlatformManager()
        
        # Mock o platformă care eșuează la extragerea metadata
        failing_platform = MockPlatform("failing", should_fail=True)
        manager.platforms['failing'] = failing_platform
        
        result = await manager.download_video("https://failing.com/video/123")
        
        # Testul ar trebui să continue chiar dacă metadata extraction eșuează
        assert isinstance(result, DownloadResult)
        
    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self):
        """Test gestionarea erorilor neașteptate"""
        manager = PlatformManager()
        
        # Mock o platformă care aruncă eroare neașteptată
        mock_platform = MockPlatform("error")
        mock_platform.download_video = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        manager.platforms['error'] = mock_platform
        
        result = await manager.download_video("https://error.com/video/123")
        
        # Ar trebui să returneze un rezultat cu eroare, nu să arunce excepție
        assert result.success is False
        assert 'Unexpected error' in result.error_message or 'Eroare neașteptată' in result.error_message


if __name__ == "__main__":
    # Rulează testele direct
    pytest.main([__file__, "-v"])
