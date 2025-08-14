# tests/test_monitoring.py - Unit tests for Monitoring System
# Versiunea: 2.0.0 - Arhitectura Modulară

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any

# Import system under test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.monitoring import (
    MonitoringSystem, MetricsCollector, AlertManager, PerformanceTracer,
    MetricType, AlertLevel, Metric, Alert, PerformanceTrace,
    TraceContext, monitoring, trace_operation
)


class TestMetricsCollector:
    """Test suite pentru MetricsCollector"""
    
    @pytest.fixture
    def collector(self):
        """Crează o instanță fresh de MetricsCollector"""
        return MetricsCollector(max_metrics=100)
        
    def test_metrics_collector_initialization(self, collector):
        """Test inițializarea MetricsCollector"""
        assert len(collector.metrics) == 0
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.histograms) == 0
        assert len(collector.timers) == 0
        
    def test_record_metric(self, collector):
        """Test înregistrarea unei metrici"""
        collector.record_metric(
            "test_counter", 
            MetricType.COUNTER, 
            5.0, 
            labels={"service": "test"}
        )
        
        assert len(collector.metrics) == 1
        
        metric = collector.metrics[0]
        assert metric.name == "test_counter"
        assert metric.type == MetricType.COUNTER
        assert metric.value == 5.0
        assert metric.labels == {"service": "test"}
        
    def test_increment_counter(self, collector):
        """Test incrementarea unui counter"""
        # Incrementează de mai multe ori
        collector.increment_counter("requests", 1)
        collector.increment_counter("requests", 2)
        collector.increment_counter("requests", 3)
        
        assert collector.get_counter("requests") == 6.0
        
    def test_increment_counter_with_labels(self, collector):
        """Test counter cu labels"""
        collector.increment_counter("requests", 5, labels={"method": "GET"})
        collector.increment_counter("requests", 3, labels={"method": "POST"})
        collector.increment_counter("requests", 2, labels={"method": "GET"})
        
        assert collector.get_counter("requests", {"method": "GET"}) == 7.0
        assert collector.get_counter("requests", {"method": "POST"}) == 3.0
        
    def test_set_gauge(self, collector):
        """Test setarea unei gauge"""
        collector.set_gauge("memory_usage", 75.5)
        collector.set_gauge("memory_usage", 80.2)  # Overwrites previous
        
        assert collector.get_gauge("memory_usage") == 80.2
        
    def test_record_histogram(self, collector):
        """Test înregistrarea în histogram"""
        values = [10, 20, 15, 25, 30, 12, 18]
        
        for value in values:
            collector.record_histogram("response_time", value)
            
        stats = collector.get_histogram_stats("response_time")
        
        assert stats["count"] == 7
        assert stats["min"] == 10
        assert stats["max"] == 30
        assert stats["mean"] == sum(values) / len(values)
        assert "p50" in stats
        assert "p90" in stats
        assert "p95" in stats
        assert "p99" in stats
        
    def test_record_timer(self, collector):
        """Test înregistrarea timer-ului"""
        durations = [100, 200, 150, 300]
        
        for duration in durations:
            collector.record_timer("operation_duration", duration)
            
        stats = collector.get_timer_stats("operation_duration")
        
        assert stats["count"] == 4
        assert stats["total_ms"] == sum(durations)
        assert stats["avg_ms"] == sum(durations) / len(durations)
        assert stats["min_ms"] == min(durations)
        assert stats["max_ms"] == max(durations)
        
    def test_metric_key_generation(self, collector):
        """Test generarea cheilor pentru metrici"""
        # Fără labels
        collector.increment_counter("simple")
        assert collector.get_counter("simple") == 1.0
        
        # Cu labels - ordinea nu contează
        collector.increment_counter("complex", labels={"b": "2", "a": "1"})
        collector.increment_counter("complex", labels={"a": "1", "b": "2"})
        
        assert collector.get_counter("complex", {"a": "1", "b": "2"}) == 2.0
        
    def test_histogram_size_limit(self, collector):
        """Test limitarea dimensiunii histogram-ului"""
        # Adaugă mai mult de 1000 de valori
        for i in range(1500):
            collector.record_histogram("large_histogram", i)
            
        # Ar trebui să păstreze doar ultimele 1000
        key = collector._get_metric_key("large_histogram", None)
        assert len(collector.histograms[key]) == 1000
        
        # Ultimele valori ar trebui să fie 500-1499
        values = collector.histograms[key]
        assert min(values) == 500
        assert max(values) == 1499


