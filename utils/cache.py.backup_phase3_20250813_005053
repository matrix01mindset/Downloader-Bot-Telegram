# utils/cache.py - Sistema de Cache inteligent pentru Free Tier
# Versiunea: 2.0.0 - Arhitectura Modulară

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
    """Intrarea din cache"""
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
        return time.time() - self.created_at > self.ttl
        
    @property
    def age_seconds(self) -> float:
        """Vârsta intrării în secunde"""
        return time.time() - self.created_at

class LRUCache(Generic[T]):
    """Cache LRU optimizat pentru memorie"""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        
    def get(self, key: str) -> Optional[T]:
        """Obține o valoare din cache"""
        with self.lock:
            if key not in self.cache:
                self._misses += 1
                if monitoring:
                    monitoring.record_cache_event("get", hit=False)
                return None
                
            entry = self.cache[key]
            
            # Verifică expirarea
            if entry.is_expired:
                del self.cache[key]
                self._misses += 1
                if monitoring:
                    monitoring.record_cache_event("get", hit=False)
                return None
                
            # Actualizează statisticile
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # Mută la sfârșitul OrderedDict (cel mai recent folosit)
            self.cache.move_to_end(key)
            
            self._hits += 1
            if monitoring:
                monitoring.record_cache_event("get", hit=True)
                
            return entry.value
            
    def put(self, key: str, value: T, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Pune o valoare în cache"""
        with self.lock:
            current_time = time.time()
            
            # Calculează dimensiunea aproximativă
            try:
                size_bytes = len(str(value).encode('utf-8'))
            except:
                size_bytes = 1024  # Estimare default
                
            # Folosește TTL-ul specificat sau cel default
            effective_ttl = ttl or self.ttl
            
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
            
            # Dacă cheia există deja, o actualizează
            if key in self.cache:
                self.cache[key] = entry
                self.cache.move_to_end(key)
                return True
                
            # Verifică dacă avem loc
            if len(self.cache) >= self.max_size:
                # Elimină intrarea cea mai puțin recent folosită
                oldest_key = next(iter(self.cache))
                removed_entry = self.cache.pop(oldest_key)
                logger.debug(f"🧹 Evicted LRU cache entry: {oldest_key}")
                
            # Adaugă noua intrare
            self.cache[key] = entry
            
            if monitoring:
                monitoring.record_cache_event("put")
                
            return True
            
    def remove(self, key: str) -> bool:
        """Elimină o intrare din cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if monitoring:
                    monitoring.record_cache_event("remove")
                return True
            return False
            
    def clear(self):
        """Curăță tot cache-ul"""
        with self.lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            
    def cleanup_expired(self) -> int:
        """Curăță intrarile expirate"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                del self.cache[key]
                
            if expired_keys and monitoring:
                monitoring.record_cache_event("cleanup_expired")
                
            return len(expired_keys)
            
    def get_stats(self) -> Dict[str, Any]:
        """Obține statistici cache"""
        with self.lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            total_size = sum(entry.size_bytes for entry in self.cache.values())
            
            return {
                "entries": len(self.cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "total_size_bytes": total_size,
                "avg_size_bytes": total_size // len(self.cache) if self.cache else 0
            }

class DiskCache:
    """Cache persistent pe disk"""
    
    def __init__(self, cache_dir: Optional[str] = None, max_size_mb: int = 50):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "video_bot_cache")
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
        # Creează directorul de cache
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Index pentru quick lookup
        self.index_file = os.path.join(self.cache_dir, "cache_index.json")
        self.index: Dict[str, Dict[str, Any]] = self._load_index()
        self.lock = threading.RLock()
        
        logger.info(f"💾 Disk cache initialized: {self.cache_dir} (max: {max_size_mb}MB)")
        
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Încarcă indexul cache-ului"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Could not load cache index: {e}")
            
        return {}
        
    def _save_index(self):
        """Salvează indexul cache-ului"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Could not save cache index: {e}")
            
    def _get_cache_file_path(self, key: str) -> str:
        """Generează calea fișierului pentru o cheie"""
        # Hash-ul cheii pentru nume de fișier sigur
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"cache_{key_hash}.pkl")
        
    def get(self, key: str) -> Optional[Any]:
        """Obține o valoare din cache"""
        with self.lock:
            if key not in self.index:
                return None
                
            entry_info = self.index[key]
            
            # Verifică expirarea
            if entry_info.get('ttl') and time.time() - entry_info['created_at'] > entry_info['ttl']:
                self.remove(key)
                return None
                
            # Încearcă să încarce fișierul
            cache_file = self._get_cache_file_path(key)
            
            try:
                if os.path.exists(cache_file):
                    with open(cache_file, 'rb') as f:
                        value = pickle.load(f)
                        
                    # Actualizează statisticile în index
                    entry_info['last_accessed'] = time.time()
                    entry_info['access_count'] = entry_info.get('access_count', 0) + 1
                    self._save_index()
                    
                    if monitoring:
                        monitoring.record_cache_event("disk_get", hit=True)
                        
                    return value
                else:
                    # Fișierul lipsește, șterge din index
                    self.remove(key)
                    return None
                    
            except Exception as e:
                logger.warning(f"⚠️ Error loading cache file {cache_file}: {e}")
                self.remove(key)
                return None
                
    def put(self, key: str, value: Any, ttl: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Pune o valoare în cache"""
        with self.lock:
            cache_file = self._get_cache_file_path(key)
            
            try:
                # Salvează valoarea
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
                    
                # Obține dimensiunea fișierului
                file_size = os.path.getsize(cache_file)
                
                # Verifică dacă depășim limita de dimensiune
                if self._get_total_size() + file_size > self.max_size_bytes:
                    # Cleanup bazat pe LRU
                    self._cleanup_lru(file_size)
                    
                # Actualizează indexul
                current_time = time.time()
                self.index[key] = {
                    'created_at': current_time,
                    'last_accessed': current_time,
                    'access_count': 1,
                    'ttl': ttl,
                    'size_bytes': file_size,
                    'file_path': cache_file,
                    'metadata': metadata or {}
                }
                
                self._save_index()
                
                if monitoring:
                    monitoring.record_cache_event("disk_put")
                    
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Error saving cache file {cache_file}: {e}")
                # Șterge fișierul parțial dacă există
                if os.path.exists(cache_file):
                    try:
                        os.remove(cache_file)
                    except:
                        pass
                return False
                
    def remove(self, key: str) -> bool:
        """Elimină o intrare din cache"""
        with self.lock:
            if key not in self.index:
                return False
                
            entry_info = self.index[key]
            cache_file = entry_info.get('file_path') or self._get_cache_file_path(key)
            
            # Șterge fișierul
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except Exception as e:
                logger.warning(f"⚠️ Error removing cache file {cache_file}: {e}")
                
            # Șterge din index
            del self.index[key]
            self._save_index()
            
            if monitoring:
                monitoring.record_cache_event("disk_remove")
                
            return True
            
    def _get_total_size(self) -> int:
        """Calculează dimensiunea totală a cache-ului"""
        return sum(entry.get('size_bytes', 0) for entry in self.index.values())
        
    def _cleanup_lru(self, needed_space: int):
        """Curăță cache-ul bazat pe LRU pentru a face loc"""
        # Sortează entrările după last_accessed
        sorted_entries = sorted(
            self.index.items(),
            key=lambda x: x[1].get('last_accessed', 0)
        )
        
        freed_space = 0
        for key, entry_info in sorted_entries:
            if freed_space >= needed_space:
                break
                
            file_size = entry_info.get('size_bytes', 0)
            if self.remove(key):
                freed_space += file_size
                logger.debug(f"🧹 Evicted disk cache entry: {key}")
                
    def cleanup_expired(self) -> int:
        """Curăță intrarile expirate"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, entry_info in self.index.items():
                ttl = entry_info.get('ttl')
                if ttl and current_time - entry_info['created_at'] > ttl:
                    expired_keys.append(key)
                    
            for key in expired_keys:
                self.remove(key)
                
            return len(expired_keys)
            
    def clear(self):
        """Curăță tot cache-ul"""
        with self.lock:
            # Șterge toate fișierele
            for entry_info in self.index.values():
                cache_file = entry_info.get('file_path')
                if cache_file and os.path.exists(cache_file):
                    try:
                        os.remove(cache_file)
                    except:
                        pass
                        
            # Curăță indexul
            self.index.clear()
            self._save_index()
            
    def get_stats(self) -> Dict[str, Any]:
        """Obține statistici cache"""
        with self.lock:
            total_size = self._get_total_size()
            
            return {
                "entries": len(self.index),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_size_mb": self.max_size_mb,
                "utilization_percent": round((total_size / self.max_size_bytes) * 100, 2),
                "cache_dir": self.cache_dir
            }

class SmartCache(Generic[T]):
    """
    Cache inteligent cu strategie adaptivă pentru Free Tier
    
    Caracteristici:
    - Hybrid memory + disk storage
    - Strategii adaptive (LRU, TTL, size-based)
    - Auto-cleanup când memoria e scăzută
    - Prioritizare bazată pe frecvență și mărime
    - Integration cu memory manager
    """
    
    def __init__(self, 
                 memory_cache_size: int = 500,
                 disk_cache_size_mb: int = 50,
                 default_ttl: Optional[float] = 3600,  # 1 oră
                 strategy: CacheStrategy = CacheStrategy.SMART):
        
        self.strategy = strategy
        self.default_ttl = default_ttl
        
        # Initialize caches
        self.memory_cache = LRUCache[T](max_size=memory_cache_size, ttl=default_ttl)
        self.disk_cache = DiskCache(max_size_mb=disk_cache_size_mb)
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
        # Background cleanup
        self.cleanup_thread = None
        self.should_stop = False
        self.cleanup_interval = 300  # 5 minute
        
        # Configuration
        if config:
            cache_config = config.get('cache', {})
            self.default_ttl = cache_config.get('default_ttl', default_ttl)
            self.cleanup_interval = cache_config.get('cleanup_interval', 300)
            
        self._start_cleanup_thread()
        
        logger.info(f"🧠 Smart Cache initialized - Strategy: {strategy.value}")
        
    def get(self, key: str) -> Optional[T]:
        """Obține o valoare din cache (memory -> disk)"""
        self.stats['total_requests'] += 1
        
        # Încearcă mai întâi memory cache
        value = self.memory_cache.get(key)
        if value is not None:
            self.stats['memory_hits'] += 1
            return value
            
        # Încearcă disk cache
        value = self.disk_cache.get(key)
        if value is not None:
            self.stats['disk_hits'] += 1
            
            # Promovează în memory cache dacă e folosit des
            self._promote_to_memory(key, value)
            return value
            
        # Miss complet
        self.stats['misses'] += 1
        return None
        
    def put(self, key: str, 
            value: T, 
            ttl: Optional[float] = None,
            priority: str = "normal",
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Pune o valoare în cache cu strategie inteligentă
        
        Args:
            key: Cheia cache-ului
            value: Valoarea de cached
            ttl: Time to live (opcional)
            priority: Prioritatea ("high", "normal", "low") 
            metadata: Metadate suplimentare
        """
        
        effective_ttl = ttl or self.default_ttl
        cache_metadata = metadata or {}
        cache_metadata['priority'] = priority
        cache_metadata['created_by'] = 'smart_cache'
        
        # Verifică dimensiunea valorii
        try:
            value_size = len(str(value).encode('utf-8'))
        except:
            value_size = 1024
            
        # Strategie de plasare
        success = False
        
        if self.strategy == CacheStrategy.SMART:
            success = self._smart_put(key, value, effective_ttl, value_size, cache_metadata)
        elif self.strategy == CacheStrategy.LRU:
            # Doar memory cache cu LRU
            success = self.memory_cache.put(key, value, effective_ttl, cache_metadata)
        else:
            # Pentru alte strategii, folosește memory cache
            success = self.memory_cache.put(key, value, effective_ttl, cache_metadata)
            
        # Înregistrează allocation în memory manager dacă e în memorie
        if success and memory_manager:
            memory_manager.track_allocation(
                f"cache_{key}",
                value_size / (1024 * 1024),  # MB
                MemoryPriority.LOW,
                lambda: self.remove(key)
            )
            
        return success
        
    def _smart_put(self, key: str, value: T, ttl: float, value_size: int, metadata: Dict[str, Any]) -> bool:
        """Strategie inteligentă de plasare în cache"""
        
        # Pentru valori mici și prioritate înaltă -> memory
        if value_size < 10240 and metadata.get('priority') == 'high':  # < 10KB
            return self.memory_cache.put(key, value, ttl, metadata)
            
        # Pentru valori mari -> disk
        if value_size > 1024 * 1024:  # > 1MB
            return self.disk_cache.put(key, value, ttl, metadata)
            
        # Pentru prioritate normală, încearcă memory, apoi disk
        if self.memory_cache.put(key, value, ttl, metadata):
            return True
        else:
            return self.disk_cache.put(key, value, ttl, metadata)
            
    def _promote_to_memory(self, key: str, value: T):
        """Promovează o valoare din disk în memory cache"""
        try:
            # Verifică dacă avem spațiu și dacă merită
            if len(self.memory_cache.cache) < self.memory_cache.max_size * 0.8:
                self.memory_cache.put(key, value, self.default_ttl)
        except Exception as e:
            logger.debug(f"Could not promote {key} to memory: {e}")
            
    def remove(self, key: str) -> bool:
        """Elimină o intrare din ambele cache-uri"""
        memory_removed = self.memory_cache.remove(key)
        disk_removed = self.disk_cache.remove(key)
        
        # Eliberează allocation din memory manager
        if memory_manager:
            memory_manager.release_allocation(f"cache_{key}")
            
        return memory_removed or disk_removed
        
    def clear(self):
        """Curăță ambele cache-uri"""
        self.memory_cache.clear()
        self.disk_cache.clear()
        
        # Reset statistics
        self.stats = {k: 0 for k in self.stats}
        
    def _start_cleanup_thread(self):
        """Pornește thread-ul de cleanup"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="CacheCleanup"
            )
            self.cleanup_thread.start()
            
    def _cleanup_loop(self):
        """Loop de cleanup periodic"""
        while not self.should_stop:
            try:
                # Cleanup expired entries
                memory_cleaned = self.memory_cache.cleanup_expired()
                disk_cleaned = self.disk_cache.cleanup_expired()
                
                if memory_cleaned > 0 or disk_cleaned > 0:
                    logger.info(f"🧹 Cache cleanup: {memory_cleaned} memory, {disk_cleaned} disk entries")
                    
                # Verifică presiunea memoriei
                if memory_manager:
                    memory_status = asyncio.run(memory_manager.get_memory_status())
                    if memory_status.get('usage_percent', 0) > 85:
                        # Cleanup agresiv când memoria e scăzută
                        self._aggressive_cleanup()
                        
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"❌ Cache cleanup error: {e}")
                time.sleep(60)
                
    def _aggressive_cleanup(self):
        """Cleanup agresiv când memoria e scăzută"""
        # Reduce memory cache size temporar
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
