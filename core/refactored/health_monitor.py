# core/refactored/health_monitor.py - Monitor de Sănătate pentru Platforme
# Versiunea: 4.0.0 - Arhitectura Refactorizată

import asyncio
import logging
import time
import statistics
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import psutil
import aiohttp

try:
    from platforms.base.abstract_platform import (
        AbstractPlatform, PlatformCapability, ContentType, 
        VideoMetadata, DownloadResult, QualityLevel,
        PlatformError, UnsupportedURLError, DownloadError
    )
    from core.refactored.platform_registry import platform_registry, PlatformStatus
except ImportError:
    # Fallback pentru development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import (
        AbstractPlatform, PlatformCapability, ContentType,
        VideoMetadata, DownloadResult, QualityLevel,
        PlatformError, UnsupportedURLError, DownloadError
    )
    from core.refactored.platform_registry import platform_registry, PlatformStatus

logger = logging.getLogger(__name__)

class HealthCheckType(Enum):
    """Tipurile de health check-uri"""
    BASIC = "basic"  # Verificare de bază
    CONNECTIVITY = "connectivity"  # Test de conectivitate
    FUNCTIONALITY = "functionality"  # Test funcțional complet
    PERFORMANCE = "performance"  # Test de performanță
    STRESS = "stress"  # Test de stres

class AlertSeverity(Enum):
    """Severitatea alertelor"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthMetric:
    """Metrică de sănătate"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    
    def is_healthy(self) -> bool:
        """Verifică dacă metrica este în parametri normali"""
        if self.threshold_critical is not None and self.value >= self.threshold_critical:
            return False
        return True
    
    def get_severity(self) -> AlertSeverity:
        """Obține severitatea bazată pe praguri"""
        if self.threshold_critical is not None and self.value >= self.threshold_critical:
            return AlertSeverity.CRITICAL
        elif self.threshold_warning is not None and self.value >= self.threshold_warning:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

@dataclass
class HealthCheckResult:
    """Rezultatul unui health check"""
    platform_name: str
    check_type: HealthCheckType
    success: bool
    response_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    metrics: List[HealthMetric] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'platform_name': self.platform_name,
            'check_type': self.check_type.value,
            'success': self.success,
            'response_time': self.response_time,
            'timestamp': self.timestamp.isoformat(),
            'error_message': self.error_message,
            'metrics': [{
                'name': m.name,
                'value': m.value,
                'unit': m.unit,
                'severity': m.get_severity().value
            } for m in self.metrics],
            'details': self.details
        }

@dataclass
class Alert:
    """Alertă de sănătate"""
    id: str
    platform_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def resolve(self):
        """Marchează alerta ca rezolvată"""
        self.resolved = True
        self.resolved_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'platform_name': self.platform_name,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'details': self.details
        }

