import time
import json
import hashlib
import logging
import threading
import asyncio
import os
import pickle
import tempfile
import weakref
from typing import Dict, Any, Optional, Union, List, Callable, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from collections import OrderedDict, defaultdict

try:
    from utils.config import config
    from utils.memory_manager import memory_manager, MemoryPriority
    from utils.monitoring import monitoring
except ImportError:
    config = None
    memory_manager = None
    monitoring = None

import sys

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheStrategy(Enum):
    """Strategii de cache disponibile"""
    LRU = "lru"              # Least Recently Used
    LFU = "lfu"              # Least Frequently Used  
    TTL = "ttl"              # Time To Live
    FIFO = "fifo"            # First In First Out
    SMART = "smart"          # Strategie inteligentă combinată

class CacheTier(Enum):
    """Niveluri de cache"""
    MEMORY = "memory"        # Cache în memorie (rapid)
    DISK = "disk"           # Cache pe disk (persistent)
    HYBRID = "hybrid"       # Combinație memory + disk

@dataclass
class CacheEntry:
    """Intrare în cache cu metadata completă"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float]
    size_bytes: int
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_expired(self) -> bool:
        """Verifică dacă intrarea a expirat"""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl
    
    @property
    def age_seconds(self) -> float:
        """Vârsta intrării în secunde"""
        return time.time() - self.created_at

class LRUCache(Generic[T]):
    """Cache LRU optimizat cu TTL și statistici"""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_removals': 0
        }
    
    def get(self, key: str) -> Optional[T]:
        """Obține valoare din cache"""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Verifică expirarea
            if entry.is_expired:
                del self.cache[key]
                self.stats['expired_removals'] += 1
                self.stats['misses'] += 1
                return None
            
            # Actualizează statistici de acces
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # Mută la sfârșitul listei (most recently used)
            self.cache.move_to_end(key)
            
            self.stats['hits'] += 1
            return entry.value
    
    def put(self, key: str, value: T, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Adaugă valoare în cache"""
        with self.lock:
            current_time = time.time()
            effective_ttl = ttl if ttl is not None else self.default_ttl
            
            # Calculează dimensiunea aproximativă
            try:
                size_bytes = sys.getsizeof(value) + sys.getsizeof(key)
            except:
                size_bytes = 1024  # Estimare default
            
            # Creează intrarea
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                ttl=effective_ttl,
                size_bytes=size_bytes,
                metadata=metadata or {}
            )
            
            # Dacă cheia există deja, actualizează
            if key in self.cache:
                self.cache[key] = entry
                self.cache.move_to_end(key)
                return True
            
            # Verifică dacă trebuie să elimine intrări
            while len(self.cache) >= self.max_size:
                oldest_key, _ = self.cache.popitem(last=False)
                self.stats['evictions'] += 1
                logger.debug(f"🗑️ Evicted cache entry: {oldest_key}")
            
            # Adaugă noua intrare
            self.cache[key] = entry
            return True
    
    def remove(self, key: str) -> bool:
        """Elimină o cheie din cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Curăță întregul cache"""
        with self.lock:
            self.cache.clear()
            self.stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expired_removals': 0
            }
    
    def cleanup_expired(self) -> int:
        """Curăță intrările expirate"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                self.stats['expired_removals'] += 1
            
            if expired_keys:
                logger.debug(f"🧹 Removed {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obține statistici cache"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'entries': len(self.cache),
                'max_size': self.max_size,
                'hit_rate_percent': round(hit_rate, 2),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions'],
                'expired_removals': self.stats['expired_removals']
            }

class DiskCache:
    """Cache persistent pe disk cu compresie și indexare"""
    
    def __init__(self, cache_dir: Optional[str] = None, max_size_mb: int = 50):
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "telegram_bot_cache")
        
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.index_file = os.path.join(cache_dir, "cache_index.json")
        
        # Creează directorul dacă nu există
        os.makedirs(cache_dir, exist_ok=True)
        
        # Încarcă indexul
        self.index = self._load_index()
        self.lock = threading.RLock()
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Încarcă indexul cache-ului de pe disk"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Could not load cache index: {e}")
        return {}
    
    def _save_index(self):
        """Salvează indexul pe disk"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Could not save cache index: {e}")
    
    def _get_cache_file_path(self, key: str) -> str:
        """Generează calea fișierului pentru o cheie"""
        safe_key = hashlib.sha256(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Obține valoare din cache-ul de pe disk"""
        with self.lock:
            if key not in self.index:
                return None
            
            entry_info = self.index[key]
            
            # Verifică expirarea
            if entry_info.get('ttl') and time.time() - entry_info['created_at'] > entry_info['ttl']:
                self.remove(key)
                return None
            
            # Încarcă valoarea de pe disk
            cache_file = self._get_cache_file_path(key)
            try:
                if os.path.exists(cache_file):
                    with open(cache_file, 'rb') as f:
                        value = pickle.load(f)
                    
                    # Actualizează statistici
                    entry_info['last_accessed'] = time.time()
                    entry_info['access_count'] = entry_info.get('access_count', 0) + 1
                    self._save_index()
                    
                    return value
                else:
                    # Fișierul nu există, elimină din index
                    del self.index[key]
                    self._save_index()
                    return None
            except Exception as e:
                logger.error(f"❌ Error loading from disk cache: {e}")
                self.remove(key)
                return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Salvează valoare în cache-ul de pe disk"""
        with self.lock:
            try:
                cache_file = self._get_cache_file_path(key)
                
                # Salvează valoarea
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
                
                # Calculează dimensiunea
                file_size = os.path.getsize(cache_file)
                
                # Actualizează indexul
                current_time = time.time()
                self.index[key] = {
                    'created_at': current_time,
                    'last_accessed': current_time,
                    'access_count': 1,
                    'ttl': ttl,
                    'size_bytes': file_size,
                    'metadata': metadata or {},
                    'file_path': cache_file
                }
                
                # Verifică dimensiunea totală și curăță dacă e necesar
                total_size = self._get_total_size()
                if total_size > self.max_size_bytes:
                    self._cleanup_lru(total_size - self.max_size_bytes)
                
                self._save_index()
                return True
                
            except Exception as e:
                logger.error(f"❌ Error saving to disk cache: {e}")
                return False
    
    def remove(self, key: str) -> bool:
        """Elimină o intrare din cache"""
        with self.lock:
            if key not in self.index:
                return False
            
            try:
                # Șterge fișierul
                cache_file = self._get_cache_file_path(key)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                
                # Elimină din index
                del self.index[key]
                self._save_index()
                return True
                
            except Exception as e:
                logger.error(f"❌ Error removing from disk cache: {e}")
                return False
    
    def _get_total_size(self) -> int:
        """Calculează dimensiunea totală a cache-ului"""
        return sum(entry.get('size_bytes', 0) for entry in self.index.values())
    
    def _cleanup_lru(self, needed_space: int):
        """Curăță intrările mai puțin folosite recent"""
        # Sortează după last_accessed
        entries = list(self.index.items())
        entries.sort(key=lambda x: x[1].get('last_accessed', 0))
        
        freed_space = 0
        for key, entry_info in entries:
            if freed_space >= needed_space:
                break
            
            freed_space += entry_info.get('size_bytes', 0)
            self.remove(key)
            logger.debug(f"🗑️ Removed LRU disk cache entry: {key}")
    
    def cleanup_expired(self) -> int:
        """Curăță intrările expirate"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry_info in self.index.items():
                ttl = entry_info.get('ttl')
                if ttl and (current_time - entry_info['created_at']) > ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.remove(key)
            
            if expired_keys:
                logger.debug(f"🧹 Removed {len(expired_keys)} expired disk entries")
            
            return len(expired_keys)
    
    def clear(self):
        """Curăță întregul cache de pe disk"""
        with self.lock:
            for key in list(self.index.keys()):
                self.remove(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obține statistici cache disk"""
        with self.lock:
            total_size = self._get_total_size()
            
            return {
                'entries': len(self.index),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
                'usage_percent': round((total_size / self.max_size_bytes) * 100, 2) if self.max_size_bytes > 0 else 0
            }

class SmartCache(Generic[T]):
    """Cache inteligent cu strategie adaptivă și management automat"""
    
    def __init__(self, 
                 memory_cache_size: int = 500,
                 disk_cache_size_mb: int = 50,
                 default_ttl: Optional[float] = 3600,  # 1 oră
                 strategy: CacheStrategy = CacheStrategy.SMART):
        
        self.strategy = strategy
        self.default_ttl = default_ttl
        self.memory_cache = LRUCache[T](max_size=memory_cache_size, ttl=default_ttl)
        self.disk_cache = DiskCache(max_size_mb=disk_cache_size_mb)
        
        # Statistici globale
        self.stats = {
            'total_requests': 0,
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0
        }
        
        # Background cleanup
        self.cleanup_thread: Optional[threading.Thread] = None
        self.should_stop = False
        self.cleanup_interval = 300  # 5 minute
        
        # Configurare avansată
        if config:
            self._start_cleanup_thread()
            logger.info("🧠 Smart Cache initialized with advanced features")
    
    def get(self, key: str) -> Optional[T]:
        """Obține valoare din cache cu strategie inteligentă"""
        self.stats['total_requests'] += 1
        
        # Încearcă memoria mai întâi
        value = self.memory_cache.get(key)
        if value is not None:
            self.stats['memory_hits'] += 1
            return value
        
        # Încearcă disk-ul
        value = self.disk_cache.get(key)
        if value is not None:
            self.stats['disk_hits'] += 1
            # Promovează în memorie pentru acces rapid viitor
            self._promote_to_memory(key, value)
            return value
        
        self.stats['misses'] += 1
        return None
    
    def put(self, key: str, 
            value: T, 
            ttl: Optional[float] = None,
            priority: str = "normal",
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Adaugă valoare în cache cu strategie optimizată"""
        
        effective_ttl = ttl if ttl is not None else self.default_ttl
        cache_metadata = metadata or {}
        cache_metadata['priority'] = priority
        
        # Calculează dimensiunea aproximativă
        try:
            value_size = sys.getsizeof(value)
        except:
            value_size = 1024
        
        # Strategie de plasare
        if self.strategy == CacheStrategy.SMART:
            return self._smart_put(key, value, effective_ttl, value_size, cache_metadata)
        elif self.strategy == CacheStrategy.LRU:
            return self.memory_cache.put(key, value, effective_ttl, cache_metadata)
        else:
            # Pentru alte strategii, folosește memoria
            success = self.memory_cache.put(key, value, effective_ttl, cache_metadata)
            if memory_manager:
                memory_manager.track_allocation(value_size, MemoryPriority.NORMAL)
            return success
    
    def _smart_put(self, key: str, value: T, ttl: float, value_size: int, metadata: Dict[str, Any]) -> bool:
        """Strategie inteligentă de plasare în cache"""
        # Obiecte mici și frecvent accesate -> memorie
        if value_size < 10240:  # < 10KB
            return self.memory_cache.put(key, value, ttl, metadata)
        else:
            # Obiecte mari -> disk
            return self.disk_cache.put(key, value, ttl, metadata)
    
    def _promote_to_memory(self, key: str, value: T):
        """Promovează o valoare din disk în memorie"""
        if len(self.memory_cache.cache) < self.memory_cache.max_size:
            try:
                self.memory_cache.put(key, value)
            except Exception as e:
                logger.debug(f"Could not promote to memory: {e}")
    
    def remove(self, key: str) -> bool:
        """Elimină din ambele cache-uri"""
        memory_removed = self.memory_cache.remove(key)
        disk_removed = self.disk_cache.remove(key)
        
        if memory_manager and (memory_removed or disk_removed):
            memory_manager.release_allocation(1024)  # Estimare
        
        return memory_removed or disk_removed
    
    def clear(self):
        """Curăță ambele cache-uri"""
        self.memory_cache.clear()
        self.disk_cache.clear()
        self.stats = {
            'total_requests': 0,
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0
        }
    
    def _start_cleanup_thread(self):
        """Pornește thread-ul de curățare automată"""
        if self.cleanup_thread is None:
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="CacheCleanup"
            )
            self.cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Loop de curățare automată"""
        while not self.should_stop:
            try:
                # Curăță intrările expirate
                self.memory_cache.cleanup_expired()
                self.disk_cache.cleanup_expired()
                
                logger.debug("🧹 Cache cleanup completed")
                
                # Verifică memoria dacă e disponibil memory_manager
                if memory_manager:
                    memory_status = asyncio.run(memory_manager.get_memory_status())
                    if memory_status.get('usage_percent', 0) > 85:
                        self._aggressive_cleanup()
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"❌ Cache cleanup error: {e}")
                time.sleep(60)  # Retry după 1 minut
    
    def _aggressive_cleanup(self):
        """Curățare agresivă când memoria e plină"""
        logger.warning("⚡ Starting aggressive cache cleanup")
        
        # Reduce temporar dimensiunea cache-ului de memorie
        original_size = self.memory_cache.max_size
        self.memory_cache.max_size = max(50, original_size // 2)
        
        # Elimină intrările mai puțin folosite
        with self.memory_cache.lock:
            # Sortează după access_count și elimină jumătate
            entries = list(self.memory_cache.cache.items())
            entries.sort(key=lambda x: x[1].access_count)
            
            to_remove = entries[:len(entries)//2]
            for key, _ in to_remove:
                self.memory_cache.cache.pop(key, None)
                
        logger.warning(f"⚡ Aggressive cache cleanup: reduced from {original_size} to {self.memory_cache.max_size}")
        
        # Restaurează dimensiunea după 5 minute
        def restore_size():
            time.sleep(300)
            self.memory_cache.max_size = original_size
            
        threading.Thread(target=restore_size, daemon=True).start()
        
    async def get_stats(self) -> Dict[str, Any]:
        """Obține statistici complete ale cache-ului"""
        
        memory_stats = self.memory_cache.get_stats()
        disk_stats = self.disk_cache.get_stats()
        
        total_requests = self.stats['total_requests']
        overall_hit_rate = 0
        
        if total_requests > 0:
            total_hits = self.stats['memory_hits'] + self.stats['disk_hits']
            overall_hit_rate = (total_hits / total_requests) * 100
            
        return {
            "strategy": self.strategy.value,
            "overall": {
                "hit_rate_percent": round(overall_hit_rate, 2),
                "total_requests": total_requests,
                "memory_hits": self.stats['memory_hits'],
                "disk_hits": self.stats['disk_hits'],
                "misses": self.stats['misses'],
                "memory_hit_rate": round((self.stats['memory_hits'] / total_requests * 100) if total_requests > 0 else 0, 2),
                "disk_hit_rate": round((self.stats['disk_hits'] / total_requests * 100) if total_requests > 0 else 0, 2)
            },
            "memory_cache": memory_stats,
            "disk_cache": disk_stats,
            "health": {
                "cleanup_thread_alive": self.cleanup_thread.is_alive() if self.cleanup_thread else False,
                "total_entries": memory_stats.get('entries', 0) + disk_stats.get('entries', 0)
            }
        }
        
    def stop(self):
        """Oprește cache-ul și cleanup thread"""
        self.should_stop = True
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
            
        logger.info("🧠 Smart Cache stopped")

# Helper functions pentru cache keys
def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generează o cheie de cache consistentă"""
    
    # Combină argumentele într-un string
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    
    # Adaugă kwargs sortate
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
        
    key_string = "|".join(key_parts)
    
    # Hash pentru lungime consistentă
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:32]

# Cache decorator
def cached(ttl: Optional[float] = None, 
          key_prefix: str = "default",
          priority: str = "normal"):
    """
    Decorator pentru cache automat
    
    Usage:
        @cached(ttl=3600, key_prefix="video_metadata")
        def get_video_info(url):
            # expensive operation
            return video_info
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Generează cheia cache
                cache_key = generate_cache_key(f"{key_prefix}_{func.__name__}", *args, **kwargs)
                
                # Încearcă să obții din cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                    
                # Execută funcția
                result = await func(*args, **kwargs)
                
                # Salvează în cache
                if result is not None:
                    cache.put(cache_key, result, ttl=ttl, priority=priority)
                    
                return result
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # Generează cheia cache
                cache_key = generate_cache_key(f"{key_prefix}_{func.__name__}", *args, **kwargs)
                
                # Încearcă să obții din cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                    
                # Execută funcția
                result = func(*args, **kwargs)
                
                # Salvează în cache
                if result is not None:
                    cache.put(cache_key, result, ttl=ttl, priority=priority)
                    
                return result
            return sync_wrapper
    return decorator

# Singleton instance
cache = SmartCache[Any](
    memory_cache_size=500,
    disk_cache_size_mb=50,
    default_ttl=3600,  # 1 oră
    strategy=CacheStrategy.SMART
)
