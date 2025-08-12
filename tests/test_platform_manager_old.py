# tests/test_platform_manager.py - Unit tests for Platform Manager
# Versiunea: 2.0.0 - Arhitectura Modulară

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
        
    def supports_url(self, url: str) -> bool:
        return f"{self.platform_name}.com" in url
        
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
            'uploader_id': "mock_uploader_123",
            'uploader_url': f"https://{self.platform_name}.com/mock_uploader",
            'upload_date': "2023-12-01T10:00:00Z",
            'view_count': 1000,
            'like_count': 100,
            'comment_count': 50,
            'thumbnail': "https://mock.thumbnail.url/image.jpg",
            'webpage_url': url,
            'formats': [{
                'url': 'https://mock.video.url/video.mp4',
                'format_id': 'mp4',
                'ext': 'mp4',
                'quality': '720p',
                'filesize': 10485760  # 10MB
            }],
            'platform': self.platform_name,
            'platform_id': "mock_123"
        }
        
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        if self.should_fail:
            return DownloadResult(
                success=False,
                error="Mock download failure",
                platform=self.platform_name
            )
        file_path = f"{output_path}/mock_video.mp4"
        return DownloadResult(
            success=True,
            file_path=file_path,
            platform=self.platform_name
        )


class TestPlatformManager:
    """Test suite pentru PlatformManager"""
    
    @pytest.fixture
    def manager(self):
        """Crează o instanță fresh de PlatformManager pentru fiecare test"""
        pm = PlatformManager()
        pm.platforms = {}  # Reset platforms
        pm.circuit_breakers = {}  # Reset circuit breakers
        return pm
        
    @pytest.fixture
    def mock_platform(self):
        """Crează o platformă mock pentru testing"""
        return MockPlatform("testplatform")
        
    @pytest.fixture
    def failing_platform(self):
        """Crează o platformă mock care eșuează"""
        return MockPlatform("failplatform", should_fail=True)
        
    def test_register_platform(self, manager, mock_platform):
        """Test înregistrarea unei platforme"""
        manager.register_platform("test", mock_platform)
        
        assert "test" in manager.platforms
        assert manager.platforms["test"] == mock_platform
        
    def test_register_duplicate_platform(self, manager, mock_platform):
        """Test înregistrarea unei platforme duplicate"""
        manager.register_platform("test", mock_platform)
        
        # Înregistrează din nou - ar trebui să înlocuiască
        new_platform = MockPlatform("newtest")
        manager.register_platform("test", new_platform)
        
        assert manager.platforms["test"] == new_platform
        
    def test_unregister_platform(self, manager, mock_platform):
        """Test dezînregistrarea unei platforme"""
        manager.register_platform("test", mock_platform)
        assert "test" in manager.platforms
        
        result = manager.unregister_platform("test")
        assert result is True
        assert "test" not in manager.platforms
        
    def test_unregister_nonexistent_platform(self, manager):
        """Test dezînregistrarea unei platforme inexistente"""
        result = manager.unregister_platform("nonexistent")
        assert result is False
        
    def test_detect_platform_success(self, manager, mock_platform):
        """Test detecția cu succes a unei platforme"""
        manager.register_platform("test", mock_platform)
        
        platform = manager.detect_platform("https://testplatform.com/video/123")
        assert platform == mock_platform
        
    def test_detect_platform_not_found(self, manager, mock_platform):
        """Test detecția când nu se găsește platforma"""
        manager.register_platform("test", mock_platform)
        
        platform = manager.detect_platform("https://unknownplatform.com/video/123")
        assert platform is None
        
    def test_detect_platform_multiple_matches(self, manager):
        """Test detecția când mai multe platforme match"""
        # Creează două platforme care match același URL pattern
        platform1 = MockPlatform("platform1")
        platform1.supports_url = lambda url: "shared.com" in url
        
        platform2 = MockPlatform("platform2") 
        platform2.supports_url = lambda url: "shared.com" in url
        
        manager.register_platform("p1", platform1)
        manager.register_platform("p2", platform2)
        
        # Ar trebui să returneze prima înregistrată
        platform = manager.detect_platform("https://shared.com/video/123")
        assert platform == platform1
        
    @pytest.mark.asyncio
    async def test_get_video_info_success(self, manager, mock_platform):
        """Test obținerea info video cu succes"""
        manager.register_platform("test", mock_platform)
        
        video_info = await manager.get_video_info("https://testplatform.com/video/123")
        
        assert video_info is not None
        assert video_info['id'] == "mock_video_123"
        assert video_info['platform'] == "testplatform"
        assert video_info['title'] == "Mock Video Title"
        
    @pytest.mark.asyncio
    async def test_get_video_info_platform_not_found(self, manager, mock_platform):
        """Test obținerea info când platforma nu e găsită"""
        manager.register_platform("test", mock_platform)
        
        with pytest.raises(Exception) as exc_info:
            await manager.get_video_info("https://unknownplatform.com/video/123")
            
        assert "No platform found" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_get_video_info_platform_failure(self, manager, failing_platform):
        """Test obținerea info când platforma eșuează"""
        manager.register_platform("fail", failing_platform)
        
        with pytest.raises(Exception) as exc_info:
            await manager.get_video_info("https://failplatform.com/video/123")
            
        assert "Mock platform failure" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_download_video_success(self, manager, mock_platform):
        """Test descărcarea video cu succes"""
        manager.register_platform("test", mock_platform)
        
        # Mai întâi obține video info
        video_info = await manager.get_video_info("https://testplatform.com/video/123")
        
        # Apoi descarcă
        file_path = await manager.download_video(video_info, "/tmp/downloads")
        
        assert file_path == "/tmp/downloads/mock_video.mp4"
        
    @pytest.mark.asyncio
    async def test_download_video_failure(self, manager, failing_platform):
        """Test descărcarea video când eșuează"""
        manager.register_platform("fail", failing_platform)
        
        # Test descărcare directă cu URL
        result = await failing_platform.download_video("https://failplatform.com/video/123", "/tmp/downloads")
        
        assert result.success is False
        assert "Mock download failure" in result.error
        
    @pytest.mark.asyncio
    async def test_get_available_platforms(self, manager):
        """Test obținerea listei de platforme disponibile"""
        platform1 = MockPlatform("platform1")
        platform2 = MockPlatform("platform2")
        
        manager.register_platform("p1", platform1)
        manager.register_platform("p2", platform2)
        
        platforms = await manager.get_available_platforms()
        
        assert len(platforms) == 2
        assert "p1" in platforms
        assert "p2" in platforms
        assert platforms["p1"]["name"] == "platform1"
        assert platforms["p2"]["name"] == "platform2"
        
        
    def test_circuit_breaker_initialization(self, manager, mock_platform):
        """Test inițializarea circuit breaker pentru platformă"""
        manager.register_platform("test", mock_platform)
        
        # Circuit breaker ar trebui să fie creat la înregistrare
        assert "test" in manager.circuit_breakers
        assert manager.circuit_breakers["test"].failure_count == 0
        assert manager.circuit_breakers["test"].state == "closed"
        
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_tracking(self, manager, failing_platform):
        """Test urmărirea erorilor în circuit breaker"""
        manager.register_platform("fail", failing_platform)
        
        # Încearcă să obții video info și eșuează
        with pytest.raises(Exception):
            await manager.get_video_info("https://failplatform.com/video/123")
            
        # Circuit breaker ar trebui să înregistreze eroarea
        cb = manager.circuit_breakers["fail"]
        assert cb.failure_count > 0
        
    @pytest.mark.asyncio
    async def test_batch_download(self, manager, mock_platform):
        """Test descărcarea în batch"""
        manager.register_platform("test", mock_platform)
        
        urls = [
            "https://testplatform.com/video/1",
            "https://testplatform.com/video/2", 
            "https://testplatform.com/video/3"
        ]
        
        with patch.object(manager, 'download_video', new=AsyncMock(return_value="/tmp/video.mp4")) as mock_download:
            results = await manager.batch_download(urls, "/tmp/downloads")
            
            assert len(results) == 3
            assert all(result['success'] for result in results)
            assert mock_download.call_count == 3
            
    @pytest.mark.asyncio
    async def test_batch_download_with_failures(self, manager):
        """Test batch download cu unele eșecuri"""
        # Înregistrează platforme mixte
        good_platform = MockPlatform("good")
        bad_platform = MockPlatform("bad", should_fail=True)
        
        manager.register_platform("good", good_platform)
        manager.register_platform("bad", bad_platform)
        
        urls = [
            "https://good.com/video/1",
            "https://bad.com/video/2",
            "https://good.com/video/3"
        ]
        
        results = await manager.batch_download(urls, "/tmp/downloads", max_concurrent=2)
        
        assert len(results) == 3
        assert results[0]['success'] is True  # good platform
        assert results[1]['success'] is False  # bad platform
        assert results[2]['success'] is True  # good platform
        
    def test_platform_stats_tracking(self, manager, mock_platform):
        """Test urmărirea statisticilor pentru platforme"""
        manager.register_platform("test", mock_platform)
        
        # Statisticile inițiale
        stats = manager.get_platform_stats("test")
        assert stats['total_requests'] == 0
        assert stats['successful_requests'] == 0
        assert stats['failed_requests'] == 0


class TestCircuitBreaker:
    """Test suite pentru Circuit Breaker logic"""
    
    def test_circuit_breaker_states(self):
        """Test tranzițiile de stare ale circuit breaker"""
        from core.platform_manager import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # Starea inițială
        assert cb.state == "closed"
        assert cb.failure_count == 0
        
        # Înregistrează eșecuri
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"  # Sub threshold
        
        cb.record_failure()
        assert cb.state == "open"  # Peste threshold
        
    def test_circuit_breaker_success_reset(self):
        """Test resetarea circuit breaker la succes"""
        from core.platform_manager import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # Generează eșecuri
        cb.record_failure()
        cb.record_failure()
        
        # Success ar trebui să reseteze counter-ul
        cb.record_success()
        assert cb.failure_count == 0
        
    def test_circuit_breaker_can_execute(self):
        """Test logica de execuție pentru circuit breaker"""
        from core.platform_manager import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=2, timeout=1)  # 1 secondă timeout
        
        # Stare closed - poate executa
        assert cb.can_execute() is True
        
        # Deschide circuit breaker
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
        
        # Așteaptă timeout și testează half-open
        import time
        time.sleep(1.1)  # Peste timeout
        assert cb.can_execute() is True  # Half-open permite o încercare


@pytest.mark.integration
class TestPlatformManagerIntegration:
    """Teste de integrare pentru PlatformManager"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_success(self):
        """Test workflow complet de succes"""
        manager = PlatformManager()
        mock_platform = MockPlatform("integration")
        
        # Înregistrează platforma
        manager.register_platform("test", mock_platform)
        
        # Workflow complet
        url = "https://integration.com/video/123"
        
        # 1. Detectează platforma
        platform = manager.detect_platform(url)
        assert platform is not None
        
        # 2. Obține video info
        video_info = await manager.get_video_info(url)
        assert video_info is not None
        
        # 3. Descarcă video
        file_path = await manager.download_video(video_info, "/tmp/downloads")
        assert file_path is not None
        
        # 4. Verifică statistici
        stats = manager.get_platform_stats("test")
        assert stats['total_requests'] > 0


if __name__ == "__main__":
    # Rulează testele direct
    pytest.main([__file__, "-v"])
