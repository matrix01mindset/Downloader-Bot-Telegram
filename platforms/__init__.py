# platforms/__init__.py - Platform Registry pentru toate platformele
# Versiunea: 3.0.0 - Arhitectura Nouă

"""
Platform Module v3.0.0 - Next Generation Video Platform Management

Supported Platforms:
- YouTube: Advanced PO Token bypass, multiple client configs, anti-detection
- Instagram: Stories, Reels, IGTV, Posts cu suport complet pentru toate tipurile
- TikTok: Anti-detection avansat, watermark removal, multiple quality options
- Facebook: Video posts, Stories, Watch videos, Live streams arhivate
- Twitter/X: Tweet videos, Spaces audio, rate limiting foarte strict
- Threads: Meta's new platform cu manual extraction fallback
- Pinterest: Pin video extraction cu suport pentru board videos
- Reddit: v.redd.it, i.redd.it, gallery posts cu video
- Vimeo: High-quality videos, On Demand, password-protected content
- Dailymotion: Geo-restriction bypass, family filter, multiple qualities

New Architecture Features:
- Dynamic platform loading cu import automat
- Enhanced error handling cu recovery mechanisms
- Advanced caching cu TTL și priority management
- Rate limiting per platform cu burst allowance
- Comprehensive monitoring cu metrics și traces
- Health checks pentru fiecare platformă
- Async-first design pentru performance maxim
"""

from typing import Dict, Type, List, Optional
import logging

# Import base classes
try:
    from .base import (
        BasePlatform, 
        VideoInfo, 
        PlatformCapability, 
        ExtractionError, 
        DownloadError,
        GenericPlatform
    )
except ImportError as e:
    logging.error(f"Failed to import base classes: {e}")
    # Fallback definitions
    class BasePlatform: pass
    class VideoInfo: pass
    class PlatformCapability: pass
    class ExtractionError(Exception): pass
    class DownloadError(Exception): pass
    class GenericPlatform(BasePlatform): pass

# Import platform classes - cu fallback pentru missing modules
try:
    from .youtube_new import YouTubePlatform
except ImportError:
    YouTubePlatform = None
    
try:
    from .instagram import InstagramPlatform  
except ImportError:
    InstagramPlatform = None
    
try:
    from .tiktok import TikTokPlatform
except ImportError:
    TikTokPlatform = None
    
try:
    from .facebook import FacebookPlatform
except ImportError:
    FacebookPlatform = None
    
try:
    from .twitter import TwitterPlatform
except ImportError:
    TwitterPlatform = None
    
try:
    from .threads import ThreadsPlatform
except ImportError:
    ThreadsPlatform = None
    
try:
    from .pinterest import PinterestPlatform
except ImportError:
    PinterestPlatform = None
    
try:
    from .reddit import RedditPlatform
except ImportError:
    RedditPlatform = None
    
try:
    from .vimeo import VimeoPlatform
except ImportError:
    VimeoPlatform = None
    
try:
    from .dailymotion import DailymotionPlatform
except ImportError:
    DailymotionPlatform = None

logger = logging.getLogger(__name__)

# Registry cu toate platformele disponibile - versiunea 3.0.0
PLATFORM_REGISTRY: Dict[str, Optional[Type[BasePlatform]]] = {
    'youtube': YouTubePlatform,
    'instagram': InstagramPlatform,
    'tiktok': TikTokPlatform,
    'facebook': FacebookPlatform,
    'twitter': TwitterPlatform,
    'threads': ThreadsPlatform,
    'pinterest': PinterestPlatform,
    'reddit': RedditPlatform,
    'vimeo': VimeoPlatform,
    'dailymotion': DailymotionPlatform,
}

# Filtrează platformele care au fost încărcate cu succes
SUPPORTED_PLATFORMS = [name for name, cls in PLATFORM_REGISTRY.items() if cls is not None]
FAILED_PLATFORMS = [name for name, cls in PLATFORM_REGISTRY.items() if cls is None]

# Platform priorities pentru loading order
PLATFORM_PRIORITIES: Dict[str, int] = {
    'youtube': 1,      # Cea mai populară și stabilă
    'instagram': 2,    # Popular, dar mai restrictiv
    'tiktok': 3,       # Popular, anti-detection complex
    'facebook': 4,     # Restrictiv, necesită atenție specială
    'twitter': 5,      # Extrem de restrictiv
    'vimeo': 6,        # Calitate înaltă, mai puțin restrictiv
    'reddit': 7,       # Destul de stabil pentru v.redd.it
    'threads': 8,      # Nou, pot fi probleme
    'pinterest': 9,    # Specific use case
    'dailymotion': 10, # Backup option
}

