# tests/conftest.py - Configurație globală pentru suite-ul de teste
# Versiunea: 2.0.0 - Arhitectura Modulară

import pytest
import asyncio
import tempfile
import shutil
import os
import sys
import logging
from pathlib import Path
from unittest.mock import Mock, patch

# Adaugă directorul root la Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Configurare logging pentru teste
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise în teste
    format='%(name)s - %(levelname)s - %(message)s'
)

# Supprimă logurile pentru biblioteci externe în timpul testelor
logging.getLogger('aiohttp').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)


@pytest.fixture(scope="session")
def event_loop():
    """Crează event loop pentru întreaga sesiune de teste"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Crează un director temporar pentru teste"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup după test
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_config():
    """Mock pentru sistemul de configurare"""
    config_data = {
        'app': {
            'name': 'test_app',
            'version': '2.0.0-test'
        },
        'performance': {
            'memory_limit_mb': 100,
            'cold_start_target': 10,
            'cache_size_mb': 10
        },
        'platforms': {
            'youtube': {
                'enabled': True,
                'po_token': 'test_po_token'
            },
            'instagram': {
                'enabled': True
            },
            'tiktok': {
                'enabled': True
            }
        },
        'cache': {
            'default_ttl': 3600,
            'cleanup_interval': 300
        },
        'monitoring': {
            'interval': 30,
            'enabled': True
        },
        'rate_limiting': {
            'requests_per_minute': 60,
            'burst_size': 10
        }
    }
    
    with patch('utils.config.config', config_data):
        yield config_data


@pytest.fixture
def mock_memory_manager():
    """Mock pentru memory manager"""
    mock = Mock()
    mock.get_memory_status = Mock(return_value=asyncio.coroutine(lambda: {
        'status': 'healthy',
        'current_memory_mb': 50.0,
        'max_memory_mb': 100.0,
        'usage_percent': 50.0,
        'tracked_allocations': 0
    })())
    mock.track_allocation = Mock(return_value=True)
    mock.release_allocation = Mock()
    mock.stop = Mock()
    
    with patch('utils.memory_manager.memory_manager', mock):
        yield mock


@pytest.fixture
def mock_monitoring():
    """Mock pentru sistemul de monitoring"""
    mock = Mock()
    mock.record_download_attempt = Mock()
    mock.record_error = Mock()
    mock.record_cache_event = Mock()
    mock.start_operation_trace = Mock(return_value="mock_trace_id")
    mock.finish_operation_trace = Mock()
    mock.get_dashboard_metrics = Mock(return_value=asyncio.coroutine(lambda: {
        'system': {'uptime': '5m'},
        'downloads': {'total': 0, 'successful': 0, 'failed': 0}
    })())
    mock.stop = Mock()
    
    with patch('utils.monitoring.monitoring', mock):
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock pentru rate limiter"""
    mock = Mock()
    mock.is_allowed = Mock(return_value=asyncio.coroutine(lambda: True)())
    mock.get_stats = Mock(return_value={'requests': 0})
    mock.stop = Mock()
    
    with patch('utils.rate_limiter.rate_limiter', mock):
        yield mock


@pytest.fixture
def isolated_cache():
    """Crează un cache izolat pentru teste"""
    from utils.cache import SmartCache
    
    cache = SmartCache(
        memory_cache_size=10,
        disk_cache_size_mb=1,
        default_ttl=3600
    )
    cache.should_stop = True  # Oprește background processes
    if cache.cleanup_thread:
        cache.cleanup_thread.join(timeout=1)
        
    yield cache
    
    # Cleanup
    cache.clear()
    cache.stop()


@pytest.fixture
def mock_platform():
    """Mock pentru o platformă video"""
    from platforms.base import BasePlatform, VideoInfo, PlatformCapability
    
    class MockPlatform(BasePlatform):
        def __init__(self, name="mock_platform"):
            super().__init__()
            self.platform_name = name
            self.capabilities = {
                PlatformCapability.DOWNLOAD_VIDEO,
                PlatformCapability.GET_METADATA
            }
            
        def supports_url(self, url: str) -> bool:
            return f"{self.platform_name}.com" in url
            
        async def get_video_info(self, url: str) -> VideoInfo:
            return VideoInfo(
                id="mock_video_123",
                title="Mock Video",
                description="Mock description",
                duration=120,
                uploader="MockUser",
                uploader_id="mock_user",
                uploader_url=f"https://{self.platform_name}.com/mock_user",
                upload_date="2023-12-01T10:00:00Z",
                view_count=1000,
                like_count=100,
                comment_count=50,
                thumbnail="https://mock.thumbnail.url/image.jpg",
                webpage_url=url,
                formats=[{
                    'url': 'https://mock.video.url/video.mp4',
                    'format_id': 'mp4',
                    'ext': 'mp4',
                    'quality': '720p'
                }],
                platform=self.platform_name,
                platform_id="mock_123"
            )
            
        async def download_video(self, video_info, output_path, quality=None, format_preference=None):
            return f"{output_path}/mock_video.mp4"
            
    return MockPlatform()


