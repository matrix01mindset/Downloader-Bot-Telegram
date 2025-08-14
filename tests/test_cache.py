# tests/test_cache.py - Unit tests for Smart Cache System
# Versiunea: 2.0.0 - Arhitectura Modulară

import pytest
import asyncio
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import system under test
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.cache import (
    SmartCache, LRUCache, DiskCache, 
    CacheStrategy, CacheTier, CacheEntry,
    generate_cache_key, cached, cache
)


class TestCacheEntry:
    """Test suite pentru CacheEntry"""
    
    def test_cache_entry_creation(self):
        """Test crearea unei instanțe CacheEntry"""
        current_time = time.time()
        
        entry = CacheEntry(
            key="test_key",
            value="test_value", 
            created_at=current_time,
            last_accessed=current_time,
            access_count=1,
            ttl=3600,
            size_bytes=1024,
            metadata={"source": "test"}
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.created_at == current_time
        assert entry.ttl == 3600
        assert entry.size_bytes == 1024
        assert entry.metadata == {"source": "test"}
        
    def test_cache_entry_with_default_metadata(self):
        """Test CacheEntry cu metadata default"""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1,
            ttl=None,
            size_bytes=100
        )
        
        assert entry.metadata == {}
        
    def test_cache_entry_is_expired(self):
        """Test verificarea expirării"""
        current_time = time.time()
        old_time = current_time - 7200  # 2 ore în urmă
        
        # Entry cu TTL expirat
        expired_entry = CacheEntry(
            key="expired",
            value="value",
            created_at=old_time,
            last_accessed=old_time, 
            access_count=1,
            ttl=3600,  # 1 oră TTL
            size_bytes=100
        )
        
        # Entry fără TTL
        no_ttl_entry = CacheEntry(
            key="no_ttl",
            value="value",
            created_at=old_time,
            last_accessed=old_time,
            access_count=1,
            ttl=None,
            size_bytes=100
        )
        
        # Entry fresh
        fresh_entry = CacheEntry(
            key="fresh", 
            value="value",
            created_at=current_time,
            last_accessed=current_time,
            access_count=1,
            ttl=3600,
            size_bytes=100
        )
        
        assert expired_entry.is_expired is True
        assert no_ttl_entry.is_expired is False
        assert fresh_entry.is_expired is False
        
    def test_cache_entry_age_seconds(self):
        """Test calcularea vârstei"""
        past_time = time.time() - 300  # 5 minute în urmă
        
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=past_time,
            last_accessed=past_time,
            access_count=1,
            ttl=None,
            size_bytes=100
        )
        
        age = entry.age_seconds
        assert 295 <= age <= 305  # ~5 minute cu toleranță


