# core/system_manager.py - System Manager pentru orchestrarea arhitecturii
# Versiunea: 2.0.0 - Arhitectura Modulară

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import threading

try:
    # Core components
    from core.platform_manager import platform_manager
    
    # Utility components
    from utils.config import config
    from utils.memory_manager import memory_manager
    from utils.monitoring import monitoring
    from utils.retry_manager import retry_manager
    from utils.rate_limiter import rate_limiter
    from utils.cache import cache
    
    # Platform implementations
    from platforms.youtube import YouTubePlatform
    from platforms.instagram import InstagramPlatform
    from platforms.tiktok import TikTokPlatform
    
except ImportError as e:
    logging.error(f"❌ Failed to import required components: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)

class SystemState(Enum):
    """Stati possibili ale sistemului"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"    # Unele componente au probleme
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class ComponentStatus:
    """Status unei componente de sistem"""
    name: str
    status: str
    health: str
    last_check: float
    error_count: int = 0
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}

class SystemManager:
    """
    Manager central pentru orchestrarea întregii arhitecturi modulare
    
    Responsabilități:
    - Inițializarea și configurarea tuturor componentelor
    - Monitoring și health checks pentru toate componentele
    - Coordonarea shutdown-ului elegant
    - Raportarea statusului general al sistemului
    - Gestionarea dependințelor între componente
    - Auto-recovery pentru componente critice
    """
    
    def __init__(self):
        self.state = SystemState.INITIALIZING
        self.start_time = time.time()
        self.components: Dict[str, ComponentStatus] = {}
        self.critical_components: Set[str] = {
            'platform_manager',
            'memory_manager', 
            'monitoring',
            'cache'
        }
        
        # Health check settings
        self.health_check_interval = 60  # 1 minut
        self.health_check_thread = None
        self.should_stop = False
        
        # Error thresholds
        self.max_component_errors = 5
        self.degraded_threshold = 2  # Numărul de componente degraded pentru DEGRADED state
        
        # Shutdown handling
        self._setup_signal_handlers()
        
        logger.info("🚀 System Manager initialized")
        
    def _setup_signal_handlers(self):
        """Configurează handler-ele pentru semnalele de system"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, starting graceful shutdown...")
            asyncio.create_task(self.shutdown())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    async def initialize(self) -> bool:
        """Inițializează toate componentele sistemului"""
        
        logger.info("🔧 Starting system initialization...")
        self.state = SystemState.INITIALIZING
        
        initialization_steps = [
            ("config", self._check_config),
            ("memory_manager", self._check_memory_manager),
            ("cache", self._check_cache),
            ("monitoring", self._check_monitoring),
            ("retry_manager", self._check_retry_manager),
            ("rate_limiter", self._check_rate_limiter),
            ("platform_manager", self._init_platform_manager),
            ("platforms", self._register_platforms),
        ]
        
        successful_components = 0
        total_components = len(initialization_steps)
        
        for component_name, init_func in initialization_steps:
            try:
                logger.info(f"🔧 Initializing {component_name}...")
                
                success = await init_func()
                
                if success:
                    self.components[component_name] = ComponentStatus(
                        name=component_name,
                        status="running",
                        health="healthy",
                        last_check=time.time()
                    )
                    successful_components += 1
                    logger.info(f"✅ {component_name} initialized successfully")
                else:
                    self.components[component_name] = ComponentStatus(
                        name=component_name,
                        status="error",
                        health="unhealthy",
                        last_check=time.time(),
                        error_count=1,
                        last_error="Initialization failed"
                    )
                    logger.error(f"❌ {component_name} initialization failed")
                    
            except Exception as e:
                self.components[component_name] = ComponentStatus(
                    name=component_name,
                    status="error", 
                    health="unhealthy",
                    last_check=time.time(),
                    error_count=1,
                    last_error=str(e)
                )
                logger.error(f"❌ Error initializing {component_name}: {e}")
                
        # Determină starea finală
        critical_failures = sum(
            1 for name, status in self.components.items()
            if name in self.critical_components and status.status == "error"
        )
        
        if critical_failures > 0:
            self.state = SystemState.ERROR
            logger.error(f"🚨 System initialization failed: {critical_failures} critical component(s) failed")
            return False
        elif successful_components < total_components - 1:  # Permitem o componentă non-critică să eșueze
            self.state = SystemState.DEGRADED
            logger.warning(f"⚠️ System initialized in degraded mode: {successful_components}/{total_components} components running")
        else:
            self.state = SystemState.RUNNING
            logger.info(f"🎉 System initialization completed successfully: {successful_components}/{total_components} components running")
            
        # Pornește health monitoring
        self._start_health_monitoring()
        
        return self.state in [SystemState.RUNNING, SystemState.DEGRADED]
        
    async def _check_config(self) -> bool:
        """Verifică configurația"""
        try:
            if config is None:
                logger.warning("⚠️ Config not loaded, using defaults")
                return True
                
            # Test basic config access
            _ = config.get('app', {})
            return True
        except Exception as e:
            logger.error(f"❌ Config check failed: {e}")
            return False
            
    async def _check_memory_manager(self) -> bool:
        """Verifică memory manager"""
        try:
            if memory_manager is None:
                return False
                
            # Test basic functionality
            status = await memory_manager.get_memory_status()
            return status.get('status') in ['healthy', 'warning']
        except Exception as e:
            logger.error(f"❌ Memory manager check failed: {e}")
            return False
            
    async def _check_cache(self) -> bool:
        """Verifică sistemul de cache"""
        try:
            if cache is None:
                return False
                
            # Test basic cache operations
            test_key = "system_test_key"
            test_value = "system_test_value"
            
            cache.put(test_key, test_value, ttl=10)
            retrieved = cache.get(test_key)
            cache.remove(test_key)
            
            return retrieved == test_value
        except Exception as e:
            logger.error(f"❌ Cache check failed: {e}")
            return False
            
    async def _check_monitoring(self) -> bool:
        """Verifică sistemul de monitoring"""
        try:
            if monitoring is None:
                return False
                
            # Test basic monitoring
            dashboard = await monitoring.get_dashboard_metrics()
            return 'system' in dashboard
        except Exception as e:
            logger.error(f"❌ Monitoring check failed: {e}")
            return False
            
    async def _check_retry_manager(self) -> bool:
        """Verifică retry manager"""
        try:
            if retry_manager is None:
                return False
                
            # Test basic retry functionality
            stats = retry_manager.get_statistics()
            return isinstance(stats, dict)
        except Exception as e:
            logger.error(f"❌ Retry manager check failed: {e}")
            return False
            
    async def _check_rate_limiter(self) -> bool:
        """Verifică rate limiter"""
        try:
            if rate_limiter is None:
                return False
                
            # Test basic rate limiting
            allowed = await rate_limiter.is_allowed("system_test", "test_operation")
            return isinstance(allowed, bool)
        except Exception as e:
            logger.error(f"❌ Rate limiter check failed: {e}")
            return False
            
    async def _init_platform_manager(self) -> bool:
        """Inițializează platform manager"""
        try:
            if platform_manager is None:
                return False
                
            # Platform manager se inițializează automat
            return True
        except Exception as e:
            logger.error(f"❌ Platform manager init failed: {e}")
            return False
            
    async def _register_platforms(self) -> bool:
        """Înregistrează toate platformele disponibile"""
        try:
            platforms_to_register = [
                ("youtube", YouTubePlatform),
                ("instagram", InstagramPlatform),
                ("tiktok", TikTokPlatform),
            ]
            
            registered_count = 0
            
            for platform_name, platform_class in platforms_to_register:
                try:
                    platform_instance = platform_class()
                    platform_manager.register_platform(platform_name, platform_instance)
                    registered_count += 1
                    logger.info(f"✅ Registered platform: {platform_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to register platform {platform_name}: {e}")
                    
            return registered_count > 0  # Cel puțin o platformă trebuie să fie înregistrată
            
        except Exception as e:
            logger.error(f"❌ Platform registration failed: {e}")
            return False
            
    def _start_health_monitoring(self):
        """Pornește thread-ul de health monitoring"""
        if self.health_check_thread is None or not self.health_check_thread.is_alive():
            self.health_check_thread = threading.Thread(
                target=self._health_monitoring_loop,
                daemon=True,
                name="SystemHealthMonitor"
            )
            self.health_check_thread.start()
            logger.info("📊 Health monitoring started")
            
    def _health_monitoring_loop(self):
        """Loop principal pentru health monitoring"""
        while not self.should_stop and self.state not in [SystemState.STOPPING, SystemState.STOPPED]:
            try:
                asyncio.run(self._perform_health_checks())
                self._update_system_state()
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Health monitoring error: {e}")
                time.sleep(30)  # Retry mai des în caz de eroare
                
    async def _perform_health_checks(self):
        """Efectuează health check-uri pentru toate componentele"""
        
        health_checks = {
            'memory_manager': self._health_check_memory_manager,
            'cache': self._health_check_cache,
            'monitoring': self._health_check_monitoring,
            'platform_manager': self._health_check_platform_manager,
            'rate_limiter': self._health_check_rate_limiter
        }
        
        for component_name, health_check in health_checks.items():
            if component_name in self.components:
                try:
                    is_healthy = await health_check()
                    component = self.components[component_name]
                    component.last_check = time.time()
                    
                    if is_healthy:
                        component.health = "healthy"
                        component.status = "running"
                        # Reset error count on successful health check
                        if component.error_count > 0:
                            component.error_count = max(0, component.error_count - 1)
                    else:
                        component.health = "unhealthy"
                        component.error_count += 1
                        
                        if component.error_count >= self.max_component_errors:
                            component.status = "error"
                        else:
                            component.status = "degraded"
                            
                except Exception as e:
                    component = self.components[component_name]
                    component.health = "unhealthy"
                    component.error_count += 1
                    component.last_error = str(e)
                    component.last_check = time.time()
                    
                    logger.warning(f"⚠️ Health check failed for {component_name}: {e}")
                    
    async def _health_check_memory_manager(self) -> bool:
        """Health check pentru memory manager"""
        try:
            status = await memory_manager.get_memory_status()
            return status.get('status') != 'critical'
        except:
            return False
            
    async def _health_check_cache(self) -> bool:
        """Health check pentru cache"""
        try:
            stats = await cache.get_stats()
            return stats.get('health', {}).get('cleanup_thread_alive', False)
        except:
            return False
            
    async def _health_check_monitoring(self) -> bool:
        """Health check pentru monitoring"""
        try:
            dashboard = await monitoring.get_dashboard_metrics()
            return 'system' in dashboard
        except:
            return False
            
    async def _health_check_platform_manager(self) -> bool:
        """Health check pentru platform manager"""
        try:
            platforms = await platform_manager.get_available_platforms()
            return len(platforms) > 0
        except:
            return False
            
    async def _health_check_rate_limiter(self) -> bool:
        """Health check pentru rate limiter"""
        try:
            stats = rate_limiter.get_stats()
            return isinstance(stats, dict)
        except:
            return False
            
    def _update_system_state(self):
        """Actualizează starea generală a sistemului"""
        if self.state in [SystemState.STOPPING, SystemState.STOPPED]:
            return
            
        critical_unhealthy = 0
        total_unhealthy = 0
        
        for component_name, component in self.components.items():
            if component.health == "unhealthy":
                total_unhealthy += 1
                if component_name in self.critical_components:
                    critical_unhealthy += 1
                    
        # Determină noua stare
        if critical_unhealthy > 0:
            new_state = SystemState.ERROR
        elif total_unhealthy >= self.degraded_threshold:
            new_state = SystemState.DEGRADED
        else:
            new_state = SystemState.RUNNING
            
        if new_state != self.state:
            logger.info(f"🔄 System state changed: {self.state.value} -> {new_state.value}")
            self.state = new_state
            
            # Record în monitoring
            if monitoring:
                monitoring.record_error("system", "state_change", f"State changed to {new_state.value}")
                
    async def get_system_status(self) -> Dict[str, Any]:
        """Obține statusul complet al sistemului"""
        
        uptime = time.time() - self.start_time
        
        component_summary = {}
        for name, component in self.components.items():
            component_summary[name] = {
                'status': component.status,
                'health': component.health,
                'error_count': component.error_count,
                'last_error': component.last_error,
                'last_check_ago': time.time() - component.last_check,
                'is_critical': name in self.critical_components
            }
            
        # Obține metrici de la monitoring dacă e disponibil
        dashboard_metrics = {}
        if monitoring:
            try:
                dashboard_metrics = await monitoring.get_dashboard_metrics()
            except:
                pass
                
        return {
            'system_state': self.state.value,
            'uptime_seconds': int(uptime),
            'uptime_formatted': self._format_uptime(uptime),
            'start_time': self.start_time,
            'components': component_summary,
            'metrics': dashboard_metrics,
            'health_summary': {
                'total_components': len(self.components),
                'healthy_components': len([c for c in self.components.values() if c.health == "healthy"]),
                'unhealthy_components': len([c for c in self.components.values() if c.health == "unhealthy"]),
                'critical_components': len(self.critical_components),
                'critical_unhealthy': len([
                    c for name, c in self.components.items() 
                    if name in self.critical_components and c.health == "unhealthy"
                ])
            }
        }
        
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Formatează uptime în format human-readable"""
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}s"
        elif uptime_seconds < 3600:
            minutes = int(uptime_seconds // 60)
            seconds = int(uptime_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
            
    async def shutdown(self):
        """Oprire elegantă a întregului sistem"""
        
        logger.info("🛑 Starting graceful system shutdown...")
        self.state = SystemState.STOPPING
        self.should_stop = True
        
        # Sequence de shutdown în ordinea dependințelor
        shutdown_sequence = [
            ("health_monitoring", self._stop_health_monitoring),
            ("platform_manager", self._shutdown_platform_manager),
            ("rate_limiter", self._shutdown_rate_limiter),
            ("retry_manager", self._shutdown_retry_manager),
            ("cache", self._shutdown_cache),
            ("monitoring", self._shutdown_monitoring),
            ("memory_manager", self._shutdown_memory_manager),
        ]
        
        for component_name, shutdown_func in shutdown_sequence:
            if component_name in self.components:
                try:
                    logger.info(f"🛑 Stopping {component_name}...")
                    await shutdown_func()
                    logger.info(f"✅ {component_name} stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping {component_name}: {e}")
                    
        self.state = SystemState.STOPPED
        logger.info("🏁 System shutdown completed")
        
    def _stop_health_monitoring(self):
        """Oprește health monitoring"""
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)
            
    async def _shutdown_platform_manager(self):
        """Oprește platform manager"""
        # Platform manager nu are shutdown specific
        pass
        
    async def _shutdown_rate_limiter(self):
        """Oprește rate limiter"""
        if rate_limiter:
            rate_limiter.stop()
            
    async def _shutdown_retry_manager(self):
        """Oprește retry manager"""
        if retry_manager:
            retry_manager.stop()
            
    async def _shutdown_cache(self):
        """Oprește cache"""
        if cache:
            cache.stop()
            
    async def _shutdown_monitoring(self):
        """Oprește monitoring"""
        if monitoring:
            monitoring.stop()
            
    async def _shutdown_memory_manager(self):
        """Oprește memory manager"""
        if memory_manager:
            memory_manager.stop()
            
    def get_component_status(self, component_name: str) -> Optional[ComponentStatus]:
        """Obține statusul unei componente specifice"""
        return self.components.get(component_name)
        
    def is_healthy(self) -> bool:
        """Verifică dacă sistemul este healthy"""
        return self.state == SystemState.RUNNING
        
    def is_operational(self) -> bool:
        """Verifică dacă sistemul este operațional (running sau degraded)"""
        return self.state in [SystemState.RUNNING, SystemState.DEGRADED]

# Singleton instance
system_manager = SystemManager()

# Helper functions
async def initialize_system() -> bool:
    """Helper function pentru inițializarea sistemului"""
    return await system_manager.initialize()
    
async def shutdown_system():
    """Helper function pentru oprirea sistemului"""
    await system_manager.shutdown()
    
async def get_system_health() -> Dict[str, Any]:
    """Helper function pentru obținerea stării sistemului"""
    return await system_manager.get_system_status()

# Main entry point pentru testing
async def main():
    """Entry point principal pentru testing"""
    success = await initialize_system()
    
    if success:
        logger.info("🎉 System initialized successfully!")
        
        # Rulează pentru 30 secunde ca test
        await asyncio.sleep(30)
        
        status = await get_system_health()
        logger.info(f"📊 System status: {status['system_state']}")
        
        await shutdown_system()
    else:
        logger.error("❌ System initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
