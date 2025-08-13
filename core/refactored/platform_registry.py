# core/refactored/platform_registry.py - Registry Centralizat pentru Platforme
# Versiunea: 4.0.0 - Arhitectura Refactorizată

import asyncio
import logging
import importlib
import inspect
import os
from typing import Dict, List, Optional, Any, Type, Set, Tuple
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime, timedelta
import time
import random
from enum import Enum

try:
    from platforms.base.abstract_platform import (
        AbstractPlatform, PlatformCapability, ContentType, 
        VideoMetadata, DownloadResult, QualityLevel,
        PlatformError, UnsupportedURLError
    )
except ImportError:
    # Fallback pentru development
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import (
        AbstractPlatform, PlatformCapability, ContentType,
        VideoMetadata, DownloadResult, QualityLevel,
        PlatformError, UnsupportedURLError
    )

logger = logging.getLogger(__name__)

class LoadBalancingStrategy(Enum):
    """Strategii de load balancing"""
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    HEALTH_BASED = "health_based"
    RANDOM = "random"
    LEAST_LOADED = "least_loaded"

class PlatformStatus(Enum):
    """Statusurile unei platforme"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"

class CircuitBreakerState(Enum):
    """Stările circuit breaker-ului"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker pentru protecția platformelor"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, 
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        
    def can_execute(self) -> bool:
        """Verifică dacă o cerere poate fi executată"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                time.time() - self.last_failure_time > self.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Înregistrează o operație reușită"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Înregistrează o operație eșuată"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if (self.state == CircuitBreakerState.CLOSED and 
            self.failure_count >= self.failure_threshold):
            self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0

class PlatformRegistry:
    """
    Registry centralizat pentru gestionarea tuturor platformelor.
    Oferă funcționalități de auto-discovery, load balancing, health monitoring
    și circuit breaking pentru platforme.
    """
    
    def __init__(self, load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.PRIORITY_BASED):
        # Registry principal
        self.platforms: Dict[str, AbstractPlatform] = {}
        self.platform_instances: Dict[str, List[AbstractPlatform]] = defaultdict(list)
        
        # Circuit breakers pentru fiecare platformă
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Health monitoring
        self.platform_status: Dict[str, PlatformStatus] = {}
        self.health_check_interval = 300  # 5 minute
        self.last_health_check: Dict[str, datetime] = {}
        
        # Load balancing
        self.load_balancing_strategy = load_balancing_strategy
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        self.platform_loads: Dict[str, int] = defaultdict(int)
        
        # URL mapping cache
        self.url_platform_cache: Dict[str, str] = {}
        self.cache_ttl = timedelta(hours=1)
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Capability mapping
        self.capability_map: Dict[PlatformCapability, Set[str]] = defaultdict(set)
        self.domain_map: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'platforms_loaded': 0,
            'circuit_breaker_trips': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self._shutdown = False
        
        logger.info("🏗️ Platform Registry initialized")
    
    async def initialize(self):
        """Inițializează registry-ul și încarcă toate platformele"""
        logger.info("🚀 Starting Platform Registry initialization...")
        
        try:
            # Auto-discovery și încărcare platforme
            await self._discover_and_load_platforms()
            
            # Configurare circuit breakers
            self._setup_circuit_breakers()
            
            # Construire mapping-uri
            self._build_capability_mappings()
            self._build_domain_mappings()
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info(f"✅ Platform Registry initialized with {len(self.platforms)} platforms")
            self._log_platform_summary()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Platform Registry: {e}")
            raise
    
    async def _discover_and_load_platforms(self):
        """Descoperă și încarcă automat toate platformele"""
        platforms_dir = Path(__file__).parent.parent.parent / "platforms" / "implementations"
        
        if not platforms_dir.exists():
            logger.warning(f"⚠️ Platforms directory not found: {platforms_dir}")
            # Fallback la directorul platforms principal
            platforms_dir = Path(__file__).parent.parent.parent / "platforms"
        
        if not platforms_dir.exists():
            logger.error(f"❌ No platforms directory found")
            return
        
        # Găsește toate fișierele Python
        platform_files = []
        for file_path in platforms_dir.glob("*.py"):
            if (file_path.name.startswith('__') or 
                file_path.name in ['base.py', 'abstract_platform.py']):
                continue
            platform_files.append(file_path)
        
        logger.info(f"🔍 Found {len(platform_files)} platform files to load")
        
        # Încarcă platformele în paralel
        load_tasks = []
        for file_path in platform_files:
            task = asyncio.create_task(self._load_platform_file(file_path))
            load_tasks.append(task)
        
        results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        loaded_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to load {platform_files[i].name}: {result}")
            elif result:
                loaded_count += 1
        
        self.stats['platforms_loaded'] = loaded_count
        logger.info(f"✅ Successfully loaded {loaded_count}/{len(platform_files)} platforms")
    
    async def _load_platform_file(self, file_path: Path) -> bool:
        """Încarcă o platformă dintr-un fișier"""
        module_name = file_path.stem
        
        try:
            # Import dinamic
            spec = importlib.util.spec_from_file_location(
                f"platforms.{module_name}", file_path
            )
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load spec for {file_path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Găsește clasa platformă
            platform_class = self._find_platform_class(module)
            if not platform_class:
                logger.warning(f"⚠️ No platform class found in {module_name}")
                return False
            
            # Instanțiază și validează platforma
            platform_instance = platform_class()
            if not self._validate_platform(platform_instance):
                logger.warning(f"⚠️ Invalid platform: {module_name}")
                return False
            
            # Înregistrează platforma
            await self.register_platform(platform_instance)
            
            logger.info(f"✅ Loaded platform: {platform_instance.platform_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading platform {module_name}: {e}")
            return False
    
    def _find_platform_class(self, module) -> Optional[Type[AbstractPlatform]]:
        """Găsește clasa de platformă în modul"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, AbstractPlatform) and 
                obj != AbstractPlatform and
                not name.startswith('_')):
                return obj
        return None
    
    def _validate_platform(self, platform: AbstractPlatform) -> bool:
        """Validează că o platformă este corect implementată"""
        required_methods = ['supports_url', 'extract_metadata', 'download_content']
        
        for method_name in required_methods:
            if not hasattr(platform, method_name):
                logger.error(f"❌ Platform missing required method: {method_name}")
                return False
            
            method = getattr(platform, method_name)
            if not callable(method):
                logger.error(f"❌ Platform method not callable: {method_name}")
                return False
        
        if not platform.platform_name:
            logger.error(f"❌ Platform missing platform_name")
            return False
        
        return True
    
    async def register_platform(self, platform: AbstractPlatform):
        """Înregistrează o platformă în registry"""
        platform_name = platform.platform_name
        
        # Înregistrează platforma principală
        self.platforms[platform_name] = platform
        
        # Adaugă la lista de instanțe (pentru load balancing)
        self.platform_instances[platform_name].append(platform)
        
        # Inițializează statusul
        self.platform_status[platform_name] = PlatformStatus.HEALTHY
        self.last_health_check[platform_name] = datetime.now()
        
        # Inițializează load counter
        self.platform_loads[platform_name] = 0
        
        logger.info(f"📝 Registered platform: {platform_name} (priority: {platform.priority})")
    
    def _setup_circuit_breakers(self):
        """Configurează circuit breakers pentru toate platformele"""
        for platform_name in self.platforms:
            self.circuit_breakers[platform_name] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3
            )
        logger.info(f"🔒 Set up circuit breakers for {len(self.circuit_breakers)} platforms")
    
    def _build_capability_mappings(self):
        """Construiește mapping-urile de capabilități"""
        for platform_name, platform in self.platforms.items():
            for capability in platform.capabilities:
                self.capability_map[capability].add(platform_name)
        
        logger.info(f"🗺️ Built capability mappings for {len(self.capability_map)} capabilities")
    
    def _build_domain_mappings(self):
        """Construiește mapping-urile de domenii"""
        for platform_name, platform in self.platforms.items():
            for domain in platform.supported_domains:
                self.domain_map[domain].add(platform_name)
        
        logger.info(f"🌐 Built domain mappings for {len(self.domain_map)} domains")
    
    async def _start_background_tasks(self):
        """Pornește task-urile de background"""
        # Health monitoring task
        health_task = asyncio.create_task(self._periodic_health_check())
        self.background_tasks.append(health_task)
        
        # Cache cleanup task
        cache_task = asyncio.create_task(self._periodic_cache_cleanup())
        self.background_tasks.append(cache_task)
        
        logger.info("🔄 Started background maintenance tasks")
    
    def find_platform_for_url(self, url: str) -> Optional[str]:
        """Găsește platforma potrivită pentru un URL"""
        # Check cache first
        if url in self.url_platform_cache:
            cache_time = self.cache_timestamps.get(url)
            if cache_time and datetime.now() - cache_time < self.cache_ttl:
                self.stats['cache_hits'] += 1
                return self.url_platform_cache[url]
            else:
                # Cache expirat
                del self.url_platform_cache[url]
                if url in self.cache_timestamps:
                    del self.cache_timestamps[url]
        
        self.stats['cache_misses'] += 1
        
        # Găsește platforma care suportă URL-ul
        for platform_name, platform in self.platforms.items():
            if (self.platform_status.get(platform_name) == PlatformStatus.HEALTHY and
                platform.enabled and
                platform.supports_url(url)):
                
                # Cache rezultatul
                self.url_platform_cache[url] = platform_name
                self.cache_timestamps[url] = datetime.now()
                
                return platform_name
        
        return None
    
    def get_platforms_by_capability(self, capability: PlatformCapability) -> List[str]:
        """Obține platformele care au o anumită capabilitate"""
        return list(self.capability_map.get(capability, set()))
    
    def get_platform_instance(self, platform_name: str) -> Optional[AbstractPlatform]:
        """Obține o instanță de platformă folosind load balancing"""
        if platform_name not in self.platform_instances:
            return None
        
        instances = self.platform_instances[platform_name]
        if not instances:
            return None
        
        # Verifică circuit breaker
        circuit_breaker = self.circuit_breakers.get(platform_name)
        if circuit_breaker and not circuit_breaker.can_execute():
            logger.warning(f"🚫 Circuit breaker OPEN for {platform_name}")
            return None
        
        # Selectează instanța bazat pe strategia de load balancing
        if self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            index = self.round_robin_counters[platform_name] % len(instances)
            self.round_robin_counters[platform_name] += 1
            return instances[index]
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.PRIORITY_BASED:
            # Sortează după prioritate și returnează primul
            sorted_instances = sorted(instances, key=lambda p: p.priority)
            return sorted_instances[0]
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(instances)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            # Returnează instanța cu cea mai mică încărcare
            return min(instances, key=lambda p: self.platform_loads.get(p.platform_name, 0))
        
        else:
            # Default: primul disponibil
            return instances[0]
    
    async def execute_with_circuit_breaker(self, platform_name: str, operation, *args, **kwargs):
        """Execută o operație cu circuit breaker protection"""
        circuit_breaker = self.circuit_breakers.get(platform_name)
        if not circuit_breaker:
            # Dacă nu există circuit breaker, execută direct
            return await operation(*args, **kwargs)
        
        if not circuit_breaker.can_execute():
            raise PlatformError(f"Circuit breaker OPEN for {platform_name}", 
                              error_code="CIRCUIT_BREAKER_OPEN", 
                              platform=platform_name)
        
        try:
            # Incrementează load counter
            self.platform_loads[platform_name] += 1
            
            result = await operation(*args, **kwargs)
            
            # Operație reușită
            circuit_breaker.record_success()
            self.stats['successful_requests'] += 1
            
            return result
            
        except Exception as e:
            # Operație eșuată
            circuit_breaker.record_failure()
            self.stats['failed_requests'] += 1
            
            if circuit_breaker.state == CircuitBreakerState.OPEN:
                self.stats['circuit_breaker_trips'] += 1
                self.platform_status[platform_name] = PlatformStatus.FAILED
                logger.error(f"🚫 Circuit breaker TRIPPED for {platform_name}")
            
            raise
        
        finally:
            # Decrementează load counter
            self.platform_loads[platform_name] = max(0, self.platform_loads[platform_name] - 1)
            self.stats['total_requests'] += 1
    
    async def _periodic_health_check(self):
        """Health check periodic pentru toate platformele"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_platforms_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in health check: {e}")
    
    async def _check_all_platforms_health(self):
        """Verifică sănătatea tuturor platformelor"""
        for platform_name, platform in self.platforms.items():
            try:
                health_status = platform.get_health_status()
                
                # Actualizează statusul bazat pe health check
                if health_status['status'] == 'healthy':
                    self.platform_status[platform_name] = PlatformStatus.HEALTHY
                elif health_status['status'] == 'degraded':
                    self.platform_status[platform_name] = PlatformStatus.DEGRADED
                else:
                    self.platform_status[platform_name] = PlatformStatus.FAILED
                
                self.last_health_check[platform_name] = datetime.now()
                
            except Exception as e:
                logger.error(f"❌ Health check failed for {platform_name}: {e}")
                self.platform_status[platform_name] = PlatformStatus.FAILED
    
    async def _periodic_cache_cleanup(self):
        """Cleanup periodic al cache-urilor"""
        while not self._shutdown:
            try:
                await asyncio.sleep(3600)  # Cleanup la fiecare oră
                self._cleanup_expired_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in cache cleanup: {e}")
    
    def _cleanup_expired_cache(self):
        """Curăță cache-urile expirate"""
        now = datetime.now()
        expired_urls = []
        
        for url, timestamp in self.cache_timestamps.items():
            if now - timestamp > self.cache_ttl:
                expired_urls.append(url)
        
        for url in expired_urls:
            if url in self.url_platform_cache:
                del self.url_platform_cache[url]
            if url in self.cache_timestamps:
                del self.cache_timestamps[url]
        
        if expired_urls:
            logger.info(f"🧹 Cleaned up {len(expired_urls)} expired cache entries")
    
    def _log_platform_summary(self):
        """Loghează un sumar al platformelor încărcate"""
        logger.info("\n" + "="*60)
        logger.info("📊 PLATFORM REGISTRY SUMMARY")
        logger.info("="*60)
        
        for platform_name, platform in sorted(self.platforms.items(), key=lambda x: x[1].priority):
            status = self.platform_status.get(platform_name, PlatformStatus.HEALTHY)
            capabilities = len(platform.capabilities)
            domains = len(platform.supported_domains)
            
            logger.info(f"  📱 {platform_name:15} | Priority: {platform.priority:3d} | "
                       f"Status: {status.value:8} | Capabilities: {capabilities:2d} | Domains: {domains:2d}")
        
        logger.info("="*60)
        logger.info(f"Total platforms: {len(self.platforms)}")
        logger.info(f"Total capabilities: {len(self.capability_map)}")
        logger.info(f"Total domains: {len(self.domain_map)}")
        logger.info("="*60)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Returnează statisticile registry-ului"""
        platform_stats = {}
        for platform_name, platform in self.platforms.items():
            platform_stats[platform_name] = {
                'status': self.platform_status.get(platform_name, PlatformStatus.HEALTHY).value,
                'priority': platform.priority,
                'enabled': platform.enabled,
                'capabilities': len(platform.capabilities),
                'domains': len(platform.supported_domains),
                'circuit_breaker_state': self.circuit_breakers.get(platform_name, CircuitBreaker()).state.value,
                'current_load': self.platform_loads.get(platform_name, 0)
            }
        
        return {
            'registry_stats': self.stats,
            'platform_stats': platform_stats,
            'cache_stats': {
                'url_cache_size': len(self.url_platform_cache),
                'cache_hit_rate': (self.stats['cache_hits'] / 
                                 max(1, self.stats['cache_hits'] + self.stats['cache_misses'])) * 100
            },
            'load_balancing_strategy': self.load_balancing_strategy.value
        }
    
    async def shutdown(self):
        """Oprește registry-ul și curăță resursele"""
        logger.info("🛑 Shutting down Platform Registry...")
        
        self._shutdown = True
        
        # Anulează task-urile de background
        for task in self.background_tasks:
            task.cancel()
        
        # Așteaptă ca task-urile să se termine
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("✅ Platform Registry shutdown complete")
    
    def __str__(self) -> str:
        return f"PlatformRegistry(platforms={len(self.platforms)}, strategy={self.load_balancing_strategy.value})"
    
    def __repr__(self) -> str:
        return (f"PlatformRegistry(platforms={list(self.platforms.keys())}, "
                f"strategy={self.load_balancing_strategy.value})")


# Singleton instance pentru utilizare globală
platform_registry = PlatformRegistry()