class TestLRUCache:
    """Test suite pentru LRUCache"""
    
    @pytest.fixture
    def lru_cache(self):
        """Crează o instanță fresh de LRUCache"""
        return LRUCache[str](max_size=3, ttl=3600)
        
    def test_lru_cache_initialization(self, lru_cache):
        """Test inițializarea LRUCache"""
        assert lru_cache.max_size == 3
        assert lru_cache.ttl == 3600
        assert len(lru_cache.cache) == 0
        assert lru_cache._hits == 0
        assert lru_cache._misses == 0
        
    def test_put_and_get(self, lru_cache):
        """Test operațiunile de bază put/get"""
        # Put
        result = lru_cache.put("key1", "value1")
        assert result is True
        
        # Get
        value = lru_cache.get("key1")
        assert value == "value1"
        
        # Get inexistent
        value = lru_cache.get("nonexistent")
        assert value is None
        
    def test_lru_eviction(self, lru_cache):
        """Test eviction policy LRU"""
        # Umple cache-ul
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2") 
        lru_cache.put("key3", "value3")
        
        # Accesează key1 pentru a-l face recently used
        lru_cache.get("key1")
        
        # Adaugă un nou key - key2 ar trebui să fie evicted
        lru_cache.put("key4", "value4")
        
        assert lru_cache.get("key1") == "value1"  # Still there
        assert lru_cache.get("key2") is None      # Evicted
        assert lru_cache.get("key3") == "value3"  # Still there
        assert lru_cache.get("key4") == "value4"  # New one
        
    def test_ttl_expiration(self, lru_cache):
        """Test expirarea TTL"""
        # Cache cu TTL scurt
        short_ttl_cache = LRUCache[str](max_size=5, ttl=1)  # 1 secundă
        
        short_ttl_cache.put("temp_key", "temp_value")
        
        # Ar trebui să existe
        assert short_ttl_cache.get("temp_key") == "temp_value"
        
        # Așteaptă să expire
        time.sleep(1.1)
        
        # Ar trebui să fie None
        assert short_ttl_cache.get("temp_key") is None
        
    def test_update_existing_key(self, lru_cache):
        """Test actualizarea unei chei existente"""
        lru_cache.put("key1", "value1")
        lru_cache.put("key1", "updated_value")
        
        assert lru_cache.get("key1") == "updated_value"
        assert len(lru_cache.cache) == 1
        
    def test_remove(self, lru_cache):
        """Test ștergerea unei intrări"""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")
        
        result = lru_cache.remove("key1")
        assert result is True
        assert lru_cache.get("key1") is None
        assert lru_cache.get("key2") == "value2"
        
        # Remove inexistent
        result = lru_cache.remove("nonexistent")
        assert result is False
        
    def test_clear(self, lru_cache):
        """Test curățarea cache-ului"""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")
        
        lru_cache.clear()
        
        assert len(lru_cache.cache) == 0
        assert lru_cache._hits == 0
        assert lru_cache._misses == 0
        
    def test_cleanup_expired(self, lru_cache):
        """Test cleanup-ul intrărilor expirate"""
        # Adaugă intrări cu TTL diferit
        lru_cache.put("key1", "value1", ttl=1)    # Expire în 1 sec
        lru_cache.put("key2", "value2", ttl=3600) # Expire în 1 oră
        
        time.sleep(1.1)
        
        cleaned = lru_cache.cleanup_expired()
        
        assert cleaned == 1
        assert lru_cache.get("key1") is None
        assert lru_cache.get("key2") == "value2"
        
    def test_get_stats(self, lru_cache):
        """Test obținerea statisticilor"""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")
        
        # Hits și misses
        lru_cache.get("key1")      # Hit
        lru_cache.get("key2")      # Hit  
        lru_cache.get("missing")   # Miss
        
        stats = lru_cache.get_stats()
        
        assert stats["entries"] == 2
        assert stats["max_size"] == 3
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 66.67
        assert stats["total_size_bytes"] > 0


class TestDiskCache:
    """Test suite pentru DiskCache"""
    
    @pytest.fixture
    def disk_cache(self, tmp_path):
        """Crează DiskCache cu director temporar"""
        return DiskCache(cache_dir=str(tmp_path), max_size_mb=1)
        
    def test_disk_cache_initialization(self, disk_cache, tmp_path):
        """Test inițializarea DiskCache"""
        assert disk_cache.cache_dir == str(tmp_path)
        assert disk_cache.max_size_mb == 1
        assert os.path.exists(disk_cache.cache_dir)
        assert len(disk_cache.index) == 0
        
    def test_put_and_get(self, disk_cache):
        """Test operațiunile de bază put/get pe disk"""
        # Put
        result = disk_cache.put("test_key", {"data": "test_value"})
        assert result is True
        
        # Get
        value = disk_cache.get("test_key")
        assert value == {"data": "test_value"}
        
        # Get inexistent
        value = disk_cache.get("nonexistent")
        assert value is None
        
    def test_ttl_expiration_disk(self, disk_cache):
        """Test expirarea TTL pe disk"""
        disk_cache.put("temp_key", "temp_value", ttl=1)  # 1 secundă
        
        # Ar trebui să existe
        assert disk_cache.get("temp_key") == "temp_value"
        
        # Așteaptă să expire
        time.sleep(1.1)
        
        # Ar trebui să fie None
        assert disk_cache.get("temp_key") is None
        
    def test_remove_disk(self, disk_cache):
        """Test ștergerea de pe disk"""
        disk_cache.put("key1", "value1")
        disk_cache.put("key2", "value2")
        
        result = disk_cache.remove("key1")
        assert result is True
        assert disk_cache.get("key1") is None
        assert disk_cache.get("key2") == "value2"
        
    def test_cleanup_old_files_disk(self, disk_cache):
        """Test cleanup fișiere vechi pe disk"""
        disk_cache.put("old_key", "old_value", ttl=1)
        disk_cache.put("new_key", "new_value", ttl=3600)
        
        time.sleep(1.1)
        
        cleaned = disk_cache.cleanup_expired()
        
        assert cleaned == 1
        assert disk_cache.get("old_key") is None
        assert disk_cache.get("new_key") == "new_value"
        
    def test_size_based_eviction(self, disk_cache):
        """Test eviction bazat pe mărimea cache-ului"""
        # Adaugă câteva obiecte mari pentru a forța eviction
        large_object = "x" * 400000  # 400KB string pentru a forța cleanup
        
        disk_cache.put("key1", large_object)
        disk_cache.put("key2", large_object) 
        disk_cache.put("key3", large_object)  # Ar trebui să declanșeze cleanup (1.2MB > 1MB)
        
        # key1 ar trebui să fie evicted (LRU)
        assert disk_cache.get("key1") is None
        assert disk_cache.get("key2") == large_object
        assert disk_cache.get("key3") == large_object
        
    def test_get_stats_disk(self, disk_cache):
        """Test statistici pentru disk cache"""
        disk_cache.put("key1", "value1")
        disk_cache.put("key2", "value2")
        
        stats = disk_cache.get_stats()
        
        assert stats["entries"] == 2
        assert stats["total_size_mb"] > 0
        assert stats["max_size_mb"] == 1
        assert stats["utilization_percent"] >= 0
        assert stats["cache_dir"] == disk_cache.cache_dir


