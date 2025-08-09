# utils/monitoring.py - Sistema de Monitoring și Observabilitate
# Versiunea: 2.0.0 - Arhitectura Modulară

import time
import logging
import asyncio
import threading
import json
import traceback
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import weakref
from datetime import datetime, timedelta

try:
    from utils.config import config
    from utils.memory_manager import memory_manager, MemoryPriority
except ImportError:
    config = None
    memory_manager = None

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Tipurile de metrici disponibile"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class AlertLevel(Enum):
    """Nivelurile de alerte"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Metric:
    """Structura unei metrici"""
    name: str
    type: MetricType
    value: Union[int, float]
    timestamp: float
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}

@dataclass
class Alert:
    """Structura unei alerte"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: float
    component: str
    metadata: Dict[str, Any] = None
    resolved: bool = False
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class PerformanceTrace:
    """Urmărire performanță pentru operațiuni"""
    trace_id: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
            
    def finish(self, status: str = "completed", error: Optional[str] = None):
        """Finalizează trace-ul"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error

class MetricsCollector:
    """Colector central pentru metrici"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Metrici agregrate
        self.aggregated_metrics = {}
        self.last_aggregation = time.time()
        self.aggregation_interval = 60  # 1 minut
        
    def record_metric(self, 
                     name: str, 
                     metric_type: MetricType, 
                     value: Union[int, float],
                     labels: Optional[Dict[str, str]] = None):
        """Înregistrează o metrică"""
        timestamp = time.time()
        metric = Metric(name, metric_type, value, timestamp, labels or {})
        
        self.metrics.append(metric)
        
        # Actualizează storage-ul specific tipului
        metric_key = self._get_metric_key(name, labels)
        
        if metric_type == MetricType.COUNTER:
            self.counters[metric_key] += value
        elif metric_type == MetricType.GAUGE:
            self.gauges[metric_key] = value
        elif metric_type == MetricType.HISTOGRAM:
            self.histograms[metric_key].append(value)
            # Limitează dimensiunea histogramelor
            if len(self.histograms[metric_key]) > 1000:
                self.histograms[metric_key] = self.histograms[metric_key][-1000:]
        elif metric_type == MetricType.TIMER:
            self.timers[metric_key].append(value)
            
    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Generează cheia pentru o metrică"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
        
    def increment_counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Incrementează un counter"""
        self.record_metric(name, MetricType.COUNTER, value, labels)
        
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Setează o valoare gauge"""
        self.record_metric(name, MetricType.GAUGE, value, labels)
        
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Înregistrează o valoare în histogram"""
        self.record_metric(name, MetricType.HISTOGRAM, value, labels)
        
    def record_timer(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Înregistrează o durată"""
        self.record_metric(name, MetricType.TIMER, duration_ms, labels)
        
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Obține valoarea unui counter"""
        key = self._get_metric_key(name, labels)
        return self.counters.get(key, 0.0)
        
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Obține valoarea unui gauge"""
        key = self._get_metric_key(name, labels)
        return self.gauges.get(key)
        
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Obține statistici pentru histogram"""
        key = self._get_metric_key(name, labels)
        values = self.histograms.get(key, [])
        
        if not values:
            return {}
            
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            "count": n,
            "sum": sum(sorted_values),
            "mean": sum(sorted_values) / n,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": sorted_values[int(n * 0.5)],
            "p90": sorted_values[int(n * 0.9)],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)] if n > 10 else sorted_values[-1]
        }
        
    def get_timer_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Obține statistici pentru timer"""
        key = self._get_metric_key(name, labels)
        values = list(self.timers.get(key, []))
        
        if not values:
            return {}
            
        return {
            "count": len(values),
            "total_ms": sum(values),
            "avg_ms": sum(values) / len(values),
            "min_ms": min(values),
            "max_ms": max(values)
        }

