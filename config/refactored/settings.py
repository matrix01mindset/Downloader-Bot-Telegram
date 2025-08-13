# config/refactored/settings.py - Configurații pentru Arhitectura Refactorizată
# Versiunea: 4.0.0 - Configurare Centralizată

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    from platforms.base.abstract_platform import PlatformCapability, ContentType, QualityLevel
    from utils.validation.validator import ValidationLevel
    from utils.network.network_manager import RateLimitStrategy, ProxyType
except ImportError:
    # Fallback pentru development
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import PlatformCapability, ContentType, QualityLevel
    from utils.validation.validator import ValidationLevel
    from utils.network.network_manager import RateLimitStrategy, ProxyType

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Mediile de rulare"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(Enum):
    """Nivelurile de logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Configurația bazei de date"""
    url: str = "sqlite:///downloader.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'echo': self.echo
        }

@dataclass
class CacheConfig:
    """Configurația cache-ului"""
    enabled: bool = True
    backend: str = "memory"  # memory, redis, file
    ttl: int = 3600  # Time to live în secunde
    max_size: int = 1000  # Numărul maxim de intrări
    cleanup_interval: int = 300  # Interval de curățare în secunde
    
    # Redis specific
    redis_url: Optional[str] = None
    redis_db: int = 0
    
    # File cache specific
    cache_dir: str = "cache"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'backend': self.backend,
            'ttl': self.ttl,
            'max_size': self.max_size,
            'cleanup_interval': self.cleanup_interval,
            'redis_url': self.redis_url,
            'redis_db': self.redis_db,
            'cache_dir': self.cache_dir
        }

@dataclass
class NetworkConfig:
    """Configurația rețelei"""
    # Rate limiting
    rate_limit_strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    max_requests_per_minute: int = 60
    burst_limit: int = 10
    backoff_factor: float = 1.5
    max_backoff: int = 300
    
    # Connection pooling
    max_connections: int = 100
    max_connections_per_host: int = 30
    connection_timeout: int = 10
    read_timeout: int = 30
    
    # Retry logic
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # User agents
    rotate_user_agents: bool = True
    custom_user_agent: Optional[str] = None
    
    # Proxy
    use_proxies: bool = False
    proxy_rotation: bool = True
    
    # SSL
    verify_ssl: bool = True
    ssl_timeout: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rate_limit_strategy': self.rate_limit_strategy.value,
            'max_requests_per_minute': self.max_requests_per_minute,
            'burst_limit': self.burst_limit,
            'backoff_factor': self.backoff_factor,
            'max_backoff': self.max_backoff,
            'max_connections': self.max_connections,
            'max_connections_per_host': self.max_connections_per_host,
            'connection_timeout': self.connection_timeout,
            'read_timeout': self.read_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'rotate_user_agents': self.rotate_user_agents,
            'custom_user_agent': self.custom_user_agent,
            'use_proxies': self.use_proxies,
            'proxy_rotation': self.proxy_rotation,
            'verify_ssl': self.verify_ssl,
            'ssl_timeout': self.ssl_timeout
        }

@dataclass
class DownloadConfig:
    """Configurația descărcărilor"""
    # Directoare
    base_download_dir: str = "downloads"
    temp_dir: str = "temp"
    
    # Concurrency
    max_concurrent_downloads: int = 5
    max_concurrent_per_platform: int = 2
    
    # Fișiere
    chunk_size: int = 8192  # 8KB
    max_file_size: int = 5 * 1024 * 1024 * 1024  # 5GB
    
    # Retry și timeout
    download_timeout: int = 300  # 5 minute
    max_download_retries: int = 3
    retry_delay: float = 2.0
    
    # Cleanup
    cleanup_temp_files: bool = True
    cleanup_interval: int = 3600  # 1 oră
    max_temp_age: int = 86400  # 24 ore
    
    # Progress tracking
    progress_update_interval: float = 1.0  # secunde
    
    # Quality și format
    default_quality: QualityLevel = QualityLevel.HIGH
    default_content_type: ContentType = ContentType.VIDEO
    
    # Validare
    validate_downloads: bool = True
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'base_download_dir': self.base_download_dir,
            'temp_dir': self.temp_dir,
            'max_concurrent_downloads': self.max_concurrent_downloads,
            'max_concurrent_per_platform': self.max_concurrent_per_platform,
            'chunk_size': self.chunk_size,
            'max_file_size': self.max_file_size,
            'download_timeout': self.download_timeout,
            'max_download_retries': self.max_download_retries,
            'retry_delay': self.retry_delay,
            'cleanup_temp_files': self.cleanup_temp_files,
            'cleanup_interval': self.cleanup_interval,
            'max_temp_age': self.max_temp_age,
            'progress_update_interval': self.progress_update_interval,
            'default_quality': self.default_quality.value,
            'default_content_type': self.default_content_type.value,
            'validate_downloads': self.validate_downloads,
            'validation_level': self.validation_level.value
        }