class TestAlertManager:
    """Test suite pentru AlertManager"""
    
    @pytest.fixture
    def alert_manager(self):
        """Crează o instanță fresh de AlertManager"""
        return AlertManager(max_alerts=50)
        
    def test_alert_manager_initialization(self, alert_manager):
        """Test inițializarea AlertManager"""
        assert len(alert_manager.alerts) == 0
        assert len(alert_manager.active_alerts) == 0
        assert len(alert_manager.alert_rules) == 0
        assert len(alert_manager.notification_callbacks) == 0
        
    def test_add_alert_rule(self, alert_manager):
        """Test adăugarea unei reguli de alertă"""
        condition = lambda m: m.get('cpu_usage', 0) > 90
        
        alert_manager.add_alert_rule(
            rule_id="high_cpu",
            condition=condition,
            alert_level=AlertLevel.WARNING,
            title="High CPU Usage",
            message_template="CPU usage is {cpu_usage}%"
        )
        
        assert len(alert_manager.alert_rules) == 1
        
        rule = alert_manager.alert_rules[0]
        assert rule["id"] == "high_cpu"
        assert rule["level"] == AlertLevel.WARNING
        assert rule["title"] == "High CPU Usage"
        
    def test_check_alert_rules_trigger(self, alert_manager):
        """Test declanșarea unei alerte"""
        condition = lambda m: m.get('memory_usage', 0) > 85
        
        alert_manager.add_alert_rule(
            rule_id="high_memory",
            condition=condition,
            alert_level=AlertLevel.ERROR,
            title="High Memory",
            message_template="Memory at {memory_usage}%"
        )
        
        # Nu ar trebui să declanșeze
        alert_manager.check_alert_rules({"memory_usage": 70})
        assert len(alert_manager.active_alerts) == 0
        
        # Ar trebui să declanșeze
        alert_manager.check_alert_rules({"memory_usage": 90})
        assert len(alert_manager.active_alerts) == 1
        assert "high_memory" in alert_manager.active_alerts
        
    def test_check_alert_rules_no_duplicate_active(self, alert_manager):
        """Test că aceeași alertă nu se declanșează de mai multe ori"""
        condition = lambda m: m.get('errors', 0) > 5
        
        alert_manager.add_alert_rule(
            rule_id="high_errors",
            condition=condition,
            alert_level=AlertLevel.CRITICAL,
            title="High Error Rate",
            message_template="Errors: {errors}"
        )
        
        # Declanșează de mai multe ori
        alert_manager.check_alert_rules({"errors": 10})
        alert_manager.check_alert_rules({"errors": 15})
        alert_manager.check_alert_rules({"errors": 20})
        
        # Doar o alertă activă
        assert len(alert_manager.active_alerts) == 1
        # Dar toate sunt în istoric
        assert len(alert_manager.alerts) >= 1
        
    def test_resolve_alert(self, alert_manager):
        """Test rezolvarea unei alerte"""
        condition = lambda m: m.get('service_down', False)
        
        alert_manager.add_alert_rule(
            rule_id="service_down",
            condition=condition,
            alert_level=AlertLevel.CRITICAL,
            title="Service Down",
            message_template="Service is down!"
        )
        
        # Declanșează alerta
        alert_manager.check_alert_rules({"service_down": True})
        assert len(alert_manager.active_alerts) == 1
        
        # Rezolvă alerta
        alert_manager.resolve_alert("service_down")
        assert len(alert_manager.active_alerts) == 0
        
        # Verifică că e marcată ca rezolvată în istoric
        assert len(alert_manager.alerts) == 1
        assert alert_manager.alerts[0].resolved == True
        
    def test_notification_callbacks(self, alert_manager):
        """Test callback-urile de notificare"""
        callback_mock = Mock()
        alert_manager.add_notification_callback(callback_mock)
        
        # Creează o alertă direct
        alert = Alert(
            id="test_alert",
            level=AlertLevel.INFO,
            title="Test Alert",
            message="This is a test",
            timestamp=time.time(),
            component="test"
        )
        
        alert_manager.trigger_alert(alert)
        
        # Callback-ul ar trebui să fi fost apelat
        callback_mock.assert_called_once_with(alert)


class TestPerformanceTracer:
    """Test suite pentru PerformanceTracer"""
    
    @pytest.fixture
    def tracer(self):
        """Crează o instanță fresh de PerformanceTracer"""
        return PerformanceTracer(max_traces=100)
        
    def test_tracer_initialization(self, tracer):
        """Test inițializarea PerformanceTracer"""
        assert len(tracer.active_traces) == 0
        assert len(tracer.completed_traces) == 0
        assert tracer._trace_counter == 0
        
    def test_start_trace(self, tracer):
        """Test începerea unui trace"""
        trace_id = tracer.start_trace("test_operation", {"user_id": "123"})
        
        assert trace_id is not None
        assert trace_id in tracer.active_traces
        
        trace = tracer.active_traces[trace_id]
        assert trace.operation == "test_operation"
        assert trace.status == "running"
        assert trace.metadata == {"user_id": "123"}
        assert trace.start_time > 0
        assert trace.end_time is None
        
    def test_finish_trace(self, tracer):
        """Test finalizarea unui trace"""
        trace_id = tracer.start_trace("test_operation")
        
        # Așteaptă puțin pentru a avea durată măsurabilă
        time.sleep(0.1)
        
        duration = tracer.finish_trace(trace_id, "completed")
        
        assert duration is not None
        assert duration > 0
        assert trace_id not in tracer.active_traces
        assert len(tracer.completed_traces) == 1
        
        completed_trace = tracer.completed_traces[0]
        assert completed_trace.status == "completed"
        assert completed_trace.end_time is not None
        assert completed_trace.duration_ms is not None
        assert completed_trace.duration_ms > 0
        
    def test_finish_trace_with_error(self, tracer):
        """Test finalizarea unui trace cu eroare"""
        trace_id = tracer.start_trace("failing_operation")
        
        duration = tracer.finish_trace(trace_id, "failed", "Connection timeout")
        
        assert duration is not None
        completed_trace = tracer.completed_traces[0]
        assert completed_trace.status == "failed"
        assert completed_trace.error == "Connection timeout"
        
    def test_finish_nonexistent_trace(self, tracer):
        """Test finalizarea unui trace inexistent"""
        result = tracer.finish_trace("nonexistent", "completed")
        assert result is None
        
    def test_get_trace_stats(self, tracer):
        """Test obținerea statisticilor pentru trace-uri"""
        # Adaugă câteva trace-uri
        for i in range(5):
            trace_id = tracer.start_trace("test_op")
            time.sleep(0.01)
            status = "completed" if i % 2 == 0 else "failed"
            tracer.finish_trace(trace_id, status)
            
        stats = tracer.get_trace_stats("test_op")
        
        assert stats["count"] == 5
        assert "avg_duration_ms" in stats
        assert "min_duration_ms" in stats
        assert "max_duration_ms" in stats
        assert "success_rate" in stats
        
        # 3 successes din 5 = 60%
        assert stats["success_rate"] == 60.0
        
    def test_get_trace_stats_no_traces(self, tracer):
        """Test stats pentru operațiune fără trace-uri"""
        stats = tracer.get_trace_stats("nonexistent_op")
        assert stats == {}
        
    def test_trace_counter_increment(self, tracer):
        """Test incrementarea counter-ului de trace-uri"""
        initial_counter = tracer._trace_counter
        
        trace_id1 = tracer.start_trace("op1")
        trace_id2 = tracer.start_trace("op2")
        
        assert tracer._trace_counter == initial_counter + 2
        assert trace_id1 != trace_id2  # ID-urile ar trebui să fie unice


class TestMonitoringSystem:
    """Test suite pentru MonitoringSystem"""
    
    @pytest.fixture
    def monitoring_system(self):
        """Crează o instanță de MonitoringSystem pentru testing"""
        with patch('utils.monitoring.monitoring', None):  # Evită singleton issues
            system = MonitoringSystem()
            system.should_stop = True  # Oprește background thread
            if system.monitoring_thread:
                system.monitoring_thread.join(timeout=1)
            return system
            
    def test_monitoring_system_initialization(self, monitoring_system):
        """Test inițializarea MonitoringSystem"""
        assert monitoring_system.metrics is not None
        assert monitoring_system.alerts is not None
        assert monitoring_system.tracer is not None
        assert monitoring_system.start_time > 0
        
        # Verifică că alertele default sunt configurate
        assert len(monitoring_system.alerts.alert_rules) > 0
        
    def test_record_download_attempt(self, monitoring_system):
        """Test înregistrarea unei încercări de descărcare"""
        monitoring_system.record_download_attempt("youtube", True, 1500.0)
        monitoring_system.record_download_attempt("youtube", False, 500.0)
        monitoring_system.record_download_attempt("instagram", True, 800.0)
        
        # Verifică counters
        youtube_total = monitoring_system.metrics.get_counter("downloads_total", {"platform": "youtube"})
        youtube_success = monitoring_system.metrics.get_counter("downloads_successful", {"platform": "youtube"})
        youtube_failed = monitoring_system.metrics.get_counter("downloads_failed", {"platform": "youtube"})
        
        assert youtube_total == 2
        assert youtube_success == 1
        assert youtube_failed == 1
        
        # Verifică că timer-ele sunt înregistrate
        timer_stats = monitoring_system.metrics.get_timer_stats("download_duration", {"platform": "youtube"})
        assert timer_stats["count"] == 2
        
    def test_record_error(self, monitoring_system):
        """Test înregistrarea unei erori"""
        monitoring_system.record_error("youtube", "rate_limit", "API quota exceeded")
        monitoring_system.record_error("instagram", "parsing_error", "Invalid JSON")
        monitoring_system.record_error("youtube", "rate_limit", "Another quota error")
        
        youtube_errors = monitoring_system.metrics.get_counter("errors_total", {
            "component": "youtube", 
            "error_type": "rate_limit"
        })
        
        instagram_errors = monitoring_system.metrics.get_counter("errors_total", {
            "component": "instagram",
            "error_type": "parsing_error"
        })
        
        assert youtube_errors == 2
        assert instagram_errors == 1
        
    def test_record_rate_limit_hit(self, monitoring_system):
        """Test înregistrarea unui rate limit hit"""
        monitoring_system.record_rate_limit_hit("youtube", "api_quota")
        monitoring_system.record_rate_limit_hit("youtube", "requests_per_second")
        
        quota_hits = monitoring_system.metrics.get_counter("rate_limits_hit", {
            "platform": "youtube",
            "limit_type": "api_quota"
        })
        
        rps_hits = monitoring_system.metrics.get_counter("rate_limits_hit", {
            "platform": "youtube", 
            "limit_type": "requests_per_second"
        })
        
        assert quota_hits == 1
        assert rps_hits == 1
        
    def test_record_cache_event(self, monitoring_system):
        """Test înregistrarea evenimentelor de cache"""
        monitoring_system.record_cache_event("metadata", hit=True)
        monitoring_system.record_cache_event("metadata", hit=False)
        monitoring_system.record_cache_event("video_url", hit=True)
        
        cache_events = monitoring_system.metrics.get_counter("cache_events", {"event_type": "metadata"})
        cache_hits = monitoring_system.metrics.get_counter("cache_hits", {"event_type": "metadata"})
        cache_misses = monitoring_system.metrics.get_counter("cache_misses", {"event_type": "metadata"})
        
        assert cache_events == 2
        assert cache_hits == 1
        assert cache_misses == 1
        
    def test_operation_tracing(self, monitoring_system):
        """Test urmărirea operațiunilor"""
        trace_id = monitoring_system.start_operation_trace("download_video", {"platform": "youtube"})
        
        assert trace_id is not None
        assert trace_id in monitoring_system.tracer.active_traces
        
        time.sleep(0.1)  # Simulează operațiune
        
        duration = monitoring_system.finish_operation_trace(trace_id, success=True)
        
        assert duration is not None
        assert duration > 0
        assert trace_id not in monitoring_system.tracer.active_traces
        
    def test_operation_tracing_with_error(self, monitoring_system):
        """Test urmărirea operațiunilor cu eroare"""
        trace_id = monitoring_system.start_operation_trace("download_video")
        
        duration = monitoring_system.finish_operation_trace(
            trace_id, 
            success=False, 
            error="Network timeout"
        )
        
        assert duration is not None
        completed_trace = monitoring_system.tracer.completed_traces[0]
        assert completed_trace.status == "failed"
        assert completed_trace.error == "Network timeout"
        
    @pytest.mark.asyncio
    async def test_get_dashboard_metrics(self, monitoring_system):
        """Test obținerea metrics pentru dashboard"""
        # Adaugă niște date
        monitoring_system.record_download_attempt("youtube", True, 1000)
        monitoring_system.record_download_attempt("instagram", False, 500)
        
        dashboard = await monitoring_system.get_dashboard_metrics()
        
        assert "system" in dashboard
        assert "downloads" in dashboard
        assert "performance" in dashboard
        assert "alerts" in dashboard
        assert "platforms" in dashboard
        
        # Verifică calculele - folosește suma tuturor platformelor
        total_downloads = sum(monitoring_system.metrics.get_counter("downloads_total", {"platform": p}) for p in ["youtube", "instagram"])
        successful_downloads = sum(monitoring_system.metrics.get_counter("downloads_successful", {"platform": p}) for p in ["youtube", "instagram"])
        failed_downloads = sum(monitoring_system.metrics.get_counter("downloads_failed", {"platform": p}) for p in ["youtube", "instagram"])
        
        assert total_downloads == 2
        assert successful_downloads == 1
        assert failed_downloads == 1
        
    def test_export_metrics(self, monitoring_system):
        """Test exportul metrics"""
        # Adaugă niște date
        monitoring_system.metrics.increment_counter("test_counter", 5)
        monitoring_system.metrics.set_gauge("test_gauge", 42.5)
        
        # Export ca dict
        export_data = monitoring_system.export_metrics("dict")
        
        assert isinstance(export_data, dict)
        assert "timestamp" in export_data
        assert "counters" in export_data
        assert "gauges" in export_data
        assert "histograms" in export_data
        assert "timers" in export_data
        
        # Export ca JSON
        json_export = monitoring_system.export_metrics("json")
        
        assert isinstance(json_export, str)
        
        # Verifică că se poate parse înapoi
        import json
        parsed = json.loads(json_export)
        assert "timestamp" in parsed


class TestTraceContext:
    """Test suite pentru TraceContext"""
    
    @pytest.fixture
    def monitoring_mock(self):
        """Mock pentru MonitoringSystem"""
        return Mock(spec=MonitoringSystem)
        
    def test_trace_context_success(self, monitoring_mock):
        """Test TraceContext cu operațiune de succes"""
        monitoring_mock.start_operation_trace.return_value = "trace_123"
        
        with TraceContext(monitoring_mock, "test_operation", {"key": "value"}) as trace_id:
            assert trace_id == "trace_123"
            # Simulează operațiune
            time.sleep(0.01)
            
        # Verifică că metodele au fost apelate corect
        monitoring_mock.start_operation_trace.assert_called_once_with("test_operation", {"key": "value"})
        monitoring_mock.finish_operation_trace.assert_called_once_with("trace_123", True, None)
        
    def test_trace_context_with_exception(self, monitoring_mock):
        """Test TraceContext cu excepție"""
        monitoring_mock.start_operation_trace.return_value = "trace_456"
        
        with pytest.raises(ValueError):
            with TraceContext(monitoring_mock, "failing_operation") as trace_id:
                raise ValueError("Something went wrong")
                
        # Verifică că eroarea a fost înregistrată
        monitoring_mock.finish_operation_trace.assert_called_once_with(
            "trace_456", 
            False, 
            "Something went wrong"
        )


class TestTraceOperationDecorator:
    """Test suite pentru decoratorul trace_operation"""
    
    @pytest.fixture
    def monitoring_mock(self):
        """Mock pentru monitoring system"""
        mock = Mock(spec=MonitoringSystem)
        mock.start_operation_trace.return_value = "trace_789"
        return mock
        
    def test_sync_function_decoration(self, monitoring_mock):
        """Test decorarea unei funcții sincrone"""
        
        with patch('utils.monitoring.monitoring', monitoring_mock):
            @trace_operation("sync_test")
            def sync_function(x, y):
                return x + y
                
            result = sync_function(2, 3)
            
            assert result == 5
            monitoring_mock.start_operation_trace.assert_called_once_with("sync_test", None)
            monitoring_mock.finish_operation_trace.assert_called_once_with("trace_789", True, None)
            
    @pytest.mark.asyncio
    async def test_async_function_decoration(self, monitoring_mock):
        """Test decorarea unei funcții asincrone"""
        
        with patch('utils.monitoring.monitoring', monitoring_mock):
            @trace_operation("async_test", {"component": "test"})
            async def async_function(x, y):
                await asyncio.sleep(0.01)
                return x * y
                
            result = await async_function(4, 5)
            
            assert result == 20
            monitoring_mock.start_operation_trace.assert_called_once_with("async_test", {"component": "test"})
            monitoring_mock.finish_operation_trace.assert_called_once_with("trace_789", True, None)
            
    def test_function_with_exception(self, monitoring_mock):
        """Test decorarea unei funcții care aruncă excepție"""
        
        with patch('utils.monitoring.monitoring', monitoring_mock):
            @trace_operation("error_test")
            def error_function():
                raise RuntimeError("Test error")
                
            with pytest.raises(RuntimeError):
                error_function()
                
            monitoring_mock.finish_operation_trace.assert_called_once_with(
                "trace_789", 
                False, 
                "Test error"
            )


@pytest.mark.integration
class TestMonitoringIntegration:
    """Teste de integrare pentru sistemul de monitoring"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test workflow complet de monitoring"""
        with patch('utils.monitoring.monitoring', None):
            system = MonitoringSystem()
            system.should_stop = True
            
            try:
                # 1. Înregistrează metrici
                system.record_download_attempt("youtube", True, 1500)
                system.record_error("instagram", "parsing", "Invalid data")
                system.record_cache_event("metadata", hit=True)
                
                # 2. Trace operațiune
                trace_id = system.start_operation_trace("video_download")
                time.sleep(0.01)
                system.finish_operation_trace(trace_id, success=True)
                
                # 3. Verifică dashboard metrics
                dashboard = await system.get_dashboard_metrics()
                total_downloads = system.metrics.get_counter("downloads_total", {"platform": "youtube"})
                assert total_downloads == 1
                
                # Verifică că există date în dashboard
                assert "downloads" in dashboard
                assert "platforms" in dashboard
                
                # 4. Export metrics
                export_data = system.export_metrics("dict")
                assert export_data["counters"]["downloads_total[platform=youtube]"] == 1
                
            finally:
                system.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