class PlatformHealthTracker:
    """Tracker pentru sănătatea unei platforme individuale"""
    
    def __init__(self, platform_name: str, max_history: int = 100):
        self.platform_name = platform_name
        self.max_history = max_history
        
        # Istoric health checks
        self.health_history: deque = deque(maxlen=max_history)
        
        # Metrici de performanță
        self.response_times: deque = deque(maxlen=max_history)
        self.success_rate_window: deque = deque(maxlen=50)  # Ultimele 50 de checks
        
        # Statistici
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.last_successful_check: Optional[datetime] = None
        self.last_failed_check: Optional[datetime] = None
        
        # Stare curentă
        self.current_status = PlatformStatus.HEALTHY
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        
        # Alertele active
        self.active_alerts: Dict[str, Alert] = {}
    
    def add_health_check_result(self, result: HealthCheckResult):
        """Adaugă un rezultat de health check"""
        self.health_history.append(result)
        self.response_times.append(result.response_time)
        self.success_rate_window.append(result.success)
        
        self.total_checks += 1
        
        if result.success:
            self.successful_checks += 1
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            self.last_successful_check = result.timestamp
            
            # Rezolvă alertele dacă platforma s-a recuperat
            if self.consecutive_successes >= 3:
                self._resolve_alerts()
                if self.current_status != PlatformStatus.HEALTHY:
                    self.current_status = PlatformStatus.HEALTHY
                    logger.info(f"✅ Platform {self.platform_name} recovered to HEALTHY status")
        else:
            self.failed_checks += 1
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            self.last_failed_check = result.timestamp
            
            # Actualizează statusul bazat pe eșecuri consecutive
            if self.consecutive_failures >= 5:
                self.current_status = PlatformStatus.FAILED
            elif self.consecutive_failures >= 3:
                self.current_status = PlatformStatus.DEGRADED
    
    def get_success_rate(self, window_size: Optional[int] = None) -> float:
        """Calculează rata de succes"""
        if window_size:
            recent_results = list(self.success_rate_window)[-window_size:]
        else:
            recent_results = list(self.success_rate_window)
        
        if not recent_results:
            return 0.0
        
        return sum(recent_results) / len(recent_results) * 100
    
    def get_average_response_time(self, window_size: Optional[int] = None) -> float:
        """Calculează timpul mediu de răspuns"""
        if window_size:
            recent_times = list(self.response_times)[-window_size:]
        else:
            recent_times = list(self.response_times)
        
        if not recent_times:
            return 0.0
        
        return statistics.mean(recent_times)
    
    def get_response_time_percentiles(self) -> Dict[str, float]:
        """Calculează percentilele pentru timpul de răspuns"""
        if not self.response_times:
            return {'p50': 0, 'p90': 0, 'p95': 0, 'p99': 0}
        
        times = sorted(self.response_times)
        n = len(times)
        
        return {
            'p50': times[int(n * 0.5)] if n > 0 else 0,
            'p90': times[int(n * 0.9)] if n > 0 else 0,
            'p95': times[int(n * 0.95)] if n > 0 else 0,
            'p99': times[int(n * 0.99)] if n > 0 else 0
        }
    
    def add_alert(self, alert: Alert):
        """Adaugă o alertă activă"""
        self.active_alerts[alert.id] = alert
        logger.warning(f"🚨 Alert added for {self.platform_name}: {alert.message}")
    
    def _resolve_alerts(self):
        """Rezolvă toate alertele active"""
        for alert in self.active_alerts.values():
            if not alert.resolved:
                alert.resolve()
                logger.info(f"✅ Alert resolved for {self.platform_name}: {alert.message}")
        
        self.active_alerts.clear()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Returnează un sumar al sănătății platformei"""
        return {
            'platform_name': self.platform_name,
            'current_status': self.current_status.value,
            'success_rate': self.get_success_rate(),
            'average_response_time': self.get_average_response_time(),
            'response_time_percentiles': self.get_response_time_percentiles(),
            'total_checks': self.total_checks,
            'successful_checks': self.successful_checks,
            'failed_checks': self.failed_checks,
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'last_successful_check': self.last_successful_check.isoformat() if self.last_successful_check else None,
            'last_failed_check': self.last_failed_check.isoformat() if self.last_failed_check else None,
            'active_alerts': len(self.active_alerts),
            'recent_checks': [result.to_dict() for result in list(self.health_history)[-10:]]
        }

class HealthMonitor:
    """
    Monitor centralizat pentru sănătatea tuturor platformelor.
    Efectuează health checks periodice, monitorizează metrici de performanță,
    generează alerte și oferă rapoarte de sănătate.
    """
    
    def __init__(self, check_interval: int = 300, alert_callbacks: List[Callable] = None):
        # Configurare
        self.check_interval = check_interval  # 5 minute default
        self.alert_callbacks = alert_callbacks or []
        
        # Trackere pentru platforme
        self.platform_trackers: Dict[str, PlatformHealthTracker] = {}
        
        # Istoric global
        self.global_health_history: deque = deque(maxlen=1000)
        self.system_metrics_history: deque = deque(maxlen=100)
        
        # Alertele globale
        self.global_alerts: Dict[str, Alert] = {}
        self.alert_counter = 0
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self._shutdown = False
        
        # Test URLs pentru connectivity checks
        self.test_urls = {
            'youtube': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'instagram': 'https://www.instagram.com/p/test/',
            'tiktok': 'https://www.tiktok.com/@test/video/test',
            'facebook': 'https://www.facebook.com/test/videos/test/',
            'twitter': 'https://twitter.com/test/status/test'
        }
        
        # Statistici globale
        self.global_stats = {
            'total_platforms': 0,
            'healthy_platforms': 0,
            'degraded_platforms': 0,
            'failed_platforms': 0,
            'total_checks_performed': 0,
            'total_alerts_generated': 0,
            'average_system_response_time': 0.0,
            'system_uptime': 0.0
        }
        
        self.start_time = datetime.now()
        
        logger.info("🏥 Health Monitor initialized")
    
    async def initialize(self):
        """Inițializează monitorul de sănătate"""
        logger.info("🚀 Starting Health Monitor...")
        
        # Asigură-te că Platform Registry este inițializat
        if not platform_registry.platforms:
            await platform_registry.initialize()
        
        # Inițializează trackere pentru toate platformele
        for platform_name in platform_registry.platforms:
            self.platform_trackers[platform_name] = PlatformHealthTracker(platform_name)
        
        # Start background tasks
        await self._start_background_tasks()
        
        logger.info(f"✅ Health Monitor initialized for {len(self.platform_trackers)} platforms")
    
    async def _start_background_tasks(self):
        """Pornește task-urile de background"""
        # Health check periodic
        health_task = asyncio.create_task(self._periodic_health_checks())
        self.background_tasks.append(health_task)
        
        # System metrics collection
        metrics_task = asyncio.create_task(self._collect_system_metrics())
        self.background_tasks.append(metrics_task)
        
        # Alert cleanup
        cleanup_task = asyncio.create_task(self._periodic_alert_cleanup())
        self.background_tasks.append(cleanup_task)
        
        logger.info("🔄 Started health monitoring background tasks")
    
    async def _periodic_health_checks(self):
        """Efectuează health checks periodice pentru toate platformele"""
        while not self._shutdown:
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic health checks: {e}")
                await asyncio.sleep(60)  # Retry după 1 minut
    
    async def _run_health_checks(self):
        """Rulează health checks pentru toate platformele"""
        logger.info("🔍 Running health checks for all platforms...")
        
        # Rulează health checks în paralel
        tasks = []
        for platform_name in self.platform_trackers:
            task = asyncio.create_task(self._check_platform_health(platform_name))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesează rezultatele
        successful_checks = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                platform_name = list(self.platform_trackers.keys())[i]
                logger.error(f"❌ Health check failed for {platform_name}: {result}")
            elif result and result.success:
                successful_checks += 1
        
        # Actualizează statisticile globale
        self._update_global_stats()
        
        logger.info(f"✅ Health checks completed: {successful_checks}/{len(self.platform_trackers)} platforms healthy")
    
    async def _check_platform_health(self, platform_name: str) -> Optional[HealthCheckResult]:
        """Efectuează health check pentru o platformă specifică"""
        start_time = time.time()
        
        try:
            platform = platform_registry.platforms.get(platform_name)
            if not platform:
                return None
            
            # Basic health check
            result = await self._perform_basic_health_check(platform)
            
            # Adaugă rezultatul la tracker
            tracker = self.platform_trackers[platform_name]
            tracker.add_health_check_result(result)
            
            # Verifică dacă trebuie generate alerte
            await self._check_for_alerts(platform_name, result)
            
            return result
            
        except Exception as e:
            # Creează rezultat de eșec
            response_time = time.time() - start_time
            result = HealthCheckResult(
                platform_name=platform_name,
                check_type=HealthCheckType.BASIC,
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
            
            # Adaugă la tracker
            if platform_name in self.platform_trackers:
                self.platform_trackers[platform_name].add_health_check_result(result)
            
            return result
    
    async def _perform_basic_health_check(self, platform: AbstractPlatform) -> HealthCheckResult:
        """Efectuează un health check de bază"""
        start_time = time.time()
        metrics = []
        details = {}
        
        try:
            # Test 1: Verifică dacă platforma este activă
            if not platform.enabled:
                raise PlatformError("Platform is disabled")
            
            # Test 2: Obține statusul de sănătate din platformă
            health_status = platform.get_health_status()
            details['platform_health_status'] = health_status
            
            # Test 3: Test de conectivitate (dacă există URL de test)
            test_url = self.test_urls.get(platform.platform_name.lower())
            if test_url:
                connectivity_time = await self._test_connectivity(platform, test_url)
                metrics.append(HealthMetric(
                    name='connectivity_response_time',
                    value=connectivity_time,
                    unit='seconds',
                    threshold_warning=5.0,
                    threshold_critical=10.0
                ))
            
            # Test 4: Verifică capabilitățile
            capabilities_working = await self._test_capabilities(platform)
            details['capabilities_status'] = capabilities_working
            
            response_time = time.time() - start_time
            
            # Determină succesul bazat pe statusul platformei
            success = health_status.get('status') == 'healthy'
            
            return HealthCheckResult(
                platform_name=platform.platform_name,
                check_type=HealthCheckType.BASIC,
                success=success,
                response_time=response_time,
                metrics=metrics,
                details=details
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                platform_name=platform.platform_name,
                check_type=HealthCheckType.BASIC,
                success=False,
                response_time=response_time,
                error_message=str(e),
                details=details
            )
    
    async def _test_connectivity(self, platform: AbstractPlatform, test_url: str) -> float:
        """Testează conectivitatea platformei"""
        start_time = time.time()
        
        try:
            # Încearcă să verifice dacă platforma suportă URL-ul
            supports = platform.supports_url(test_url)
            
            # Dacă suportă, încearcă să extragă metadata (fără să descarce)
            if supports:
                try:
                    # Timeout scurt pentru test
                    await asyncio.wait_for(
                        platform.extract_metadata(test_url),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    pass  # Timeout-ul este acceptabil pentru test
                except Exception:
                    pass  # Alte erori sunt acceptabile pentru test
            
            return time.time() - start_time
            
        except Exception:
            return time.time() - start_time
    
    async def _test_capabilities(self, platform: AbstractPlatform) -> Dict[str, bool]:
        """Testează capabilitățile platformei"""
        capabilities_status = {}
        
        for capability in platform.capabilities:
            try:
                # Test simplu pentru fiecare capabilitate
                if capability == PlatformCapability.DOWNLOAD_VIDEO:
                    capabilities_status['download_video'] = hasattr(platform, 'download_content')
                elif capability == PlatformCapability.GET_METADATA:
                    capabilities_status['get_metadata'] = hasattr(platform, 'extract_metadata')
                elif capability == PlatformCapability.GET_THUMBNAIL:
                    capabilities_status['get_thumbnail'] = hasattr(platform, 'get_thumbnail')
                else:
                    capabilities_status[capability.value] = True
            except Exception:
                capabilities_status[capability.value] = False
        
        return capabilities_status
    
    async def _check_for_alerts(self, platform_name: str, result: HealthCheckResult):
        """Verifică dacă trebuie generate alerte"""
        tracker = self.platform_trackers[platform_name]
        
        # Alert pentru eșecuri consecutive
        if tracker.consecutive_failures >= 3:
            alert_id = f"consecutive_failures_{platform_name}"
            if alert_id not in tracker.active_alerts:
                alert = Alert(
                    id=alert_id,
                    platform_name=platform_name,
                    severity=AlertSeverity.ERROR if tracker.consecutive_failures >= 5 else AlertSeverity.WARNING,
                    message=f"Platform has {tracker.consecutive_failures} consecutive failures",
                    details={'consecutive_failures': tracker.consecutive_failures}
                )
                tracker.add_alert(alert)
                await self._send_alert(alert)
        
        # Alert pentru rata de succes scăzută
        success_rate = tracker.get_success_rate(window_size=20)
        if success_rate < 50 and tracker.total_checks >= 10:
            alert_id = f"low_success_rate_{platform_name}"
            if alert_id not in tracker.active_alerts:
                alert = Alert(
                    id=alert_id,
                    platform_name=platform_name,
                    severity=AlertSeverity.WARNING,
                    message=f"Platform has low success rate: {success_rate:.1f}%",
                    details={'success_rate': success_rate}
                )
                tracker.add_alert(alert)
                await self._send_alert(alert)
        
        # Alert pentru timp de răspuns mare
        avg_response_time = tracker.get_average_response_time(window_size=10)
        if avg_response_time > 30:  # 30 secunde
            alert_id = f"high_response_time_{platform_name}"
            if alert_id not in tracker.active_alerts:
                alert = Alert(
                    id=alert_id,
                    platform_name=platform_name,
                    severity=AlertSeverity.WARNING,
                    message=f"Platform has high response time: {avg_response_time:.2f}s",
                    details={'average_response_time': avg_response_time}
                )
                tracker.add_alert(alert)
                await self._send_alert(alert)
    
    async def _send_alert(self, alert: Alert):
        """Trimite o alertă prin callback-urile configurate"""
        self.global_alerts[alert.id] = alert
        self.global_stats['total_alerts_generated'] += 1
        
        logger.warning(f"🚨 ALERT [{alert.severity.value.upper()}] {alert.platform_name}: {alert.message}")
        
        # Apelează callback-urile de alertă
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"❌ Alert callback failed: {e}")
    
    async def _collect_system_metrics(self):
        """Colectează metrici de sistem"""
        while not self._shutdown:
            try:
                # Colectează metrici de sistem
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                system_metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024**3)
                }
                
                self.system_metrics_history.append(system_metrics)
                
                # Verifică pentru alerte de sistem
                await self._check_system_alerts(system_metrics)
                
                await asyncio.sleep(60)  # Colectează la fiecare minut
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error collecting system metrics: {e}")
                await asyncio.sleep(60)
    
    async def _check_system_alerts(self, metrics: Dict[str, Any]):
        """Verifică pentru alerte de sistem"""
        # Alert pentru CPU mare
        if metrics['cpu_percent'] > 90:
            alert_id = "high_cpu_usage"
            if alert_id not in self.global_alerts or self.global_alerts[alert_id].resolved:
                alert = Alert(
                    id=alert_id,
                    platform_name="system",
                    severity=AlertSeverity.WARNING,
                    message=f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                    details=metrics
                )
                await self._send_alert(alert)
        
        # Alert pentru memorie mare
        if metrics['memory_percent'] > 90:
            alert_id = "high_memory_usage"
            if alert_id not in self.global_alerts or self.global_alerts[alert_id].resolved:
                alert = Alert(
                    id=alert_id,
                    platform_name="system",
                    severity=AlertSeverity.WARNING,
                    message=f"High memory usage: {metrics['memory_percent']:.1f}%",
                    details=metrics
                )
                await self._send_alert(alert)
    
    async def _periodic_alert_cleanup(self):
        """Cleanup periodic al alertelor rezolvate"""
        while not self._shutdown:
            try:
                await asyncio.sleep(3600)  # Cleanup la fiecare oră
                self._cleanup_resolved_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in alert cleanup: {e}")
    
    def _cleanup_resolved_alerts(self):
        """Curăță alertele rezolvate vechi"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Cleanup alerte globale
        resolved_alerts = []
        for alert_id, alert in self.global_alerts.items():
            if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff_time:
                resolved_alerts.append(alert_id)
        
        for alert_id in resolved_alerts:
            del self.global_alerts[alert_id]
        
        # Cleanup alerte din trackere
        for tracker in self.platform_trackers.values():
            resolved_platform_alerts = []
            for alert_id, alert in tracker.active_alerts.items():
                if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff_time:
                    resolved_platform_alerts.append(alert_id)
            
            for alert_id in resolved_platform_alerts:
                del tracker.active_alerts[alert_id]
        
        if resolved_alerts:
            logger.info(f"🧹 Cleaned up {len(resolved_alerts)} resolved alerts")
    
    def _update_global_stats(self):
        """Actualizează statisticile globale"""
        self.global_stats['total_platforms'] = len(self.platform_trackers)
        
        healthy_count = 0
        degraded_count = 0
        failed_count = 0
        total_checks = 0
        total_response_times = []
        
        for tracker in self.platform_trackers.values():
            total_checks += tracker.total_checks
            
            if tracker.current_status == PlatformStatus.HEALTHY:
                healthy_count += 1
            elif tracker.current_status == PlatformStatus.DEGRADED:
                degraded_count += 1
            elif tracker.current_status == PlatformStatus.FAILED:
                failed_count += 1
            
            if tracker.response_times:
                total_response_times.extend(tracker.response_times)
        
        self.global_stats['healthy_platforms'] = healthy_count
        self.global_stats['degraded_platforms'] = degraded_count
        self.global_stats['failed_platforms'] = failed_count
        self.global_stats['total_checks_performed'] = total_checks
        
        if total_response_times:
            self.global_stats['average_system_response_time'] = statistics.mean(total_response_times)
        
        # Uptime
        uptime = datetime.now() - self.start_time
        self.global_stats['system_uptime'] = uptime.total_seconds()
    
    def get_health_dashboard(self) -> Dict[str, Any]:
        """Returnează dashboard-ul complet de sănătate"""
        platform_summaries = {}
        for platform_name, tracker in self.platform_trackers.items():
            platform_summaries[platform_name] = tracker.get_health_summary()
        
        active_alerts = [alert.to_dict() for alert in self.global_alerts.values() if not alert.resolved]
        recent_system_metrics = list(self.system_metrics_history)[-10:] if self.system_metrics_history else []
        
        return {
            'global_stats': self.global_stats,
            'platform_summaries': platform_summaries,
            'active_alerts': active_alerts,
            'recent_system_metrics': recent_system_metrics,
            'health_check_interval': self.check_interval,
            'monitor_uptime': (datetime.now() - self.start_time).total_seconds()
        }
    
    def get_platform_health(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Obține sănătatea unei platforme specifice"""
        tracker = self.platform_trackers.get(platform_name)
        if not tracker:
            return None
        
        return tracker.get_health_summary()
    
    def add_alert_callback(self, callback: Callable):
        """Adaugă un callback pentru alerte"""
        self.alert_callbacks.append(callback)
        logger.info("📎 Added alert callback")
    
    async def force_health_check(self, platform_name: Optional[str] = None):
        """Forțează un health check imediat"""
        if platform_name:
            if platform_name in self.platform_trackers:
                await self._check_platform_health(platform_name)
                logger.info(f"🔍 Forced health check for {platform_name}")
            else:
                logger.warning(f"⚠️ Platform {platform_name} not found")
        else:
            await self._run_health_checks()
            logger.info("🔍 Forced health check for all platforms")
    
    async def shutdown(self):
        """Oprește monitorul de sănătate"""
        logger.info("🛑 Shutting down Health Monitor...")
        
        self._shutdown = True
        
        # Anulează task-urile de background
        for task in self.background_tasks:
            task.cancel()
        
        # Așteaptă ca task-urile să se termine
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("✅ Health Monitor shutdown complete")
    
    def __str__(self) -> str:
        healthy = self.global_stats['healthy_platforms']
        total = self.global_stats['total_platforms']
        return f"HealthMonitor(platforms={total}, healthy={healthy})"
    
    def __repr__(self) -> str:
        return (f"HealthMonitor(platforms={self.global_stats['total_platforms']}, "
                f"healthy={self.global_stats['healthy_platforms']}, "
                f"check_interval={self.check_interval})")


# Singleton instance pentru utilizare globală
health_monitor = HealthMonitor()