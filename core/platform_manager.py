# core/platform_manager_new.py - Platform Manager Nou
# Versiunea: 3.0.0 - Arhitectura Nouă

import asyncio
import logging
import importlib
import inspect
import os
import time
from typing import Dict, List, Optional, Any, Type, Tuple
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

from platforms.base import BasePlatform, VideoInfo, PlatformCapability, ExtractionError, DownloadError
from utils.cache import cache, generate_cache_key
from utils.monitoring import monitoring, trace_operation
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class PlatformManager:
    """
    Platform Manager nou cu arhitectură asincronă și încărcare dinamică.
    Gestionează toate platformele video suportate și orchestrează descărcările.
    """
    
    def __init__(self):
        self.platforms: Dict[str, BasePlatform] = {}
        self.platform_priorities: Dict[str, int] = {}
        self.cache = cache  # Pentru compatibilitate cu testele
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.url_cache: Dict[str, str] = {}  # URL -> platform_name cache
        self.stats = {
            'total_requests': 0,
            'successful_extractions': 0,
            'successful_downloads': 0,
            'failed_requests': 0,
            'platform_stats': defaultdict(lambda: {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0.0
            }),
            'last_cleanup': None
        }
        
        # Atribute pentru compatibilitate cu testele
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'platform_usage': defaultdict(int),
            'error_types': defaultdict(int)
        }
        self.rate_limits = {}  # Pentru compatibilitate cu testele vechi
        
        # Configurări
        self.max_concurrent_downloads = 3
        self.url_cache_ttl = 3600  # 1 oră
        self.platform_health_check_interval = 300  # 5 minute
        self.cleanup_interval = 600  # 10 minute
        
        # Semafoare pentru concurrency
        self.download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        self.extraction_semaphore = asyncio.Semaphore(10)
        
        # Task management
        self.background_tasks: List[asyncio.Task] = []
        self._initialized = False
        self._shutdown = False
        
        logger.info("🔧 Platform Manager v3.0.0 initialized")
        
    async def initialize(self):
        """Inițializează platform manager-ul și încarcă toate platformele"""
        if self._initialized:
            return
            
        logger.info("🚀 Starting Platform Manager initialization...")
        
        try:
            # Încarcă platformele dinamice
            await self._load_all_platforms()
            
            # Configurează rate limiters
            await self._setup_rate_limiters()
            
            # Pornește task-urile de background
            await self._start_background_tasks()
            
            self._initialized = True
            logger.info(f"✅ Platform Manager initialized with {len(self.platforms)} platforms")
            
            # Log platformele încărcate
            for name, platform in self.platforms.items():
                capabilities = [cap.value for cap in platform.capabilities] if hasattr(platform, 'capabilities') else []
                priority = self.platform_priorities.get(name, 999)
                logger.info(f"  📱 {name}: priority={priority}, capabilities={capabilities}")
                
            if monitoring and hasattr(monitoring, 'record_metric'):
                 monitoring.record_metric("platform_manager.platforms_loaded", len(self.platforms))
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Platform Manager: {e}")
            raise
            
    async def _load_all_platforms(self):
        """Încarcă toate platformele dinamic din directorul platforms/"""
        platforms_dir = Path(__file__).parent.parent / "platforms"
        
        if not platforms_dir.exists():
            logger.warning(f"⚠️ Platforms directory not found: {platforms_dir}")
            return
            
        # Găsește toate fișierele Python din platforms/
        platform_files = []
        for file_path in platforms_dir.glob("*.py"):
            if file_path.name.startswith('__') or file_path.name == 'base.py':
                continue
            platform_files.append(file_path)
            
        logger.info(f"🔍 Found {len(platform_files)} platform files to load")
        
        # Încarcă platformele în paralel cu error handling
        load_tasks = []
        for file_path in platform_files:
            task = asyncio.create_task(self._load_platform_file(file_path))
            load_tasks.append(task)
            
        # Așteaptă ca toate să se încarce
        results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        loaded_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to load {platform_files[i].name}: {result}")
            elif result:
                loaded_count += 1
                
        logger.info(f"✅ Successfully loaded {loaded_count}/{len(platform_files)} platforms")
        
    async def _load_platform_file(self, file_path: Path) -> bool:
        """Încarcă o platformă dintr-un fișier specific"""
        module_name = file_path.stem
        
        try:
            # Import dinamic
            spec = importlib.util.spec_from_file_location(
                f"platforms.{module_name}", 
                file_path
            )
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load spec for {file_path}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Găsește clasa platformă în modul
            platform_class = self._find_platform_class(module)
            if not platform_class:
                logger.warning(f"⚠️ No platform class found in {module_name}")
                return False
                
            # Instanțiază platforma
            platform_instance = platform_class()
            
            # Validează că este o platformă validă
            if not self._validate_platform(platform_instance):
                logger.warning(f"⚠️ Invalid platform: {module_name}")
                return False
                
            # Înregistrează platforma
            platform_name = getattr(platform_instance, 'platform_name', module_name.lower())
            self.platforms[platform_name] = platform_instance
            
            # Setează prioritatea
            priority = getattr(platform_instance, 'priority', 999)
            self.platform_priorities[platform_name] = priority
            
            logger.info(f"✅ Loaded platform: {platform_name} (priority: {priority})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading platform {module_name}: {e}")
            return False
            
    def _find_platform_class(self, module) -> Optional[Type[BasePlatform]]:
        """Găsește clasa de platformă în modulul dat"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BasePlatform) and 
                obj != BasePlatform and
                not name.startswith('_')):
                return obj
        return None
        
    def _validate_platform(self, platform: BasePlatform) -> bool:
        """Validează că o platformă este corect implementată"""
        required_methods = ['supports_url', 'get_video_info', 'download_video']
        
        for method_name in required_methods:
            if not hasattr(platform, method_name):
                logger.error(f"❌ Platform missing required method: {method_name}")
                return False
                
            method = getattr(platform, method_name)
            if not callable(method):
                logger.error(f"❌ Platform method not callable: {method_name}")
                return False
                
        return True
        
    async def _setup_rate_limiters(self):
        """Configurează rate limiters pentru fiecare platformă"""
        for platform_name, platform in self.platforms.items():
            # Obține configurarea rate limit pentru platformă
            rate_limit = getattr(platform, 'rate_limit_delay', 1.0)
            max_burst = getattr(platform, 'rate_limit_per_minute', 10)
            
            # Creează rate limiter
            self.rate_limiters[platform_name] = RateLimiter(
                max_requests=max_burst,
                time_window=60.0,
                burst_allowance=3
            )
            
            logger.debug(f"🔒 Set up rate limiter for {platform_name}: {max_burst}/min")
            
    async def _start_background_tasks(self):
        """Pornește task-urile de background pentru mentenanță"""
        # Task pentru health check
        health_task = asyncio.create_task(self._periodic_health_check())
        self.background_tasks.append(health_task)
        
        # Task pentru cleanup
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.background_tasks.append(cleanup_task)
        
        logger.info("🔄 Started background maintenance tasks")
        
    async def _periodic_health_check(self):
        """Check periodic al sănătății platformelor"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.platform_health_check_interval)
                await self._check_platform_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in health check: {e}")
                
    async def _periodic_cleanup(self):
        """Cleanup periodic al cache-urilor și statisticilor"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_caches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in cleanup: {e}")
                
    async def _check_platform_health(self):
        """Verifică starea de sănătate a tuturor platformelor"""
        unhealthy_platforms = []
        
        for platform_name, platform in self.platforms.items():
            if hasattr(platform, 'is_healthy') and not platform.is_healthy():
                unhealthy_platforms.append(platform_name)
                
        if unhealthy_platforms:
            logger.warning(f"⚠️ Unhealthy platforms detected: {unhealthy_platforms}")
            
            if monitoring and hasattr(monitoring, 'record_metric'):
                monitoring.record_metric("platform_manager.unhealthy_platforms", len(unhealthy_platforms))
                
    async def _cleanup_caches(self):
        """Curăță cache-urile expirate"""
        current_time = time.time()
        expired_urls = []
        
        # Curăță URL cache-ul
        for url, (platform_name, timestamp) in list(self.url_cache.items()):
            if current_time - timestamp > self.url_cache_ttl:
                expired_urls.append(url)
                
        for url in expired_urls:
            del self.url_cache[url]
            
        if expired_urls:
            logger.debug(f"🧹 Cleaned {len(expired_urls)} expired URL cache entries")
            
        self.stats['last_cleanup'] = datetime.now()
        
    @trace_operation("platform_manager.find_platform")
    async def find_platform_for_url(self, url: str) -> Optional[BasePlatform]:
        """
        Găsește platforma potrivită pentru un URL dat
        
        Args:
            url: URL-ul de analizat
            
        Returns:
            Instanța platformei sau None dacă nu e suportată
        """
        if not url or not isinstance(url, str):
            return None
            
        # Check cache first
        cache_key = generate_cache_key("platform_url", url)
        cached_platform = cache.get(cache_key)
        if cached_platform and cached_platform in self.platforms:
            return self.platforms[cached_platform]
            
        # Sortează platformele după prioritate
        sorted_platforms = sorted(
            self.platforms.items(),
            key=lambda x: self.platform_priorities.get(x[0], 999)
        )
        
        logger.debug(f"🔍 Available platforms: {list(self.platforms.keys())}")
        logger.debug(f"🔍 Testing URL: {url}")
        
        # Testează fiecare platformă
        for platform_name, platform in sorted_platforms:
            try:
                logger.debug(f"🔍 Testing platform {platform_name} for URL: {url}")
                supports = await platform.supports_url(url)
                logger.debug(f"🔍 Platform {platform_name} supports URL: {supports}")
                
                if supports:
                    # Cache rezultatul pentru 30 minute
                    cache.put(cache_key, platform_name, ttl=1800)
                    
                    logger.debug(f"🎯 Found platform {platform_name} for URL: {url[:50]}...")
                    
                    if monitoring and hasattr(monitoring, 'record_metric'):
                        monitoring.record_metric(f"platform_manager.platform_{platform_name}_matched", 1)
                        
                    return platform
                    
            except Exception as e:
                logger.warning(f"⚠️ Error checking platform {platform_name} for URL: {e}")
                continue
                
        logger.debug(f"❌ No platform found for URL: {url[:50]}...")
        return None
        
    @trace_operation("platform_manager.extract_video_info")
    async def extract_video_info(self, url: str) -> VideoInfo:
        """
        Extrage informațiile video de la URL
        
        Args:
            url: URL-ul video-ului
            
        Returns:
            VideoInfo cu datele video-ului
            
        Raises:
            ExtractionError: Dacă extragerea eșuează
        """
        async with self.extraction_semaphore:
            start_time = time.time()
            
            try:
                # Găsește platforma potrivită
                platform = await self.find_platform_for_url(url)
                if not platform:
                    raise ExtractionError(f"No supported platform found for URL: {url}")
                    
                platform_name = platform.platform_name
                
                # Verifică rate limiting
                rate_limiter = self.rate_limiters.get(platform_name)
                if rate_limiter:
                    can_proceed = await rate_limiter.acquire(platform_name)
                    if not can_proceed:
                        raise ExtractionError(f"Rate limit exceeded for platform {platform_name}")
                    
                # Extrage informațiile
                video_info = await platform.get_video_info(url)
                
                # Actualizează statisticile
                response_time = time.time() - start_time
                self._update_stats(platform_name, True, response_time)
                
                logger.info(f"✅ Extracted video info from {platform_name}: {video_info.title[:50]}...")
                
                if monitoring and hasattr(monitoring, 'record_metric'):
                    monitoring.record_metric("platform_manager.extraction_success", 1)
                    monitoring.record_metric(f"platform_manager.{platform_name}_extraction_success", 1)
                    
                return video_info
                
            except Exception as e:
                response_time = time.time() - start_time
                platform_name = platform.platform_name if 'platform' in locals() and platform is not None else 'unknown'
                self._update_stats(platform_name, False, response_time)
                
                logger.error(f"❌ Failed to extract video info: {e}")
                
                if monitoring:
                    monitoring.record_error("platform_manager", "extraction_failed", str(e))
                    
                raise ExtractionError(f"Failed to extract video info: {str(e)}")
                
    @trace_operation("platform_manager.download_video")
    async def download_video(self, video_info_or_url, output_path: str = None, 
                           quality: Optional[str] = None, user_id: Optional[int] = None):
        """
        Descarcă un video folosind platforma potrivită
        
        Args:
            video_info_or_url: VideoInfo sau URL string
            output_path: Calea unde să salveze fișierul (opțional)
            quality: Calitatea dorită (opțional)
            user_id: ID-ul utilizatorului (pentru compatibilitate cu testele)
            
        Returns:
            DownloadResult sau calea către fișierul descărcat
            
        Raises:
            DownloadError: Dacă descărcarea eșuează
        """
        # Compatibilitate cu testele - acceptă URL string
        if isinstance(video_info_or_url, str):
            url = video_info_or_url
            try:
                video_info = await self.extract_video_info(url)
                if output_path is None:
                    output_path = "/tmp"
            except Exception as e:
                from platforms.base import DownloadResult
                return DownloadResult(
                    success=False,
                    error_message=str(e),
                    platform='unknown',
                    file_path=None,
                    metadata={}
                )
        else:
            video_info = video_info_or_url
            url = video_info.webpage_url if hasattr(video_info, 'webpage_url') else ""
        async with self.download_semaphore:
            start_time = time.time()
            
            try:
                # Găsește platforma pentru acest video
                platform_name = video_info.platform
                platform = self.platforms.get(platform_name)
                
                if not platform:
                    from platforms.base import DownloadResult
                    self._record_download_attempt(platform_name, False, "platform_not_found")
                    return DownloadResult(
                        success=False,
                        error_message=f"Platform {platform_name} not available for download",
                        platform=platform_name,
                        file_path=None,
                        metadata={}
                    )
                    
                # Verifică rate limiting
                rate_limiter = self.rate_limiters.get(platform_name)
                if rate_limiter:
                    await rate_limiter.acquire()
                    
                # Descarcă video-ul
                file_path = await platform.download_video(video_info, output_path, quality)
                
                # Actualizează statisticile
                response_time = time.time() - start_time
                self._update_stats(platform_name, True, response_time)
                self._record_download_attempt(platform_name, True)
                
                logger.info(f"✅ Downloaded video via {platform_name}: {file_path}")
                
                if monitoring and hasattr(monitoring, 'record_metric'):
                    monitoring.record_metric("platform_manager.download_success", 1)
                    monitoring.record_metric(f"platform_manager.{platform_name}_download_success", 1)
                
                # Pentru compatibilitate cu testele, returnează DownloadResult dacă e cerut URL
                if isinstance(video_info_or_url, str):
                    from platforms.base import DownloadResult
                    return DownloadResult(
                        success=True,
                        file_path=file_path,
                        platform=platform_name,
                        metadata=video_info.__dict__ if hasattr(video_info, '__dict__') else {}
                    )
                    
                return file_path
                
            except Exception as e:
                response_time = time.time() - start_time
                platform_name = video_info.platform if video_info else 'unknown'
                self._update_stats(platform_name, False, response_time)
                self._record_download_attempt(platform_name, False, "download_error")
                
                logger.error(f"❌ Failed to download video: {e}")
                
                if monitoring:
                    monitoring.record_error("platform_manager", "download_failed", str(e))
                
                # Pentru compatibilitate cu testele, returnează DownloadResult în loc de excepție
                if isinstance(video_info_or_url, str):
                    from platforms.base import DownloadResult
                    return DownloadResult(
                        success=False,
                        error_message=str(e),
                        platform=platform_name,
                        file_path=None,
                        metadata={}
                    )
                    
                raise DownloadError(f"Failed to download video: {str(e)}")
                
    def _update_stats(self, platform_name: str, success: bool, response_time: float):
        """Actualizează statisticile interne"""
        self.stats['total_requests'] += 1
        
        if success:
            if 'extraction' in str(inspect.stack()[1].function):
                self.stats['successful_extractions'] += 1
            else:
                self.stats['successful_downloads'] += 1
        else:
            self.stats['failed_requests'] += 1
            
        # Statistici per platformă
        platform_stats = self.stats['platform_stats'][platform_name]
        platform_stats['requests'] += 1
        
        if success:
            platform_stats['successes'] += 1
        else:
            platform_stats['failures'] += 1
            
        # Actualizează timpul mediu de răspuns (moving average)
        current_avg = platform_stats['avg_response_time']
        platform_stats['avg_response_time'] = (current_avg + response_time) / 2
        
    def get_supported_platforms(self) -> List[str]:
        """Returnează lista platformelor suportate"""
        return list(self.platforms.keys())
        
    def get_platform_info(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Returnează informații despre o platformă specifică"""
        platform = self.platforms.get(platform_name)
        if not platform:
            return None
            
        info = {
            'name': platform_name,
            'priority': self.platform_priorities.get(platform_name, 999),
            'capabilities': [],
            'health_status': 'unknown'
        }
        
        # Adaugă capabilitățile dacă sunt disponibile
        if hasattr(platform, 'capabilities'):
            info['capabilities'] = [cap.value for cap in platform.capabilities]
            
        # Verifică sănătatea
        if hasattr(platform, 'is_healthy'):
            info['health_status'] = 'healthy' if platform.is_healthy() else 'unhealthy'
            
        # Adaugă statistici
        platform_stats = self.stats['platform_stats'].get(platform_name, {})
        info['stats'] = dict(platform_stats)
        
        return info
        
    def get_manager_stats(self) -> Dict[str, Any]:
        """Returnează statisticile complete ale manager-ului"""
        return {
            'platforms_loaded': len(self.platforms),
            'total_requests': self.stats['total_requests'],
            'successful_extractions': self.stats['successful_extractions'],
            'successful_downloads': self.stats['successful_downloads'],
            'failed_requests': self.stats['failed_requests'],
            'success_rate': self._calculate_success_rate(),
            'platform_stats': dict(self.stats['platform_stats']),
            'last_cleanup': self.stats['last_cleanup'].isoformat() if self.stats['last_cleanup'] else None,
            'background_tasks_running': len([t for t in self.background_tasks if not t.done()]),
            'cache_size': len(self.url_cache),
            'initialized': self._initialized
        }
        
    def _calculate_success_rate(self) -> float:
        """Calculează rata de succes globală"""
        total = self.stats['total_requests']
        if total == 0:
            return 0.0
            
        successes = self.stats['successful_extractions'] + self.stats['successful_downloads']
        return round((successes / total) * 100, 2)
        
    async def health_check(self) -> Dict[str, Any]:
        """Verifică starea de sănătate a întregului sistem"""
        healthy_platforms = []
        unhealthy_platforms = []
        
        for platform_name, platform in self.platforms.items():
            if hasattr(platform, 'is_healthy'):
                if platform.is_healthy():
                    healthy_platforms.append(platform_name)
                else:
                    unhealthy_platforms.append(platform_name)
            else:
                healthy_platforms.append(platform_name)  # Assume healthy if no check
                
        return {
            'status': 'healthy' if not unhealthy_platforms else 'degraded',
            'platforms_total': len(self.platforms),
            'platforms_healthy': len(healthy_platforms),
            'platforms_unhealthy': len(unhealthy_platforms),
            'unhealthy_platforms': unhealthy_platforms,
            'manager_initialized': self._initialized,
            'background_tasks_active': len([t for t in self.background_tasks if not t.done()]),
            'success_rate': self._calculate_success_rate()
        }
        
    async def shutdown(self):
        """Oprește platform manager-ul și curăță resursele"""
        logger.info("🛑 Shutting down Platform Manager...")
        
        self._shutdown = True
        
        # Anulează task-urile de background
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                
        # Așteaptă ca task-urile să se termine
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
        # Curăță platformele
        cleanup_tasks = []
        for platform_name, platform in self.platforms.items():
            if hasattr(platform, 'cleanup'):
                task = asyncio.create_task(platform.cleanup())
                cleanup_tasks.append(task)
                
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        # Curăță cache-urile
        self.url_cache.clear()
        
        logger.info("✅ Platform Manager shutdown complete")
        
    def is_initialized(self) -> bool:
        """Verifică dacă manager-ul este inițializat"""
        return self._initialized
        
    def __str__(self) -> str:
        return f"PlatformManager(platforms={len(self.platforms)}, initialized={self._initialized})"
        
    def __repr__(self) -> str:
        return f"<PlatformManager(platforms={list(self.platforms.keys())})>"
        
    # Metode pentru compatibilitate cu testele
    def get_supported_platforms(self) -> List[str]:
        """Returnează lista platformelor suportate"""
        return list(self.platforms.keys())
        
    def _cache_metadata(self, url: str, metadata: Dict[str, Any]):
        """Salvează metadata în cache"""
        if hasattr(self, 'cache') and self.cache:
            self.cache.put(f"metadata_{url}", metadata, ttl=1800)
        
    def _get_cached_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Obține metadata din cache"""
        if hasattr(self, 'cache') and self.cache:
            return self.cache.get(f"metadata_{url}")
        return None
        
    def _record_download_attempt(self, platform: str, success: bool, error_type: str = None):
        """Înregistrează o încercare de download"""
        self.download_stats['total_downloads'] += 1
        self.download_stats['platform_usage'][platform] += 1
        
        if success:
            self.download_stats['successful_downloads'] += 1
        else:
            self.download_stats['failed_downloads'] += 1
            if error_type:
                self.download_stats['error_types'][error_type] += 1
                
    async def get_health_status(self) -> Dict[str, Any]:
        """Obține statusul de sănătate al sistemului"""
        platform_health = {}
        healthy_count = 0
        
        for name, platform in self.platforms.items():
            if hasattr(platform, 'get_platform_health'):
                try:
                    health = await platform.get_platform_health()
                    platform_health[name] = health
                    if health.get('status') == 'healthy':
                        healthy_count += 1
                except Exception as e:
                    platform_health[name] = {'status': 'error', 'error': str(e)}
            else:
                platform_health[name] = {'status': 'healthy'}
                healthy_count += 1
                
        return {
            'overall_status': 'healthy' if healthy_count == len(self.platforms) else 'degraded',
            'enabled_platforms': len(self.platforms),
            'statistics': self.get_manager_stats(),
            'platforms': platform_health
        }
        
    def _cleanup_rate_limits(self, current_time: float, time_window: float):
        """Curăță rate limits expirate"""
        cutoff_time = current_time - time_window
        
        for user_id in list(self.rate_limits.keys()):
            # Filtrează request-urile vechi
            self.rate_limits[user_id] = [
                req_time for req_time in self.rate_limits[user_id]
                if req_time > cutoff_time
            ]
            
            # Șterge utilizatorii fără request-uri
            if not self.rate_limits[user_id]:
                del self.rate_limits[user_id]
                
    async def reload_platforms(self):
        """Reîncarcă toate platformele"""
        logger.info("🔄 Reloading platforms...")
        
        # Salvează platformele existente
        old_platforms = self.platforms.copy()
        
        try:
            # Reîncarcă platformele
            await self._load_all_platforms()
            logger.info(f"✅ Reloaded {len(self.platforms)} platforms")
        except Exception as e:
            # Restaurează platformele vechi în caz de eroare
            self.platforms = old_platforms
            logger.error(f"❌ Failed to reload platforms: {e}")
            raise

# Singleton instance pentru utilizare globală
_platform_manager = None

async def get_platform_manager() -> PlatformManager:
    """Obține instanța singleton a platform manager-ului"""
    global _platform_manager
    
    if _platform_manager is None:
        _platform_manager = PlatformManager()
        await _platform_manager.initialize()
        
    return _platform_manager

async def shutdown_platform_manager():
    """Oprește platform manager-ul singleton"""
    global _platform_manager
    
    if _platform_manager is not None:
        await _platform_manager.shutdown()
        _platform_manager = None
