# core/bot_manager.py - Bot Lifecycle Management
# Versiunea: 3.0.0 - Arhitectura Nouă

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from utils.monitoring import monitoring, trace_operation
from utils.cache import cache
from utils.memory_manager import MemoryManager
from core.platform_manager import PlatformManager

logger = logging.getLogger(__name__)

@dataclass
class BotStatus:
    """Status container pentru bot"""
    is_running: bool = False
    start_time: Optional[float] = None
    uptime: float = 0
    total_requests: int = 0
    successful_requests: int = 0
    error_count: int = 0
    memory_usage_mb: float = 0
    active_downloads: int = 0

class BotManager:
    """
    Manager pentru ciclul de viață al botului
    Gestionează inițializarea, monitorizarea și shutdown-ul
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.status = BotStatus()
        self.memory_manager = MemoryManager(
            max_memory_mb=config.get('performance', {}).get('memory_limit_mb', 200)
        )
        self.platform_manager = None
        self.is_initialized = False
        self.shutdown_event = asyncio.Event()
        
    @trace_operation("bot_manager.initialize")
    async def initialize(self) -> bool:
        """
        Inițializează botul cu optimizări pentru cold start
        """
        try:
            start_time = time.time()
            logger.info("🚀 Starting bot initialization...")
            
            # 1. Pre-load critical modules
            await self._preload_critical_modules()
            
            # 2. Initialize cache system
            await self._initialize_cache()
            
            # 3. Initialize platform manager
            await self._initialize_platform_manager()
            
            # 4. Warm up connections
            await self._warm_up_connections()
            
            # 5. Setup monitoring
            await self._setup_monitoring()
            
            initialization_time = time.time() - start_time
            
            self.status.is_running = True
            self.status.start_time = time.time()
            self.is_initialized = True
            
            logger.info(f"✅ Bot initialized successfully in {initialization_time:.2f}s")
            
            if monitoring:
                monitoring.record_event("bot_initialized", {
                    "initialization_time": initialization_time,
                    "timestamp": time.time()
                })
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            if monitoring:
                monitoring.record_error("bot_manager", "initialization", str(e))
            return False
            
    async def _preload_critical_modules(self):
        """Pre-încarcă modulele critice pentru a reduce cold start"""
        logger.info("📦 Pre-loading critical modules...")
        
        # Pre-load yt-dlp și extractoare
        try:
            import yt_dlp
            # Force load common extractors
            extractors = ['youtube', 'tiktok', 'instagram', 'facebook', 'twitter']
            for extractor_name in extractors:
                try:
                    extractor_class = yt_dlp.extractor.get_info_extractor(extractor_name)
                    logger.debug(f"Pre-loaded extractor: {extractor_name}")
                except Exception:
                    pass  # Ignore extractor loading errors
        except Exception as e:
            logger.warning(f"Could not pre-load yt-dlp extractors: {e}")
            
        # Pre-load other critical modules
        try:
            import aiohttp
            import requests
            import tempfile
            import json
            logger.debug("Pre-loaded HTTP and utility modules")
        except Exception as e:
            logger.warning(f"Could not pre-load utility modules: {e}")
            
    async def _initialize_cache(self):
        """Inițializează sistemul de cache"""
        logger.info("💾 Initializing cache system...")
        
        cache_config = self.config.get('cache', {})
        if cache_config.get('enabled', True):
            await cache.initialize(cache_config)
            logger.info("✅ Cache system initialized")
        else:
            logger.info("⚠️ Cache system disabled in config")
            
    async def _initialize_platform_manager(self):
        """Inițializează platform manager"""
        logger.info("🌐 Initializing platform manager...")
        
        self.platform_manager = PlatformManager(self.config)
        await self.platform_manager.initialize()
        
        logger.info(f"✅ Platform manager initialized with {len(self.platform_manager.platforms)} platforms")
        
    async def _warm_up_connections(self):
        """Pre-încălzește conexiunile pentru a reduce latența"""
        logger.info("🔥 Warming up connections...")
        
        # Test Telegram API connection
        try:
            token = self.config.get('telegram', {}).get('token')
            if token:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.telegram.org/bot{token}/getMe"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            logger.info("✅ Telegram API connection warmed up")
                        else:
                            logger.warning(f"⚠️ Telegram API connection issue: {response.status}")
        except Exception as e:
            logger.warning(f"Could not warm up Telegram connection: {e}")
            
    async def _setup_monitoring(self):
        """Configurează monitorizarea"""
        logger.info("📊 Setting up monitoring...")
        
        if monitoring:
            # Start monitoring tasks
            asyncio.create_task(self._monitor_system())
            logger.info("✅ Monitoring setup complete")
            
    @trace_operation("bot_manager.monitor_system")
    async def _monitor_system(self):
        """Task pentru monitorizarea continuă a sistemului"""
        while self.status.is_running and not self.shutdown_event.is_set():
            try:
                # Update system metrics
                self._update_system_metrics()
                
                # Check memory usage
                await self._check_memory_usage()
                
                # Cleanup old cache entries
                if hasattr(cache, 'cleanup'):
                    await cache.cleanup()
                    
                # Sleep for monitoring interval
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(60)  # Back off on error
                
    def _update_system_metrics(self):
        """Actualizează metricile sistemului"""
        try:
            import psutil
            process = psutil.Process()
            
            # Update status
            if self.status.start_time:
                self.status.uptime = time.time() - self.status.start_time
                
            self.status.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
            if monitoring:
                monitoring.record_metric("system.memory_usage_mb", self.status.memory_usage_mb)
                monitoring.record_metric("system.uptime", self.status.uptime)
                
        except Exception as e:
            logger.debug(f"Could not update system metrics: {e}")
            
    async def _check_memory_usage(self):
        """Verifică utilizarea memoriei și face cleanup dacă e necesar"""
        max_memory = self.memory_manager.max_memory_mb
        current_memory = self.status.memory_usage_mb
        
        if current_memory > max_memory * 0.8:  # 80% threshold
            logger.warning(f"High memory usage: {current_memory:.1f}MB / {max_memory}MB")
            
            # Trigger cleanup
            await self.memory_manager.cleanup_old_downloads()
            
            if hasattr(cache, 'cleanup'):
                await cache.cleanup(force=True)
                
            logger.info("Memory cleanup completed")
            
    def increment_request_count(self):
        """Incrementează contorul de cereri"""
        self.status.total_requests += 1
        
    def increment_success_count(self):
        """Incrementează contorul de succese"""
        self.status.successful_requests += 1
        
    def increment_error_count(self):
        """Incrementează contorul de erori"""
        self.status.error_count += 1
        
    def get_health_status(self) -> Dict[str, Any]:
        """Returnează starea de sănătate a botului"""
        success_rate = 0
        if self.status.total_requests > 0:
            success_rate = (self.status.successful_requests / self.status.total_requests) * 100
            
        return {
            "status": "healthy" if self.status.is_running else "unhealthy",
            "uptime_seconds": int(self.status.uptime),
            "total_requests": self.status.total_requests,
            "successful_requests": self.status.successful_requests,
            "error_count": self.status.error_count,
            "success_rate_percent": round(success_rate, 2),
            "memory_usage_mb": round(self.status.memory_usage_mb, 2),
            "active_downloads": self.status.active_downloads,
            "platforms_loaded": len(self.platform_manager.platforms) if self.platform_manager else 0,
            "cache_enabled": hasattr(cache, 'is_enabled') and cache.is_enabled,
            "monitoring_enabled": monitoring is not None
        }
        
    async def shutdown(self):
        """Oprește botul în mod elegant"""
        logger.info("🛑 Starting bot shutdown...")
        
        self.status.is_running = False
        self.shutdown_event.set()
        
        # Cleanup resources
        try:
            if self.platform_manager:
                await self.platform_manager.cleanup()
                
            if hasattr(cache, 'cleanup'):
                await cache.cleanup(force=True)
                
            if self.memory_manager:
                await self.memory_manager.cleanup_all()
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
        logger.info("✅ Bot shutdown complete")
        
    def is_ready(self) -> bool:
        """Verifică dacă botul este gata să primească cereri"""
        return (
            self.is_initialized and 
            self.status.is_running and 
            self.platform_manager is not None and
            len(self.platform_manager.platforms) > 0
        )

# Global bot manager instance
bot_manager = None

async def get_bot_manager(config: dict) -> BotManager:
    """Obține instanța globală a bot manager-ului"""
    global bot_manager
    
    if bot_manager is None:
        bot_manager = BotManager(config)
        await bot_manager.initialize()
        
    return bot_manager