@dataclass
class PlatformConfig:
    """Configurația platformelor"""
    # Auto-discovery
    auto_discover: bool = True
    discovery_paths: List[str] = field(default_factory=lambda: ["platforms/implementations"])
    
    # Load balancing
    enable_load_balancing: bool = True
    load_balancing_strategy: str = "round_robin"  # round_robin, least_used, health_based
    
    # Health monitoring
    health_check_interval: int = 300  # 5 minute
    health_check_timeout: int = 10
    max_consecutive_failures: int = 3
    
    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    
    # Cache
    cache_platform_metadata: bool = True
    metadata_cache_ttl: int = 1800  # 30 minute
    
    # Compatibility
    enable_legacy_support: bool = True
    strict_capability_checking: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'auto_discover': self.auto_discover,
            'discovery_paths': self.discovery_paths,
            'enable_load_balancing': self.enable_load_balancing,
            'load_balancing_strategy': self.load_balancing_strategy,
            'health_check_interval': self.health_check_interval,
            'health_check_timeout': self.health_check_timeout,
            'max_consecutive_failures': self.max_consecutive_failures,
            'circuit_breaker_enabled': self.circuit_breaker_enabled,
            'circuit_breaker_failure_threshold': self.circuit_breaker_failure_threshold,
            'circuit_breaker_recovery_timeout': self.circuit_breaker_recovery_timeout,
            'cache_platform_metadata': self.cache_platform_metadata,
            'metadata_cache_ttl': self.metadata_cache_ttl,
            'enable_legacy_support': self.enable_legacy_support,
            'strict_capability_checking': self.strict_capability_checking
        }

@dataclass
class MonitoringConfig:
    """Configurația monitorizării"""
    # Health monitoring
    enabled: bool = True
    check_interval: int = 60  # secunde
    
    # Metrics
    collect_metrics: bool = True
    metrics_retention: int = 86400  # 24 ore
    
    # Alerts
    enable_alerts: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'error_rate': 0.1,  # 10%
        'response_time': 5.0,  # 5 secunde
        'memory_usage': 0.8,  # 80%
        'disk_usage': 0.9  # 90%
    })
    
    # Logging
    log_performance: bool = True
    log_errors: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'check_interval': self.check_interval,
            'collect_metrics': self.collect_metrics,
            'metrics_retention': self.metrics_retention,
            'enable_alerts': self.enable_alerts,
            'alert_thresholds': self.alert_thresholds,
            'log_performance': self.log_performance,
            'log_errors': self.log_errors
        }

@dataclass
class SecurityConfig:
    """Configurația securității"""
    # Validation
    strict_validation: bool = True
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    
    # File security
    scan_downloads: bool = True
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a',
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'
    ])
    blocked_extensions: List[str] = field(default_factory=lambda: [
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.msi', '.dll'
    ])
    
    # Network security
    verify_ssl_certificates: bool = True
    allow_insecure_connections: bool = False
    
    # Rate limiting pentru securitate
    enable_security_rate_limiting: bool = True
    max_requests_per_ip: int = 100
    security_rate_window: int = 3600  # 1 oră
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strict_validation': self.strict_validation,
            'validation_level': self.validation_level.value,
            'scan_downloads': self.scan_downloads,
            'allowed_extensions': self.allowed_extensions,
            'blocked_extensions': self.blocked_extensions,
            'verify_ssl_certificates': self.verify_ssl_certificates,
            'allow_insecure_connections': self.allow_insecure_connections,
            'enable_security_rate_limiting': self.enable_security_rate_limiting,
            'max_requests_per_ip': self.max_requests_per_ip,
            'security_rate_window': self.security_rate_window
        }

@dataclass
class LoggingConfig:
    """Configurația logging-ului"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File logging
    log_to_file: bool = True
    log_file: str = "logs/downloader.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # Console logging
    log_to_console: bool = True
    console_level: LogLevel = LogLevel.INFO
    
    # Structured logging
    structured_logging: bool = False
    json_format: bool = False
    
    # Logger specific levels
    logger_levels: Dict[str, str] = field(default_factory=lambda: {
        'urllib3': 'WARNING',
        'aiohttp': 'WARNING',
        'asyncio': 'WARNING'
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level.value,
            'format': self.format,
            'log_to_file': self.log_to_file,
            'log_file': self.log_file,
            'max_file_size': self.max_file_size,
            'backup_count': self.backup_count,
            'log_to_console': self.log_to_console,
            'console_level': self.console_level.value,
            'structured_logging': self.structured_logging,
            'json_format': self.json_format,
            'logger_levels': self.logger_levels
        }

@dataclass
class PerformanceConfig:
    """Configurația performanței"""
    # Memory management
    max_memory_usage: int = 1024 * 1024 * 1024  # 1GB
    memory_check_interval: int = 60  # secunde
    
    # CPU management
    max_cpu_usage: float = 80.0  # 80%
    cpu_check_interval: int = 30  # secunde
    
    # Disk management
    max_disk_usage: float = 90.0  # 90%
    disk_check_interval: int = 300  # 5 minute
    
    # Optimization
    enable_compression: bool = True
    compression_level: int = 6  # 1-9
    
    # Garbage collection
    gc_threshold: int = 1000
    gc_interval: int = 300  # 5 minute
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_memory_usage': self.max_memory_usage,
            'memory_check_interval': self.memory_check_interval,
            'max_cpu_usage': self.max_cpu_usage,
            'cpu_check_interval': self.cpu_check_interval,
            'max_disk_usage': self.max_disk_usage,
            'disk_check_interval': self.disk_check_interval,
            'enable_compression': self.enable_compression,
            'compression_level': self.compression_level,
            'gc_threshold': self.gc_threshold,
            'gc_interval': self.gc_interval
        }

@dataclass
class Settings:
    """
    Configurația principală a aplicației.
    Combină toate configurațiile specifice într-o singură clasă.
    """
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    
    # Componente
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Metadata
    version: str = "4.0.0"
    name: str = "Downloader Bot Refactored"
    description: str = "Arhitectură refactorizată pentru compatibilitate optimizată"
    
    def __post_init__(self):
        """Post-procesare după inițializare"""
        # Ajustează configurațiile pe baza mediului
        if self.environment == Environment.PRODUCTION:
            self.debug = False
            self.logging.level = LogLevel.WARNING
            self.security.strict_validation = True
            self.security.validation_level = ValidationLevel.STRICT
        elif self.environment == Environment.DEVELOPMENT:
            self.debug = True
            self.logging.level = LogLevel.DEBUG
            self.logging.console_level = LogLevel.DEBUG
        
        # Creează directoarele necesare
        self._create_directories()
    
    def _create_directories(self):
        """Creează directoarele necesare"""
        directories = [
            self.download.base_download_dir,
            self.download.temp_dir,
            self.cache.cache_dir,
            os.path.dirname(self.logging.log_file)
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertește configurația în dicționar"""
        return {
            'environment': self.environment.value,
            'debug': self.debug,
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'database': self.database.to_dict(),
            'cache': self.cache.to_dict(),
            'network': self.network.to_dict(),
            'download': self.download.to_dict(),
            'platform': self.platform.to_dict(),
            'monitoring': self.monitoring.to_dict(),
            'security': self.security.to_dict(),
            'logging': self.logging.to_dict(),
            'performance': self.performance.to_dict()
        }
    
    def save_to_file(self, file_path: str):
        """Salvează configurația într-un fișier JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Settings saved to: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save settings: {e}")
            raise
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Settings':
        """Încarcă configurația dintr-un fișier JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Creează instanța cu datele încărcate
            settings = cls()
            settings._update_from_dict(data)
            
            logger.info(f"📂 Settings loaded from: {file_path}")
            return settings
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Settings file not found: {file_path}, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"❌ Failed to load settings: {e}")
            raise
    
    def _update_from_dict(self, data: Dict[str, Any]):
        """Actualizează configurația din dicționar"""
        # Actualizează câmpurile simple
        if 'environment' in data:
            self.environment = Environment(data['environment'])
        if 'debug' in data:
            self.debug = data['debug']
        if 'version' in data:
            self.version = data['version']
        if 'name' in data:
            self.name = data['name']
        if 'description' in data:
            self.description = data['description']
        
        # Actualizează configurațiile componente
        if 'database' in data:
            self._update_database_config(data['database'])
        if 'cache' in data:
            self._update_cache_config(data['cache'])
        if 'network' in data:
            self._update_network_config(data['network'])
        if 'download' in data:
            self._update_download_config(data['download'])
        if 'platform' in data:
            self._update_platform_config(data['platform'])
        if 'monitoring' in data:
            self._update_monitoring_config(data['monitoring'])
        if 'security' in data:
            self._update_security_config(data['security'])
        if 'logging' in data:
            self._update_logging_config(data['logging'])
        if 'performance' in data:
            self._update_performance_config(data['performance'])
    
    def _update_database_config(self, data: Dict[str, Any]):
        """Actualizează configurația bazei de date"""
        for key, value in data.items():
            if hasattr(self.database, key):
                setattr(self.database, key, value)
    
    def _update_cache_config(self, data: Dict[str, Any]):
        """Actualizează configurația cache-ului"""
        for key, value in data.items():
            if hasattr(self.cache, key):
                setattr(self.cache, key, value)
    
    def _update_network_config(self, data: Dict[str, Any]):
        """Actualizează configurația rețelei"""
        for key, value in data.items():
            if key == 'rate_limit_strategy':
                self.network.rate_limit_strategy = RateLimitStrategy(value)
            elif hasattr(self.network, key):
                setattr(self.network, key, value)
    
    def _update_download_config(self, data: Dict[str, Any]):
        """Actualizează configurația descărcărilor"""
        for key, value in data.items():
            if key == 'default_quality':
                self.download.default_quality = QualityLevel(value)
            elif key == 'default_content_type':
                self.download.default_content_type = ContentType(value)
            elif key == 'validation_level':
                self.download.validation_level = ValidationLevel(value)
            elif hasattr(self.download, key):
                setattr(self.download, key, value)
    
    def _update_platform_config(self, data: Dict[str, Any]):
        """Actualizează configurația platformelor"""
        for key, value in data.items():
            if hasattr(self.platform, key):
                setattr(self.platform, key, value)
    
    def _update_monitoring_config(self, data: Dict[str, Any]):
        """Actualizează configurația monitorizării"""
        for key, value in data.items():
            if hasattr(self.monitoring, key):
                setattr(self.monitoring, key, value)
    
    def _update_security_config(self, data: Dict[str, Any]):
        """Actualizează configurația securității"""
        for key, value in data.items():
            if key == 'validation_level':
                self.security.validation_level = ValidationLevel(value)
            elif hasattr(self.security, key):
                setattr(self.security, key, value)
    
    def _update_logging_config(self, data: Dict[str, Any]):
        """Actualizează configurația logging-ului"""
        for key, value in data.items():
            if key == 'level':
                self.logging.level = LogLevel(value)
            elif key == 'console_level':
                self.logging.console_level = LogLevel(value)
            elif hasattr(self.logging, key):
                setattr(self.logging, key, value)
    
    def _update_performance_config(self, data: Dict[str, Any]):
        """Actualizează configurația performanței"""
        for key, value in data.items():
            if hasattr(self.performance, key):
                setattr(self.performance, key, value)
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Obține configurația specifică mediului"""
        base_config = self.to_dict()
        
        # Configurații specifice mediului
        env_configs = {
            Environment.DEVELOPMENT: {
                'debug': True,
                'logging': {'level': 'DEBUG', 'console_level': 'DEBUG'},
                'security': {'strict_validation': False},
                'monitoring': {'check_interval': 30}
            },
            Environment.TESTING: {
                'debug': True,
                'database': {'url': 'sqlite:///:memory:'},
                'cache': {'backend': 'memory'},
                'logging': {'level': 'INFO'}
            },
            Environment.STAGING: {
                'debug': False,
                'logging': {'level': 'INFO'},
                'security': {'strict_validation': True},
                'monitoring': {'check_interval': 60}
            },
            Environment.PRODUCTION: {
                'debug': False,
                'logging': {'level': 'WARNING', 'console_level': 'ERROR'},
                'security': {'strict_validation': True, 'validation_level': 'strict'},
                'monitoring': {'check_interval': 60, 'enable_alerts': True},
                'performance': {'max_memory_usage': 2147483648}  # 2GB
            }
        }
        
        env_config = env_configs.get(self.environment, {})
        
        # Merge configurațiile
        def deep_merge(base: Dict, override: Dict) -> Dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(base_config, env_config)
    
    def validate(self) -> List[str]:
        """Validează configurația și returnează o listă de probleme"""
        issues = []
        
        # Validează directoarele
        if not self.download.base_download_dir:
            issues.append("Download directory cannot be empty")
        
        if not self.download.temp_dir:
            issues.append("Temp directory cannot be empty")
        
        # Validează limitele
        if self.download.max_concurrent_downloads <= 0:
            issues.append("Max concurrent downloads must be positive")
        
        if self.network.max_connections <= 0:
            issues.append("Max connections must be positive")
        
        if self.download.chunk_size <= 0:
            issues.append("Chunk size must be positive")
        
        # Validează timeout-urile
        if self.network.connection_timeout <= 0:
            issues.append("Connection timeout must be positive")
        
        if self.download.download_timeout <= 0:
            issues.append("Download timeout must be positive")
        
        # Validează rate limiting
        if self.network.max_requests_per_minute <= 0:
            issues.append("Max requests per minute must be positive")
        
        # Validează cache
        if self.cache.enabled and self.cache.ttl <= 0:
            issues.append("Cache TTL must be positive when cache is enabled")
        
        return issues
    
    def __str__(self) -> str:
        return f"Settings(env={self.environment.value}, debug={self.debug}, version={self.version})"
    
    def __repr__(self) -> str:
        return (f"Settings(environment={self.environment.value}, "
                f"debug={self.debug}, version='{self.version}')")


# Funcții utilitare pentru încărcarea configurației
def load_settings(config_file: Optional[str] = None, 
                 environment: Optional[Environment] = None) -> Settings:
    """
    Încarcă configurația din fișier sau variabile de mediu.
    
    Args:
        config_file: Calea către fișierul de configurație
        environment: Mediul de rulare (override)
    
    Returns:
        Instanța Settings configurată
    """
    # Determină fișierul de configurație
    if not config_file:
        config_file = os.getenv('DOWNLOADER_CONFIG', 'config/settings.json')
    
    # Încarcă configurația
    if os.path.exists(config_file):
        settings = Settings.load_from_file(config_file)
    else:
        settings = Settings()
    
    # Override environment dacă este specificat
    if environment:
        settings.environment = environment
    elif os.getenv('DOWNLOADER_ENV'):
        settings.environment = Environment(os.getenv('DOWNLOADER_ENV'))
    
    # Override cu variabile de mediu
    _apply_environment_overrides(settings)
    
    # Validează configurația
    issues = settings.validate()
    if issues:
        logger.warning(f"⚠️ Configuration issues found: {', '.join(issues)}")
    
    logger.info(f"⚙️ Settings loaded for environment: {settings.environment.value}")
    return settings

def _apply_environment_overrides(settings: Settings):
    """Aplică override-uri din variabilele de mediu"""
    env_mappings = {
        'DOWNLOADER_DEBUG': ('debug', lambda x: x.lower() == 'true'),
        'DOWNLOADER_LOG_LEVEL': ('logging.level', lambda x: LogLevel(x.upper())),
        'DOWNLOADER_MAX_DOWNLOADS': ('download.max_concurrent_downloads', int),
        'DOWNLOADER_DOWNLOAD_DIR': ('download.base_download_dir', str),
        'DOWNLOADER_TEMP_DIR': ('download.temp_dir', str),
        'DOWNLOADER_MAX_RETRIES': ('network.max_retries', int),
        'DOWNLOADER_TIMEOUT': ('download.download_timeout', int),
        'DOWNLOADER_CACHE_ENABLED': ('cache.enabled', lambda x: x.lower() == 'true'),
        'DOWNLOADER_CACHE_TTL': ('cache.ttl', int),
        'DOWNLOADER_REDIS_URL': ('cache.redis_url', str),
        'DOWNLOADER_DATABASE_URL': ('database.url', str),
    }
    
    for env_var, (config_path, converter) in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            try:
                converted_value = converter(value)
                _set_nested_attr(settings, config_path, converted_value)
                logger.debug(f"🔧 Applied environment override: {env_var} = {converted_value}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to apply environment override {env_var}: {e}")

def _set_nested_attr(obj: Any, path: str, value: Any):
    """Setează un atribut nested folosind dot notation"""
    parts = path.split('.')
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)

# Instanța globală de configurație
settings = load_settings()