class AlertManager:
    """Manager pentru alerte și notificări"""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts: deque = deque(maxlen=max_alerts)
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.notification_callbacks: List[Callable] = []
        
    def add_alert_rule(self, 
                      rule_id: str,
                      condition: Callable[[Dict[str, Any]], bool],
                      alert_level: AlertLevel,
                      title: str,
                      message_template: str):
        """Adaugă o regulă de alerting"""
        self.alert_rules.append({
            "id": rule_id,
            "condition": condition,
            "level": alert_level,
            "title": title,
            "message_template": message_template
        })
        
    def check_alert_rules(self, metrics: Dict[str, Any]):
        """Verifică regulile de alerting"""
        for rule in self.alert_rules:
            try:
                if rule["condition"](metrics):
                    # Generează alerta dacă nu e deja activă
                    if rule["id"] not in self.active_alerts:
                        alert = Alert(
                            id=rule["id"],
                            level=rule["level"],
                            title=rule["title"],
                            message=rule["message_template"].format(**metrics),
                            timestamp=time.time(),
                            component="monitoring",
                            metadata={"rule_id": rule["id"], "metrics": metrics}
                        )
                        
                        self.trigger_alert(alert)
                        
            except Exception as e:
                logger.warning(f"⚠️ Error checking alert rule {rule['id']}: {e}")
                
    def trigger_alert(self, alert: Alert):
        """Declanșează o alertă"""
        self.alerts.append(alert)
        self.active_alerts[alert.id] = alert
        
        logger.log(
            self._alert_level_to_log_level(alert.level),
            f"🚨 ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}"
        )
        
        # Notifică callback-urile
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"❌ Notification callback error: {e}")
                
    def resolve_alert(self, alert_id: str):
        """Rezolvă o alertă"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]
            
            logger.info(f"✅ Alert resolved: {alert.title}")
            
    def add_notification_callback(self, callback: Callable[[Alert], None]):
        """Adaugă un callback pentru notificări"""
        self.notification_callbacks.append(callback)
        
    def _alert_level_to_log_level(self, level: AlertLevel) -> int:
        """Convertește nivel alertă la nivel logging"""
        mapping = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }
        return mapping.get(level, logging.WARNING)

class PerformanceTracer:
    """Urmărire performanță pentru operațiuni"""
    
    def __init__(self, max_traces: int = 5000):
        self.active_traces: Dict[str, PerformanceTrace] = {}
        self.completed_traces: deque = deque(maxlen=max_traces)
        self._trace_counter = 0
        self._lock = threading.Lock()
        
    def start_trace(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Începe urmărirea unei operațiuni"""
        with self._lock:
            self._trace_counter += 1
            trace_id = f"trace_{self._trace_counter}_{int(time.time() * 1000)}"
            
        trace = PerformanceTrace(
            trace_id=trace_id,
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        self.active_traces[trace_id] = trace
        return trace_id
        
    def finish_trace(self, trace_id: str, status: str = "completed", error: Optional[str] = None):
        """Finalizează urmărirea unei operațiuni"""
        if trace_id in self.active_traces:
            trace = self.active_traces[trace_id]
            trace.finish(status, error)
            
            # Mută la completed traces
            self.completed_traces.append(trace)
            del self.active_traces[trace_id]
            
            return trace.duration_ms
        return None
        
    def get_trace_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Obține statistici pentru trace-uri"""
        traces = [t for t in self.completed_traces 
                 if operation is None or t.operation == operation]
        
        if not traces:
            return {}
            
        durations = [t.duration_ms for t in traces if t.duration_ms is not None]
        
        if not durations:
            return {"count": len(traces)}
            
        return {
            "count": len(traces),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "success_rate": len([t for t in traces if t.status == "completed"]) / len(traces) * 100
        }

class MonitoringSystem:
    """
    Sistema centrală de monitoring și observabilitate
    
    Caracteristici:
    - Metrici în timp real (counters, gauges, histograms, timers)
    - Alerting cu reguli configurabile
    - Performance tracing pentru operațiuni
    - Integrare cu memory manager
    - Dashboard metrics pentru debugging
    - Export pentru sisteme externe
    """
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self.tracer = PerformanceTracer()
        
        # Background monitoring
        self.monitoring_thread = None
        self.should_stop = False
        self.monitoring_interval = 30  # 30 secunde
        
        # System metrics
        self.start_time = time.time()
        
        # Configurare din fișier
        if config:
            monitor_config = config.get('monitoring', {})
            self.monitoring_interval = monitor_config.get('interval', 30)
            
        # Configurare alerte default
        self._setup_default_alerts()
        
        # Pornire monitoring
        self._start_monitoring()
        
        logger.info("📊 Monitoring System initialized")
        
    def _setup_default_alerts(self):
        """Configurează alertele default"""
        
        # Alertă memorie critică
        self.alerts.add_alert_rule(
            rule_id="memory_critical",
            condition=lambda m: m.get('memory_usage_percent', 0) > 95,
            alert_level=AlertLevel.CRITICAL,
            title="Critical Memory Usage",
            message_template="Memory usage is at {memory_usage_percent:.1f}% ({current_memory_mb:.1f}MB)"
        )
        
        # Alertă memorie warning
        self.alerts.add_alert_rule(
            rule_id="memory_warning",
            condition=lambda m: m.get('memory_usage_percent', 0) > 80,
            alert_level=AlertLevel.WARNING,
            title="High Memory Usage",
            message_template="Memory usage is at {memory_usage_percent:.1f}% ({current_memory_mb:.1f}MB)"
        )
        
        # Alertă rate de erori înalt
        self.alerts.add_alert_rule(
            rule_id="high_error_rate",
            condition=lambda m: m.get('error_rate_percent', 0) > 10,
            alert_level=AlertLevel.ERROR,
            title="High Error Rate",
            message_template="Error rate is {error_rate_percent:.1f}% over the last hour"
        )
        
        # Alertă performanță slabă
        self.alerts.add_alert_rule(
            rule_id="slow_downloads",
            condition=lambda m: m.get('avg_download_time_ms', 0) > 30000,  # 30 secunde
            alert_level=AlertLevel.WARNING,
            title="Slow Download Performance",
            message_template="Average download time is {avg_download_time_ms:.0f}ms"
        )
        
    def record_download_attempt(self, platform: str, success: bool, duration_ms: float):
        """Înregistrează o încercare de descărcare"""
        labels = {"platform": platform}
        
        self.metrics.increment_counter("downloads_total", labels=labels)
        
        if success:
            self.metrics.increment_counter("downloads_successful", labels=labels)
        else:
            self.metrics.increment_counter("downloads_failed", labels=labels)
            
        self.metrics.record_timer("download_duration", duration_ms, labels)
        
    def record_error(self, component: str, error_type: str, details: Optional[str] = None):
        """Înregistrează o eroare"""
        labels = {"component": component, "error_type": error_type}
        self.metrics.increment_counter("errors_total", labels=labels)
        
        if details:
            logger.error(f"❌ Error in {component} [{error_type}]: {details}")
            
    def record_rate_limit_hit(self, platform: str, limit_type: str):
        """Înregistrează când se atinge un rate limit"""
        labels = {"platform": platform, "limit_type": limit_type}
        self.metrics.increment_counter("rate_limits_hit", labels=labels)
        
    def record_cache_event(self, event_type: str, hit: bool = False):
        """Înregistrează evenimente cache"""
        labels = {"event_type": event_type}
        self.metrics.increment_counter("cache_events", labels=labels)
        
        if hit:
            self.metrics.increment_counter("cache_hits", labels=labels)
        else:
            self.metrics.increment_counter("cache_misses", labels=labels)
            
    def start_operation_trace(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Începe urmărirea unei operațiuni"""
        return self.tracer.start_trace(operation, metadata)
        
    def finish_operation_trace(self, trace_id: str, success: bool = True, error: Optional[str] = None):
        """Finalizează urmărirea unei operațiuni"""
        status = "completed" if success else "failed"
        duration = self.tracer.finish_trace(trace_id, status, error)
        
        if duration is not None:
            # Înregistrează și ca metrică
            operation = self.tracer.completed_traces[-1].operation if self.tracer.completed_traces else "unknown"
            self.metrics.record_timer(f"operation_{operation}", duration)
            
        return duration
        
    def _start_monitoring(self):
        """Pornește monitoring-ul în background"""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MonitoringSystem"
            )
            self.monitoring_thread.start()
            
    def _monitoring_loop(self):
        """Loop principal de monitoring"""
        while not self.should_stop:
            try:
                self._collect_system_metrics()
                self._check_alerts()
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                time.sleep(60)  # Sleep mai lung în caz de eroare
                
    def _collect_system_metrics(self):
        """Colectează metrici de sistem"""
        try:
            # Memory metrics
            if memory_manager:
                memory_status = asyncio.run(memory_manager.get_memory_status())
                
                self.metrics.set_gauge("memory_usage_mb", memory_status['current_memory_mb'])
                self.metrics.set_gauge("memory_usage_percent", memory_status['usage_percent'])
                self.metrics.set_gauge("memory_tracked_allocations", memory_status['tracked_allocations'])
                
            # Uptime
            uptime_seconds = time.time() - self.start_time
            self.metrics.set_gauge("uptime_seconds", uptime_seconds)
            
            # Active traces
            self.metrics.set_gauge("active_traces", len(self.tracer.active_traces))
            
        except Exception as e:
            logger.warning(f"⚠️ Error collecting system metrics: {e}")
            
    def _check_alerts(self):
        """Verifică condițiile de alertare"""
        try:
            # Pregătește metrici pentru verificarea alertelor
            metrics_for_alerts = {}
            
            # Memory metrics
            if memory_manager:
                memory_status = asyncio.run(memory_manager.get_memory_status())
                metrics_for_alerts.update({
                    'memory_usage_percent': memory_status['usage_percent'],
                    'current_memory_mb': memory_status['current_memory_mb']
                })
                
            # Error rate (ultimele 1000 de metrici)
            recent_errors = self.metrics.get_counter("errors_total")
            recent_total = self.metrics.get_counter("downloads_total")
            
            if recent_total > 0:
                error_rate = (recent_errors / recent_total) * 100
                metrics_for_alerts['error_rate_percent'] = error_rate
                
            # Performance metrics
            download_stats = self.metrics.get_timer_stats("download_duration")
            if download_stats:
                metrics_for_alerts['avg_download_time_ms'] = download_stats.get('avg_ms', 0)
                
            # Verifică regulile
            self.alerts.check_alert_rules(metrics_for_alerts)
            
        except Exception as e:
            logger.warning(f"⚠️ Error checking alerts: {e}")
            
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Obține metrici pentru dashboard"""
        
        # System overview
        uptime_seconds = time.time() - self.start_time
        
        dashboard = {
            "system": {
                "uptime_seconds": int(uptime_seconds),
                "uptime_formatted": self._format_duration(uptime_seconds),
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            },
            "downloads": {
                "total": self.metrics.get_counter("downloads_total"),
                "successful": self.metrics.get_counter("downloads_successful"),
                "failed": self.metrics.get_counter("downloads_failed"),
                "success_rate": 0
            },
            "performance": {},
            "memory": {},
            "alerts": {
                "active_count": len(self.alerts.active_alerts),
                "total_count": len(self.alerts.alerts)
            },
            "platforms": {}
        }
        
        # Calculate success rate
        if dashboard["downloads"]["total"] > 0:
            dashboard["downloads"]["success_rate"] = (
                dashboard["downloads"]["successful"] / dashboard["downloads"]["total"]
            ) * 100
            
        # Download performance
        download_stats = self.metrics.get_timer_stats("download_duration")
        if download_stats:
            dashboard["performance"] = download_stats
            
        # Memory status
        if memory_manager:
            memory_status = await memory_manager.get_memory_status()
            dashboard["memory"] = memory_status
            
        # Platform breakdown
        platforms = ["youtube", "instagram", "tiktok", "facebook", "twitter"]  # Common platforms
        for platform in platforms:
            platform_downloads = self.metrics.get_counter("downloads_total", {"platform": platform})
            if platform_downloads > 0:
                dashboard["platforms"][platform] = {
                    "downloads": platform_downloads,
                    "success": self.metrics.get_counter("downloads_successful", {"platform": platform}),
                    "failed": self.metrics.get_counter("downloads_failed", {"platform": platform})
                }
                
        return dashboard
        
    def _format_duration(self, seconds: float) -> str:
        """Formatează durata în format human-readable"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
            
    def export_metrics(self, format_type: str = "json") -> Union[str, Dict[str, Any]]:
        """Exportă metrici pentru sisteme externe"""
        
        export_data = {
            "timestamp": time.time(),
            "counters": dict(self.metrics.counters),
            "gauges": dict(self.metrics.gauges),
            "histograms": {k: self.metrics.get_histogram_stats(k.split('[')[0], 
                                                              self._parse_labels(k))
                          for k in self.metrics.histograms.keys()},
            "timers": {k: self.metrics.get_timer_stats(k.split('[')[0],
                                                      self._parse_labels(k))
                      for k in self.metrics.timers.keys()},
            "active_alerts": [asdict(alert) for alert in self.alerts.active_alerts.values()],
            "recent_alerts": [asdict(alert) for alert in list(self.alerts.alerts)[-10:]],  # Last 10
            "traces": {
                "active": len(self.tracer.active_traces),
                "completed": len(self.tracer.completed_traces)
            }
        }
        
        if format_type == "json":
            return json.dumps(export_data, indent=2)
        else:
            return export_data
            
    def _parse_labels(self, metric_key: str) -> Optional[Dict[str, str]]:
        """Parse labels din cheia metricii"""
        if '[' not in metric_key:
            return None
            
        label_part = metric_key.split('[')[1].rstrip(']')
        if not label_part:
            return None
            
        labels = {}
        for pair in label_part.split(','):
            if '=' in pair:
                key, value = pair.split('=', 1)
                labels[key.strip()] = value.strip()
                
        return labels if labels else None
        
    def stop(self):
        """Oprește sistemul de monitoring"""
        self.should_stop = True
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
            
        logger.info("📊 Monitoring System stopped")

# Context manager pentru trace-uri
class TraceContext:
    """Context manager pentru urmărire automată"""
    
    def __init__(self, monitoring: MonitoringSystem, operation: str, metadata: Optional[Dict[str, Any]] = None):
        self.monitoring = monitoring
        self.operation = operation
        self.metadata = metadata
        self.trace_id = None
        
    def __enter__(self):
        self.trace_id = self.monitoring.start_operation_trace(self.operation, self.metadata)
        return self.trace_id
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        self.monitoring.finish_operation_trace(self.trace_id, success, error)

# Singleton instance
monitoring = MonitoringSystem()

# Helper functions
def trace_operation(operation: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator pentru urmărire automată a operațiunilor"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with TraceContext(monitoring, operation, metadata):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with TraceContext(monitoring, operation, metadata):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator
