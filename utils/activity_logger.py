# utils/activity_logger.py - Sistem de Logging pentru Activitățile Botului
# Versiunea: 1.0.0 - Logging Complet

import os
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class ActivityType(Enum):
    """Tipurile de activități monitorizate"""
    DOWNLOAD_SUCCESS = "download_success"
    DOWNLOAD_ERROR = "download_error"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_ERROR = "command_error"
    USER_MESSAGE = "user_message"
    PLATFORM_ERROR = "platform_error"
    RATE_LIMIT_HIT = "rate_limit_hit"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    SYSTEM_ERROR = "system_error"
    WEBHOOK_RECEIVED = "webhook_received"
    BOT_STARTUP = "bot_startup"
    BOT_SHUTDOWN = "bot_shutdown"

class LogLevel(Enum):
    """Nivelurile de logging"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ActivityLog:
    """Structura unui log de activitate"""
    id: str
    timestamp: float
    activity_type: ActivityType
    level: LogLevel
    user_id: Optional[int]
    chat_id: Optional[int]
    platform: Optional[str]
    url: Optional[str]
    command: Optional[str]
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertește log-ul în dicționar"""
        data = asdict(self)
        data['activity_type'] = self.activity_type.value
        data['level'] = self.level.value
        data['datetime'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data
    
    def to_readable_string(self) -> str:
        """Convertește log-ul într-un string lizibil"""
        dt = datetime.fromtimestamp(self.timestamp)
        status_icon = "✅" if self.success else "❌"
        
        base_info = f"{status_icon} {dt.strftime('%H:%M:%S')} - {self.message}"
        
        details = []
        if self.user_id:
            details.append(f"User: {self.user_id}")
        if self.platform:
            details.append(f"Platform: {self.platform}")
        if self.duration_ms:
            details.append(f"Duration: {self.duration_ms:.1f}ms")
        if self.error_code:
            details.append(f"Error: {self.error_code}")
            
        if details:
            base_info += f" ({', '.join(details)})"
            
        return base_info

class ActivityLogger:
    """Sistem de logging pentru activitățile botului"""
    
    def __init__(self, max_logs: int = 10000, log_file_path: Optional[str] = None):
        self.max_logs = max_logs
        self.logs = deque(maxlen=max_logs)
        self.log_file_path = log_file_path or "logs/bot_activity.jsonl"
        self.stats = defaultdict(int)
        self.platform_stats = defaultdict(lambda: defaultdict(int))
        self.hourly_stats = defaultdict(lambda: defaultdict(int))
        self.lock = threading.Lock()
        self.file_lock = threading.Lock()
        
        # Asigură că directorul pentru log-uri există
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        
        logger.info(f"📝 Activity Logger initialized with max {max_logs} logs")
    
    def _generate_log_id(self) -> str:
        """Generează un ID unic pentru log"""
        return f"log_{int(time.time() * 1000)}_{len(self.logs)}"
    
    def log_activity(self, 
                    activity_type: ActivityType,
                    message: str,
                    level: LogLevel = LogLevel.INFO,
                    user_id: Optional[int] = None,
                    chat_id: Optional[int] = None,
                    platform: Optional[str] = None,
                    url: Optional[str] = None,
                    command: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None,
                    duration_ms: Optional[float] = None,
                    success: bool = True,
                    error_code: Optional[str] = None):
        """Înregistrează o activitate"""
        
        log_entry = ActivityLog(
            id=self._generate_log_id(),
            timestamp=time.time(),
            activity_type=activity_type,
            level=level,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            url=url,
            command=command,
            message=message,
            details=details,
            duration_ms=duration_ms,
            success=success,
            error_code=error_code
        )
        
        with self.lock:
            self.logs.append(log_entry)
            self._update_stats(log_entry)
        
        # Scrie în fișier async
        asyncio.create_task(self._write_to_file(log_entry))
        
        # Log în sistemul standard de logging
        log_level = getattr(logging, level.value.upper())
        logger.log(log_level, f"[{activity_type.value}] {message}")
    
    def _update_stats(self, log_entry: ActivityLog):
        """Actualizează statisticile"""
        # Statistici generale
        self.stats[f"total_{log_entry.activity_type.value}"] += 1
        self.stats[f"total_{log_entry.level.value}"] += 1
        
        if log_entry.success:
            self.stats["total_success"] += 1
        else:
            self.stats["total_errors"] += 1
        
        # Statistici per platformă
        if log_entry.platform:
            platform_key = log_entry.platform.lower()
            self.platform_stats[platform_key]["total"] += 1
            if log_entry.success:
                self.platform_stats[platform_key]["success"] += 1
            else:
                self.platform_stats[platform_key]["errors"] += 1
        
        # Statistici pe ore
        hour_key = datetime.fromtimestamp(log_entry.timestamp).strftime("%Y-%m-%d_%H")
        self.hourly_stats[hour_key][log_entry.activity_type.value] += 1
    
    async def _write_to_file(self, log_entry: ActivityLog):
        """Scrie log-ul în fișier"""
        try:
            with self.file_lock:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Error writing log to file: {e}")
    
    def get_logs(self, 
                hours: int = 24,
                activity_types: Optional[List[ActivityType]] = None,
                platforms: Optional[List[str]] = None,
                success_only: Optional[bool] = None,
                user_id: Optional[int] = None) -> List[ActivityLog]:
        """Obține log-urile filtrate"""
        
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            filtered_logs = []
            
            for log in self.logs:
                # Filtru timp
                if log.timestamp < cutoff_time:
                    continue
                
                # Filtru tip activitate
                if activity_types and log.activity_type not in activity_types:
                    continue
                
                # Filtru platformă
                if platforms and log.platform and log.platform.lower() not in [p.lower() for p in platforms]:
                    continue
                
                # Filtru success
                if success_only is not None and log.success != success_only:
                    continue
                
                # Filtru user
                if user_id and log.user_id != user_id:
                    continue
                
                filtered_logs.append(log)
            
            # Sortează după timestamp (cel mai recent primul)
            filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
            
            return filtered_logs
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Obține statistici pentru perioada specificată"""
        logs = self.get_logs(hours=hours)
        
        stats = {
            "period_hours": hours,
            "total_activities": len(logs),
            "success_rate": 0,
            "activity_breakdown": defaultdict(int),
            "platform_breakdown": defaultdict(lambda: {"total": 0, "success": 0, "errors": 0}),
            "error_breakdown": defaultdict(int),
            "hourly_activity": defaultdict(int),
            "top_errors": [],
            "performance_metrics": {
                "avg_download_time": 0,
                "fastest_download": None,
                "slowest_download": None
            }
        }
        
        if not logs:
            return stats
        
        success_count = 0
        download_times = []
        error_messages = defaultdict(int)
        
        for log in logs:
            # Breakdown activități
            stats["activity_breakdown"][log.activity_type.value] += 1
            
            # Success rate
            if log.success:
                success_count += 1
            else:
                if log.error_code:
                    stats["error_breakdown"][log.error_code] += 1
                error_messages[log.message] += 1
            
            # Platform breakdown
            if log.platform:
                platform = log.platform.lower()
                stats["platform_breakdown"][platform]["total"] += 1
                if log.success:
                    stats["platform_breakdown"][platform]["success"] += 1
                else:
                    stats["platform_breakdown"][platform]["errors"] += 1
            
            # Activitate pe ore
            hour = datetime.fromtimestamp(log.timestamp).strftime("%H:00")
            stats["hourly_activity"][hour] += 1
            
            # Timpi de download
            if log.duration_ms and log.activity_type == ActivityType.DOWNLOAD_SUCCESS:
                download_times.append(log.duration_ms)
        
        # Calculează success rate
        if len(logs) > 0:
            stats["success_rate"] = (success_count / len(logs)) * 100
        
        # Top erori
        stats["top_errors"] = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Metrici de performanță
        if download_times:
            stats["performance_metrics"]["avg_download_time"] = sum(download_times) / len(download_times)
            stats["performance_metrics"]["fastest_download"] = min(download_times)
            stats["performance_metrics"]["slowest_download"] = max(download_times)
        
        return dict(stats)
    
    def generate_report(self, hours: int = 24, format_type: str = "text") -> str:
        """Generează un raport complet"""
        logs = self.get_logs(hours=hours)
        stats = self.get_statistics(hours=hours)
        
        if format_type == "json":
            return json.dumps({
                "logs": [log.to_dict() for log in logs],
                "statistics": stats
            }, ensure_ascii=False, indent=2)
        
        # Format text
        report_lines = []
        report_lines.append(f"📊 RAPORT ACTIVITATE BOT - Ultimele {hours} ore")
        report_lines.append("=" * 50)
        report_lines.append(f"📅 Perioada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"📈 Total activități: {stats['total_activities']}")
        report_lines.append(f"✅ Rata de succes: {stats['success_rate']:.1f}%")
        report_lines.append("")
        
        # Breakdown activități
        if stats['activity_breakdown']:
            report_lines.append("📋 ACTIVITĂȚI:")
            for activity, count in sorted(stats['activity_breakdown'].items()):
                icon = "✅" if "success" in activity else "❌" if "error" in activity else "📝"
                report_lines.append(f"  {icon} {activity}: {count}")
            report_lines.append("")
        
        # Platform breakdown
        if stats['platform_breakdown']:
            report_lines.append("🌐 PLATFORME:")
            for platform, data in sorted(stats['platform_breakdown'].items()):
                success_rate = (data['success'] / data['total'] * 100) if data['total'] > 0 else 0
                report_lines.append(f"  📱 {platform.upper()}: {data['total']} total, {success_rate:.1f}% succes")
            report_lines.append("")
        
        # Top erori
        if stats['top_errors']:
            report_lines.append("🚨 TOP ERORI:")
            for error, count in stats['top_errors']:
                report_lines.append(f"  ❌ {error}: {count} apariții")
            report_lines.append("")
        
        # Performance
        perf = stats['performance_metrics']
        if perf['avg_download_time'] > 0:
            report_lines.append("⚡ PERFORMANȚĂ:")
            report_lines.append(f"  📊 Timp mediu download: {perf['avg_download_time']:.1f}ms")
            report_lines.append(f"  🚀 Cel mai rapid: {perf['fastest_download']:.1f}ms")
            report_lines.append(f"  🐌 Cel mai lent: {perf['slowest_download']:.1f}ms")
            report_lines.append("")
        
        # Ultimele activități
        report_lines.append("📝 ULTIMELE ACTIVITĂȚI:")
        for log in logs[:20]:  # Ultimele 20
            report_lines.append(f"  {log.to_readable_string()}")
        
        if len(logs) > 20:
            report_lines.append(f"  ... și încă {len(logs) - 20} activități")
        
        return "\n".join(report_lines)
    
    def cleanup_old_logs(self, days: int = 7):
        """Curăță log-urile vechi"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        with self.lock:
            # Păstrează doar log-urile recente în memorie
            self.logs = deque(
                [log for log in self.logs if log.timestamp >= cutoff_time],
                maxlen=self.max_logs
            )
        
        logger.info(f"🧹 Cleaned up logs older than {days} days")
    
    # Metode de conveniență pentru logging-ul activităților comune
    def log_download_success(self, platform: str, url: str, duration_ms: float, user_id: int, chat_id: int):
        """Log pentru download reușit"""
        self.log_activity(
            ActivityType.DOWNLOAD_SUCCESS,
            f"Download reușit de pe {platform}",
            level=LogLevel.INFO,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            url=url,
            duration_ms=duration_ms,
            success=True
        )
    
    def log_download_error(self, platform: str, url: str, error: str, user_id: int, chat_id: int, error_code: str = None):
        """Log pentru eroare de download"""
        self.log_activity(
            ActivityType.DOWNLOAD_ERROR,
            f"Eroare download de pe {platform}: {error}",
            level=LogLevel.ERROR,
            user_id=user_id,
            chat_id=chat_id,
            platform=platform,
            url=url,
            success=False,
            error_code=error_code
        )
    
    def log_command_executed(self, command: str, user_id: int, chat_id: int, success: bool = True):
        """Log pentru comandă executată"""
        self.log_activity(
            ActivityType.COMMAND_EXECUTED,
            f"Comandă executată: {command}",
            level=LogLevel.INFO if success else LogLevel.ERROR,
            user_id=user_id,
            chat_id=chat_id,
            command=command,
            success=success
        )
    
    def log_platform_error(self, platform: str, error: str, details: Dict[str, Any] = None):
        """Log pentru eroare de platformă"""
        self.log_activity(
            ActivityType.PLATFORM_ERROR,
            f"Eroare platformă {platform}: {error}",
            level=LogLevel.ERROR,
            platform=platform,
            details=details,
            success=False
        )
    
    def log_system_error(self, component: str, error: str, details: Dict[str, Any] = None):
        """Log pentru eroare de sistem"""
        self.log_activity(
            ActivityType.SYSTEM_ERROR,
            f"Eroare sistem în {component}: {error}",
            level=LogLevel.CRITICAL,
            details=details,
            success=False
        )

# Singleton instance
activity_logger = ActivityLogger()

# Helper functions pentru logging rapid
def log_download_success(platform: str, url: str, duration_ms: float, user_id: int, chat_id: int):
    activity_logger.log_download_success(platform, url, duration_ms, user_id, chat_id)

def log_download_error(platform: str, url: str, error: str, user_id: int, chat_id: int, error_code: str = None):
    activity_logger.log_download_error(platform, url, error, user_id, chat_id, error_code)

def log_command_executed(command: str, user_id: int, chat_id: int, success: bool = True):
    activity_logger.log_command_executed(command, user_id, chat_id, success)

def log_platform_error(platform: str, error: str, details: Dict[str, Any] = None):
    activity_logger.log_platform_error(platform, error, details)

def log_system_error(component: str, error: str, details: Dict[str, Any] = None):
    activity_logger.log_system_error(component, error, details)