class TestSmartCache:
    """Test suite pentru SmartCache"""
    
    @pytest.fixture
    def smart_cache(self):
        """Crează SmartCache pentru testing"""
        cache = SmartCache[str](
            memory_cache_size=3,
            disk_cache_size_mb=1, 
            default_ttl=3600,
            strategy=CacheStrategy.SMART
        )
        cache.should_stop = True  # Oprește background cleanup
        if cache.cleanup_thread:
            cache.cleanup_thread.join(timeout=1)
        return cache
        
    def test_smart_cache_initialization(self, smart_cache):
        """Test inițializarea SmartCache"""
        assert smart_cache.strategy == CacheStrategy.SMART
        assert smart_cache.default_ttl == 3600
        assert smart_cache.memory_cache.max_size == 3
        assert smart_cache.disk_cache.max_size_mb == 1
        
    def test_memory_first_strategy(self, smart_cache):
        """Test strategia memory-first"""
        # Valoare mică, prioritate înaltă -> ar trebui să meargă în memory
        result = smart_cache.put("small_key", "small_value", priority="high")
        assert result is True
        
        # Verifică că e în memory cache
        memory_value = smart_cache.memory_cache.get("small_key")
        assert memory_value == "small_value"
        
    def test_disk_for_large_values(self, smart_cache):
        """Test plasarea valorilor mari pe disk"""
        large_value = "x" * 50000  # 50KB - ar trebui să meargă pe disk (>10KB)
        
        result = smart_cache.put("large_key", large_value)
        assert result is True
        
        # Ar trebui să fie pe disk, nu în memory
        memory_value = smart_cache.memory_cache.get("large_key")
        assert memory_value is None
        
        disk_value = smart_cache.disk_cache.get("large_key")
        assert disk_value == large_value
        
    def test_get_with_promotion(self, smart_cache):
        """Test promovarea din disk în memory la access frecvent"""
        # Pune ceva pe disk direct
        smart_cache.disk_cache.put("disk_key", "disk_value")
        
        # Get ar trebui să îl promoveze în memory
        value = smart_cache.get("disk_key")
        assert value == "disk_value"
        
        # Verifică că stats sunt actualizate
        assert smart_cache.stats['disk_hits'] > 0
        
    def test_memory_and_disk_hit_stats(self, smart_cache):
        """Test statistics pentru hit-uri memory și disk"""
        # Memory hit
        smart_cache.memory_cache.put("mem_key", "mem_value")
        value1 = smart_cache.get("mem_key")
        
        # Disk hit
        smart_cache.disk_cache.put("disk_key", "disk_value")
        value2 = smart_cache.get("disk_key")
        
        # Miss
        value3 = smart_cache.get("missing_key")
        
        assert smart_cache.stats['memory_hits'] >= 1
        assert smart_cache.stats['disk_hits'] >= 1
        assert smart_cache.stats['misses'] >= 1
        
    def test_remove_from_both_caches(self, smart_cache):
        """Test ștergerea din ambele cache-uri"""
        smart_cache.memory_cache.put("key", "value")
        smart_cache.disk_cache.put("key", "value")
        
        result = smart_cache.remove("key")
        assert result is True
        
        assert smart_cache.memory_cache.get("key") is None
        assert smart_cache.disk_cache.get("key") is None
        
    def test_clear_both_caches(self, smart_cache):
        """Test curățarea ambelor cache-uri"""
        smart_cache.memory_cache.put("mem_key", "mem_value")
        smart_cache.disk_cache.put("disk_key", "disk_value")
        
        smart_cache.clear()
        
        assert len(smart_cache.memory_cache.cache) == 0
        assert len(smart_cache.disk_cache.index) == 0
        
        # Stats ar trebui să fie resetate
        assert all(count == 0 for count in smart_cache.stats.values())
        
    @pytest.mark.asyncio
    async def test_get_stats(self, smart_cache):
        """Test obținerea statisticilor pentru SmartCache"""
        # Adaugă niște date pentru stats
        smart_cache.put("key1", "value1")
        smart_cache.get("key1")  # Hit
        smart_cache.get("missing")  # Miss
        
        stats = await smart_cache.get_stats()
        
        assert "strategy" in stats
        assert "overall" in stats
        assert "memory_cache" in stats
        assert "disk_cache" in stats
        assert "health" in stats
        
        # Verifică calculele
        overall = stats["overall"]
        assert "hit_rate_percent" in overall
        assert "total_requests" in overall
        assert "memory_hits" in overall
        assert "disk_hits" in overall
        assert "misses" in overall


class TestCacheHelperFunctions:
    """Test suite pentru funcțiile helper de cache"""
    
    def test_generate_cache_key_basic(self):
        """Test generarea unei chei de cache de bază"""
        key = generate_cache_key("prefix", "arg1", "arg2")
        
        assert isinstance(key, str)
        assert len(key) == 32  # SHA256 truncat
        
        # Același input ar trebui să producă aceeași cheie
        key2 = generate_cache_key("prefix", "arg1", "arg2")
        assert key == key2
        
    def test_generate_cache_key_with_kwargs(self):
        """Test generarea cheii cu kwargs"""
        key1 = generate_cache_key("prefix", user_id=123, action="download")
        key2 = generate_cache_key("prefix", action="download", user_id=123)  # Ordine diferită
        
        # Ar trebui să fie identice (kwargs sunt sortate)
        assert key1 == key2
        
    def test_generate_cache_key_different_inputs(self):
        """Test că input-uri diferite produc chei diferite"""
        key1 = generate_cache_key("prefix", "arg1")
        key2 = generate_cache_key("prefix", "arg2")
        key3 = generate_cache_key("different_prefix", "arg1")
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class TestCachedDecorator:
    """Test suite pentru decoratorul @cached"""
    
    @pytest.fixture
    def test_cache(self):
        """Mock cache pentru testing"""
        return SmartCache[Any](memory_cache_size=10, disk_cache_size_mb=1)
        
    def test_cached_decorator_sync_function(self, test_cache):
        """Test decoratorul pe funcție sincronă"""
        call_count = 0
        
        with patch('utils.cache.cache', test_cache):
            @cached(ttl=3600, key_prefix="test")
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y
                
            # Prima apelare - ar trebui să execute funcția
            result1 = expensive_function(2, 3)
            assert result1 == 5
            assert call_count == 1
            
            # A doua apelare - ar trebui să vină din cache
            result2 = expensive_function(2, 3)
            assert result2 == 5
            assert call_count == 1  # Nu s-a mai apelat
            
            # Apelare cu parametri diferiți - ar trebui să execute din nou
            result3 = expensive_function(5, 7)
            assert result3 == 12
            assert call_count == 2
            
    @pytest.mark.asyncio
    async def test_cached_decorator_async_function(self, test_cache):
        """Test decoratorul pe funcție asincronă"""
        call_count = 0
        
        with patch('utils.cache.cache', test_cache):
            @cached(ttl=1800, key_prefix="async_test")
            async def async_expensive_function(x):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.01)  # Simulează operațiune asincronă
                return x * 2
                
            # Prima apelare
            result1 = await async_expensive_function(5)
            assert result1 == 10
            assert call_count == 1
            
            # A doua apelare - din cache
            result2 = await async_expensive_function(5)
            assert result2 == 10
            assert call_count == 1
            
    def test_cached_decorator_none_result(self, test_cache):
        """Test că rezultatele None nu sunt cached"""
        call_count = 0
        
        with patch('utils.cache.cache', test_cache):
            @cached(key_prefix="none_test")
            def function_returning_none():
                nonlocal call_count
                call_count += 1
                return None
                
            result1 = function_returning_none()
            result2 = function_returning_none()
            
            assert result1 is None
            assert result2 is None
            assert call_count == 2  # Apelat de fiecare dată


