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
from platforms.base import BasePlatform, DownloadResult


class MockPlatform(BasePlatform):
    """Mock platform pentru testing"""
    
    def __init__(self, name: str = "mock", should_fail: bool = False):
        super().__init__(name)
        self.platform_name = name
        self.should_fail = should_fail
        self.supported_domains = [f"{name}.com"]
        self.enabled = True  # Explicit enable
        
    async def is_supported_url(self, url: str) -> bool:
        return f"{self.platform_name}.com" in url
        
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
        
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        if self.should_fail:
            return DownloadResult(
                success=False,
                error="Mock download failure",
                platform=self.platform_name
            )
        return DownloadResult(
            success=True,
            file_path=output_path,
            platform=self.platform_name,
            metadata={'title': 'Mock Video'}
        )


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
        assert hasattr(manager, 'download_stats')
        assert hasattr(manager, 'rate_limits')
        assert hasattr(manager, 'metadata_cache')
        
    def test_get_supported_platforms(self, manager):
        """Test obținerea platformelor suportate"""
        platforms = manager.get_supported_platforms()
        assert isinstance(platforms, list)
        
    def test_url_validation(self, manager):
        """Test validarea URL-urilor"""
        # Test URL valid
        valid_url = "https://www.example.com/video"
        assert manager._validate_url(valid_url) is True
        
        # Test URL-uri invalid
        invalid_urls = [
            "",
            None,
            "not_a_url",
            "ftp://example.com",
            "x" * 3000  # URL prea lung
        ]
        
        for invalid_url in invalid_urls:
            assert manager._validate_url(invalid_url) is False
    
    @pytest.mark.asyncio        
    async def test_rate_limiting(self, manager):
        """Test rate limiting"""
        user_id = 123
        
        # Primele 5 request-uri ar trebui să treacă
        for i in range(5):
            result = await manager._check_rate_limit(user_id)
            assert result is True
            
        # Al 6-lea request ar trebui să fie blocat
        result = await manager._check_rate_limit(user_id)
        assert result is False
        
    @pytest.mark.asyncio
    async def test_get_platform_for_url(self, manager):
        """Test găsirea platformei pentru URL"""
        # Mock o platformă în manager
        mock_platform = MockPlatform("testplatform")
        manager.platforms['test'] = mock_platform
        
        # Test URL care match-uiește
        platform = await manager.get_platform_for_url("https://testplatform.com/video/123")
        assert platform == mock_platform
        
        # Test URL care nu match-uiește
        platform = await manager.get_platform_for_url("https://unknown.com/video/123")
        assert platform is None
        
    @pytest.mark.asyncio
    async def test_download_video_success(self, manager):
        """Test download video cu succes"""
        # Mock o platformă în manager
        mock_platform = MockPlatform("testplatform")
        manager.platforms['test'] = mock_platform
        
        # Patch extract_metadata și process_download_with_retry
        with patch.object(mock_platform, 'extract_metadata', new=AsyncMock(return_value={'title': 'Test Video'})):
            with patch.object(mock_platform, 'process_download_with_retry', new=AsyncMock(return_value=DownloadResult(success=True, file_path='/tmp/test.mp4', platform='testplatform'))):
                result = await manager.download_video("https://testplatform.com/video/123")
                
                assert result.success is True
                assert result.platform == 'testplatform'
        
    @pytest.mark.asyncio
    async def test_download_video_no_platform(self, manager):
        """Test download video fără platformă"""
        result = await manager.download_video("https://unknown.com/video/123")
        
        assert result.success is False
        assert "nu este suportată" in result.error
        
    @pytest.mark.asyncio
    async def test_download_video_invalid_url(self, manager):
        """Test download video cu URL invalid"""
        result = await manager.download_video("invalid_url")
        
        assert result.success is False
        assert "URL invalid" in result.error
        
    @pytest.mark.asyncio  
    async def test_download_video_rate_limited(self, manager):
        """Test download video cu rate limiting"""
        user_id = 999
        
        # Consumă toate request-urile permise
        for i in range(5):
            await manager._check_rate_limit(user_id)
            
        # Următorul download ar trebui să fie rate limited
        result = await manager.download_video("https://example.com/video", user_id)
        
        assert result.success is False
        assert "Prea multe request-uri" in result.error
        
    @pytest.mark.asyncio
    async def test_metadata_caching(self, manager):
        """Test caching pentru metadata"""
        url = "https://example.com/video/123"
        metadata = {'title': 'Test Video', 'duration': 120}
        
        # Salvează în cache
        await manager._cache_metadata(url, metadata)
        
        # Obține din cache
        cached_metadata = await manager._get_cached_metadata(url)
        assert cached_metadata == metadata
        
        # Test cache miss
        cached_metadata = await manager._get_cached_metadata("https://other.com/video")
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
        mock_platform.extract_metadata = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        manager.platforms['error'] = mock_platform
        
        result = await manager.download_video("https://error.com/video/123")
        
        # Ar trebui să returneze un rezultat cu eroare, nu să arunce excepție
        assert result.success is False
        assert 'Unexpected error' in result.error or 'Eroare neașteptată' in result.error


if __name__ == "__main__":
    # Rulează testele direct
    pytest.main([__file__, "-v"])