@pytest.fixture
def disable_background_tasks():
    """Disable background tasks pentru teste mai rapide"""
    patches = []
    
    # Patch toate thread-urile de background
    patches.append(patch('threading.Thread.start'))
    patches.append(patch('asyncio.create_task'))
    
    for p in patches:
        p.start()
        
    yield
    
    for p in patches:
        p.stop()


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Cleanup singletons după fiecare test"""
    yield
    
    # Reset singletons dacă există
    modules_to_reset = [
        'utils.memory_manager',
        'utils.monitoring', 
        'utils.cache',
        'core.platform_manager'
    ]
    
    for module_name in modules_to_reset:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            # Reset singleton instances dacă au atribute specifice
            for attr in dir(module):
                obj = getattr(module, attr)
                if hasattr(obj, 'should_stop'):
                    obj.should_stop = True
                if hasattr(obj, 'stop'):
                    try:
                        if asyncio.iscoroutinefunction(obj.stop):
                            # Skip async stop în cleanup
                            pass
                        else:
                            obj.stop()
                    except:
                        pass


# Configurații pentru pytest
def pytest_configure(config):
    """Configurare globală pytest"""
    import psutil
    
    # Adaugă markere custom
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
    
    # Skip testele care necesită multă memorie pe sisteme cu memorie limitată
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    if available_memory_gb < 1:
        config.addinivalue_line(
            "markers", "high_memory: skip on systems with limited memory"
        )


def pytest_collection_modifyitems(config, items):
    """Modifică colecția de teste"""
    # Adaugă marker pentru teste lente
    for item in items:
        # Marchează testele async ca lente
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.slow)
            
        # Marchează testele de integrare
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)


# Funcții helper pentru teste
def create_mock_video_info(platform="youtube", video_id="test123"):
    """Helper pentru crearea unui VideoInfo mock"""
    from platforms.base import VideoInfo
    
    return VideoInfo(
        id=video_id,
        title=f"Test Video {video_id}",
        description="Test description",
        duration=180,
        uploader="TestUser",
        uploader_id="test_user",
        uploader_url=f"https://{platform}.com/test_user",
        upload_date="2023-12-01T12:00:00Z",
        view_count=5000,
        like_count=250,
        comment_count=75,
        thumbnail=f"https://{platform}.com/thumb_{video_id}.jpg",
        webpage_url=f"https://{platform}.com/watch?v={video_id}",
        formats=[
            {
                'url': f'https://{platform}.com/video_{video_id}_720p.mp4',
                'format_id': '720p',
                'ext': 'mp4', 
                'quality': '720p',
                'width': 1280,
                'height': 720
            },
            {
                'url': f'https://{platform}.com/video_{video_id}_480p.mp4',
                'format_id': '480p',
                'ext': 'mp4',
                'quality': '480p', 
                'width': 854,
                'height': 480
            }
        ],
        platform=platform,
        platform_id=video_id
    )


async def async_test_helper(coro):
    """Helper pentru rularea corutinelor în teste sincrone"""
    return await coro


# Pytest hooks pentru raportare
def pytest_runtest_setup(item):
    """Setup pentru fiecare test"""
    # Log începutul testului
    logging.getLogger('test').info(f"Starting test: {item.name}")
    
    # Skip teste de rețea dacă nu avem conexiune
    if "requires_network" in [mark.name for mark in item.iter_markers()]:
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except OSError:
            pytest.skip("Network connection required")
            
    # Skip teste memory-intensive pe sisteme limitate
    if "high_memory" in [mark.name for mark in item.iter_markers()]:
        import psutil
        if psutil.virtual_memory().available < 1024 * 1024 * 1024:  # 1GB
            pytest.skip("Insufficient memory available")


def pytest_runtest_teardown(item):
    """Teardown pentru fiecare test"""
    # Log sfârșitul testului
    logging.getLogger('test').info(f"Finished test: {item.name}")
