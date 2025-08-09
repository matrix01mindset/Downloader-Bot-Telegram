# core/platform_manager.py - Platform Manager pentru gestionarea centralizată
# Versiunea: 2.0.0 - Arhitectura Modulară

import asyncio
import logging
import tempfile
import os
from typing import Dict, List, Optional, Any
import time

# Imports locale
try:
    from utils.config import config
    from platforms.base import BasePlatform, DownloadResult
    from platforms.youtube import youtube_platform
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    config = None
    # Create dummy classes pentru fallback
    class BasePlatform:
        pass
    class DownloadResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    youtube_platform = None

logger = logging.getLogger(__name__)

class PlatformManager:
    """
    Manager centralizat pentru toate platformele video
    
    Funcționalități:
    - Auto-discovery și loading al platformelor
    - URL matching cu prioritizare
    - Download cu retry logic și fallback
    - Rate limiting per utilizator
    - Caching și optimizări de performanță
    - Health monitoring și statistici
    """
    
    def __init__(self):
        self.platforms: Dict[str, BasePlatform] = {}
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'platform_usage': {},
            'error_types': {}
        }
        
        # Rate limiting storage (în producție ar trebui să fie persistent)
        self.rate_limits = {}  # user_id -> {timestamp, count}
        
        # Cache pentru metadata (în memorie pentru Free Tier)
        self.metadata_cache = {}  # url_hash -> {metadata, timestamp}
        self.cache_ttl = 3600  # 1 oră
        
        self._initialize_platforms()
        
        logger.info(f"🚀 Platform Manager initialized with {len(self.platforms)} platforms")
        
    def _initialize_platforms(self):
        """Inițializează și înregistrează toate platformele disponibile"""
        
        # Înregistrează platformele disponibile
        available_platforms = []
        
        # YouTube platform
        try:
            if youtube_platform and youtube_platform.enabled:
                self.platforms['youtube'] = youtube_platform
                available_platforms.append('youtube')
                logger.info("✅ YouTube platform registered")
            else:
                logger.warning("⚠️ YouTube platform disabled or not available")
        except Exception as e:
            logger.error(f"❌ Failed to register YouTube platform: {e}")
            
        # TODO: Adaugă alte platforme (Instagram, TikTok, Facebook, etc.)
        # În următoarele iterații vom adăuga:
        # - Instagram platform
        # - TikTok platform  
        # - Facebook platform
        # - Twitter platform
        # - Threads platform (nou!)
        # - Pinterest platform (nou!)
        # - Reddit platform (nou!)
        # - Vimeo platform (nou!)
        
        if not available_platforms:
            logger.warning("⚠️ No platforms are available! This may cause issues.")
        else:
            logger.info(f"🎯 Available platforms: {', '.join(available_platforms)}")
            
    async def get_platform_for_url(self, url: str) -> Optional[BasePlatform]:
        """
        Găsește platforma potrivită pentru un URL
        
        Args:
            url: URL-ul de verificat
            
        Returns:
            Platforma corespunzătoare sau None
        """
        if not url or not isinstance(url, str):
            return None
            
        # Sortează platformele după prioritate (mai mic = prioritate mai mare)
        sorted_platforms = sorted(
            self.platforms.values(), 
            key=lambda p: p.priority
        )
        
        for platform in sorted_platforms:
            if platform.enabled:
                try:
                    if await platform.is_supported_url(url):
                        logger.info(f"🎯 URL matched to {platform.name} platform")
                        return platform
                except Exception as e:
                    logger.warning(f"⚠️ Error checking {platform.name} for URL: {e}")
                    continue
                    
        logger.warning(f"❌ No platform found for URL: {url[:50]}...")
        return None
        
    async def download_video(self, url: str, user_id: int = 0) -> DownloadResult:
        """
        Descarcă video cu platform matching, rate limiting și cache
        
        Args:
            url: URL-ul videoclipului
            user_id: ID-ul utilizatorului pentru rate limiting
            
        Returns:
            DownloadResult cu toate informațiile
        """
        start_time = time.time()
        
        try:
            # 1. Validare URL
            if not self._validate_url(url):
                return DownloadResult(
                    success=False,
                    error="❌ URL invalid sau format nesuportat",
                    platform="system"
                )
            
            # 2. Rate limiting check
            if not await self._check_rate_limit(user_id):
                return DownloadResult(
                    success=False,
                    error="⏳ Prea multe request-uri. Te rog așteaptă și încearcă din nou.",
                    platform="system"
                )
            
            # 3. Găsește platforma potrivită
            platform = await self.get_platform_for_url(url)
            if not platform:
                self._record_download_attempt('unknown', False, 'no_platform_found')
                return DownloadResult(
                    success=False,
                    error="🤷‍♂️ Platforma nu este suportată momentan. Platforme disponibile: " + 
                          ", ".join([p.name.title() for p in self.platforms.values() if p.enabled]),
                    platform="system"
                )
            
            # 4. Check cache pentru metadata (pentru validări rapide)
            cached_metadata = await self._get_cached_metadata(url)
            
            # 5. Extrage metadata dacă nu este în cache
            if not cached_metadata:
                try:
                    metadata = await platform.extract_metadata(url)
                    await self._cache_metadata(url, metadata)
                except Exception as e:
                    logger.error(f"❌ Failed to extract metadata: {e}")
                    metadata = {}
            else:
                metadata = cached_metadata
                logger.info("✅ Using cached metadata")
            
            # 6. Validează constrângerile
            if metadata:
                validation = await platform.validate_constraints(metadata)
                if not validation['valid']:
                    self._record_download_attempt(platform.name, False, 'constraint_violation')
                    return DownloadResult(
                        success=False,
                        error=validation['error'],
                        platform=platform.name,
                        metadata=metadata
                    )
            
            # 7. Creează fișierul temporar pentru download
            output_path = await self._create_temp_file()
            
            # 8. Descarcă videoclipul cu retry logic
            result = await platform.process_download_with_retry(url, output_path)
            
            # 9. Înregistrează statistici
            self._record_download_attempt(
                platform.name, 
                result.success, 
                'success' if result.success else 'download_failed'
            )
            
            # 10. Adaugă metadata la rezultat dacă nu există
            if result.success and not result.metadata and metadata:
                result.metadata = metadata
            
            # 11. Calculează timpul total
            total_time = time.time() - start_time
            logger.info(f"⏱️ Download completed in {total_time:.2f}s - Success: {result.success}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in download_video: {e}")
            self._record_download_attempt('system', False, 'unexpected_error')
            return DownloadResult(
                success=False,
                error=f"❌ Eroare neașteptată: {str(e)[:100]}",
                platform="system"
            )
    
    def _validate_url(self, url: str) -> bool:
        """Validare de bază a URL-ului"""
        if not url or not isinstance(url, str):
            return False
            
        # Verifică că URL-ul începe cu http/https
        if not url.strip().startswith(('http://', 'https://')):
            return False
            
        # Verifică lungimea
        if len(url) > 2048:  # Limită rezonabilă pentru URL
            return False
            
        return True
        
    async def _check_rate_limit(self, user_id: int) -> bool:
        """
        Verifică rate limiting pentru utilizator
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            True dacă utilizatorul poate face request
        """
        current_time = time.time()
        rate_limit_window = 60  # 1 minut
        max_requests_per_minute = 5  # 5 request-uri pe minut per user
        
        # Cleanup old entries
        self._cleanup_rate_limits(current_time, rate_limit_window)
        
        # Check current user's requests
        user_requests = self.rate_limits.get(user_id, [])
        
        # Count requests în ultimul minut
        recent_requests = [req_time for req_time in user_requests 
                          if current_time - req_time < rate_limit_window]
        
        if len(recent_requests) >= max_requests_per_minute:
            logger.warning(f"⏳ Rate limit exceeded for user {user_id}")
            return False
        
        # Adaugă request-ul curent
        recent_requests.append(current_time)
        self.rate_limits[user_id] = recent_requests
        
        return True
        
    def _cleanup_rate_limits(self, current_time: float, window: int):
        """Curăță intrările vechi din rate limiting"""
        for user_id in list(self.rate_limits.keys()):
            user_requests = self.rate_limits[user_id]
            # Păstrează doar request-urile din ultima fereastră de timp
            recent_requests = [req_time for req_time in user_requests 
                             if current_time - req_time < window]
            
            if recent_requests:
                self.rate_limits[user_id] = recent_requests
            else:
                # Șterge utilizatorii fără request-uri recente
                del self.rate_limits[user_id]
                
    async def _get_cached_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Obține metadata din cache dacă este disponibilă"""
        url_hash = hash(url)
        
        if url_hash in self.metadata_cache:
            cached_entry = self.metadata_cache[url_hash]
            
            # Verifică dacă cache-ul nu a expirat
            if time.time() - cached_entry['timestamp'] < self.cache_ttl:
                return cached_entry['metadata']
            else:
                # Șterge intrarea expirată
                del self.metadata_cache[url_hash]
                
        return None
        
    async def _cache_metadata(self, url: str, metadata: Dict[str, Any]):
        """Salvează metadata în cache"""
        url_hash = hash(url)
        self.metadata_cache[url_hash] = {
            'metadata': metadata,
            'timestamp': time.time()
        }
        
        # Limitează dimensiunea cache-ului (pentru Free Tier)
        if len(self.metadata_cache) > 100:  # Max 100 entries
            # Șterge cele mai vechi intrări
            oldest_entries = sorted(
                self.metadata_cache.items(),
                key=lambda x: x[1]['timestamp']
            )[:20]  # Șterge 20 entries
            
            for url_hash, _ in oldest_entries:
                del self.metadata_cache[url_hash]
                
    async def _create_temp_file(self) -> str:
        """Creează un fișier temporar pentru download"""
        temp_dir = tempfile.gettempdir()
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.mp4',
            dir=temp_dir,
            delete=False
        )
        temp_file.close()
        return temp_file.name
        
    def _record_download_attempt(self, platform: str, success: bool, error_type: str = None):
        """Înregistrează o încercare de download pentru statistici"""
        self.download_stats['total_downloads'] += 1
        
        if success:
            self.download_stats['successful_downloads'] += 1
        else:
            self.download_stats['failed_downloads'] += 1
            
            if error_type:
                self.download_stats['error_types'][error_type] = \
                    self.download_stats['error_types'].get(error_type, 0) + 1
        
        # Platform usage
        self.download_stats['platform_usage'][platform] = \
            self.download_stats['platform_usage'].get(platform, 0) + 1
            
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Returnează starea de sănătate a tuturor platformelor
        
        Returns:
            Dict cu informații despre starea sistemului
        """
        platform_health = {}
        
        for name, platform in self.platforms.items():
            try:
                health = await platform.get_platform_health()
                platform_health[name] = health
            except Exception as e:
                platform_health[name] = {
                    'name': name,
                    'status': 'error',
                    'error': str(e)
                }
                
        # Calculează statistici generale
        total_downloads = self.download_stats['total_downloads']
        success_rate = 0
        if total_downloads > 0:
            success_rate = round(
                (self.download_stats['successful_downloads'] / total_downloads) * 100, 2
            )
        
        return {
            'overall_status': 'healthy' if len([p for p in self.platforms.values() if p.enabled]) > 0 else 'unhealthy',
            'enabled_platforms': len([p for p in self.platforms.values() if p.enabled]),
            'total_platforms': len(self.platforms),
            'statistics': {
                'total_downloads': total_downloads,
                'success_rate': success_rate,
                'top_platforms': sorted(
                    self.download_stats['platform_usage'].items(),
                    key=lambda x: x[1], reverse=True
                )[:5],
                'top_errors': sorted(
                    self.download_stats['error_types'].items(),
                    key=lambda x: x[1], reverse=True
                )[:5]
            },
            'platforms': platform_health,
            'cache_size': len(self.metadata_cache),
            'active_rate_limits': len(self.rate_limits)
        }
        
    def get_supported_platforms(self) -> List[str]:
        """Returnează lista platformelor suportate și activate"""
        return [name for name, platform in self.platforms.items() if platform.enabled]
        
    async def reload_platforms(self):
        """Reîncarcă toate platformele (pentru configurări dinamice)"""
        logger.info("🔄 Reloading platforms...")
        self._initialize_platforms()
        logger.info("✅ Platforms reloaded")

# Singleton instance pentru PlatformManager
platform_manager = PlatformManager()