def get_platform_class(platform_name: str) -> Optional[Type[BasePlatform]]:
    """
    Obține clasa unei platforme după nume
    
    Args:
        platform_name: Numele platformei
        
    Returns:
        Clasa platformei sau None dacă nu există
    """
    return PLATFORM_REGISTRY.get(platform_name.lower())

def get_all_platform_classes() -> Dict[str, Type[BasePlatform]]:
    """
    Obține toate clasele de platforme disponibile (doar cele încărcate)
    
    Returns:
        Dictionary cu numele și clasele platformelor
    """
    return {name: cls for name, cls in PLATFORM_REGISTRY.items() if cls is not None}

def get_platforms_by_priority() -> List[str]:
    """
    Obține platformele sortate după prioritate (doar cele disponibile)
    
    Returns:
        Lista cu numele platformelor în ordinea priorității
    """
    available = [p for p in SUPPORTED_PLATFORMS if p in PLATFORM_PRIORITIES]
    return sorted(available, key=lambda x: PLATFORM_PRIORITIES.get(x, 999))

def is_platform_supported(platform_name: str) -> bool:
    """
    Verifică dacă o platformă este suportată și disponibilă
    
    Args:
        platform_name: Numele platformei
        
    Returns:
        True dacă platforma este suportată și disponibilă
    """
    return platform_name.lower() in SUPPORTED_PLATFORMS

def get_platform_info() -> Dict[str, Dict[str, any]]:
    """
    Obține informații despre toate platformele
    
    Returns:
        Dictionary cu informații despre fiecare platformă
    """
    info = {}
    
    for name, platform_class in PLATFORM_REGISTRY.items():
        if platform_class is not None:
            try:
                # Instanțiază temporary pentru a obține info
                temp_instance = platform_class()
                info[name] = {
                    'class_name': platform_class.__name__,
                    'priority': PLATFORM_PRIORITIES.get(name, 999),
                    'capabilities': [cap.value for cap in getattr(temp_instance, 'capabilities', [])],
                    'platform_name': getattr(temp_instance, 'platform_name', name),
                    'status': 'available',
                    'version': '3.0.0'
                }
            except Exception as e:
                info[name] = {
                    'class_name': platform_class.__name__,
                    'priority': PLATFORM_PRIORITIES.get(name, 999),
                    'error': str(e),
                    'status': 'error',
                    'version': '3.0.0'
                }
        else:
            info[name] = {
                'class_name': 'Not Loaded',
                'priority': PLATFORM_PRIORITIES.get(name, 999),
                'error': 'Import failed',
                'status': 'unavailable',
                'version': '3.0.0'
            }
            
    return info

def get_registry_stats() -> Dict[str, any]:
    """
    Obține statistici despre registry
    """
    return {
        'total_platforms': len(PLATFORM_REGISTRY),
        'available_platforms': len(SUPPORTED_PLATFORMS),
        'failed_platforms': len(FAILED_PLATFORMS),
        'success_rate': round((len(SUPPORTED_PLATFORMS) / len(PLATFORM_REGISTRY)) * 100, 2),
        'supported_platforms': SUPPORTED_PLATFORMS,
        'failed_platforms': FAILED_PLATFORMS,
        'version': '3.0.0'
    }

# Log initialization results
stats = get_registry_stats()
if FAILED_PLATFORMS:
    logger.warning(f"⚠️ Failed to load {len(FAILED_PLATFORMS)} platforms: {', '.join(FAILED_PLATFORMS)}")
    
logger.info(
    f"📦 Platform Registry v3.0.0 initialized: {stats['available_platforms']}/{stats['total_platforms']} "
    f"platforms loaded ({stats['success_rate']}% success rate)"
)
logger.info(f"✅ Available platforms: {', '.join(SUPPORTED_PLATFORMS)}")

# Export pentru utilizare externă - versiunea 3.0.0
__all__ = [
    # Base classes and exceptions
    'BasePlatform',
    'VideoInfo',
    'PlatformCapability', 
    'ExtractionError',
    'DownloadError',
    'GenericPlatform',
    # Platform classes (poate fi None dacă import a eșuat)
    'YouTubePlatform', 
    'InstagramPlatform',
    'TikTokPlatform',
    'FacebookPlatform',
    'TwitterPlatform',
    'ThreadsPlatform',
    'PinterestPlatform',
    'RedditPlatform',
    'VimeoPlatform',
    'DailymotionPlatform',
    # Registry and utilities
    'PLATFORM_REGISTRY',
    'SUPPORTED_PLATFORMS',
    'FAILED_PLATFORMS',
    'PLATFORM_PRIORITIES',
    'get_platform_class',
    'get_all_platform_classes',
    'get_platforms_by_priority',
    'is_platform_supported',
    'get_platform_info',
    'get_registry_stats'
]