@pytest.mark.integration
class TestCacheIntegration:
    """Teste de integrare pentru sistemul de cache"""
    
    @pytest.mark.asyncio
    async def test_full_cache_workflow(self):
        """Test workflow complet de cache"""
        smart_cache = SmartCache[str](
            memory_cache_size=2,
            disk_cache_size_mb=1,
            default_ttl=60
        )
        smart_cache.should_stop = True
        
        try:
            # 1. Put diferite tipuri de date
            smart_cache.put("small_data", "small", priority="high")      # Memory
            smart_cache.put("medium_data", "x" * 1000, priority="normal") # Memory fallback to disk
            
            # 2. Get și verifică promovarea
            value1 = smart_cache.get("small_data")
            value2 = smart_cache.get("medium_data") 
            
            assert value1 == "small"
            assert value2 == "x" * 1000
            
            # 3. Stats și monitoring
            stats = await smart_cache.get_stats()
            assert stats["overall"]["total_requests"] > 0
            assert stats["overall"]["hit_rate_percent"] >= 0
            
            # 4. Cleanup și clear
            smart_cache.clear()
            
            assert smart_cache.get("small_data") is None
            assert smart_cache.get("medium_data") is None
            
        finally:
            smart_cache.stop()
            
    def test_memory_pressure_simulation(self):
        """Test simularea presiunii pe memorie"""
        smart_cache = SmartCache[str](
            memory_cache_size=2,  # Foarte mic pentru a forța eviction
            disk_cache_size_mb=1
        )
        smart_cache.should_stop = True
        
        try:
            # Umple memory cache
            smart_cache.put("key1", "value1", priority="normal")
            smart_cache.put("key2", "value2", priority="normal")
            
            # Forțează eviction cu un nou key
            smart_cache.put("key3", "value3", priority="high")
            
            # Verifică că key3 e în memory (prioritate înaltă)
            assert smart_cache.memory_cache.get("key3") == "value3"
            
            # Cel puțin unul din key1/key2 ar trebui să fie evicted din memory
            mem_key1 = smart_cache.memory_cache.get("key1")
            mem_key2 = smart_cache.memory_cache.get("key2")
            
            # Dar toate ar trebui să fie accesibile via get (disk fallback)
            assert smart_cache.get("key1") == "value1"
            assert smart_cache.get("key2") == "value2"
            assert smart_cache.get("key3") == "value3"
            
        finally:
            smart_cache.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
