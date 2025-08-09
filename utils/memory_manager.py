# utils/memory_manager.py - Memory Management pentru Free Tier hosting
# Versiunea: 2.0.0 - Arhitectura Modulară

import os
import psutil
import gc
import logging
import time
import threading
import tempfile
import shutil
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import weakref

try:
    from utils.config import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)

class MemoryPriority(Enum):
    """Priorități pentru cleanup-ul memoriei"""
    CRITICAL = 1    # Cleanup imediat
    HIGH = 2        # Cleanup urgent
    MEDIUM = 3      # Cleanup normal
    LOW = 4         # Cleanup când avem timp

@dataclass
class MemoryAllocation:
    """Informații despre o alocare de memorie"""
    id: str
    size_mb: float
    created_at: float
    last_accessed: float
    priority: MemoryPriority
    cleanup_callback: Optional[Callable] = None
    metadata: Optional[Dict[str, Any]] = None

class MemoryMonitor:
    """Monitor pentru statisticile de memorie"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = 0.0
        self.peak_memory = 0.0
        self.measurements = []
        self.measurement_limit = 1000  # Păstrează ultimele 1000 de măsurători
        
        # Încercăm să obținem memoria de bază
        try:
            self.baseline_memory = self.get_current_memory_mb()
            self.peak_memory = self.baseline_memory
            logger.info(f"📊 Memory Monitor initialized - Baseline: {self.baseline_memory:.1f}MB")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize memory monitoring: {e}")
            
    def get_current_memory_mb(self) -> float:
        """Obține memoria curentă în MB"""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convertește la MB
        except Exception as e:
            logger.warning(f"⚠️ Could not get memory info: {e}")
            return 0.0
            
    def get_memory_percent(self) -> float:
        """Obține procentajul de memorie folosit"""
        try:
            return self.process.memory_percent()
        except Exception as e:
            logger.warning(f"⚠️ Could not get memory percent: {e}")
            return 0.0
            
    def record_measurement(self):
        """Înregistrează o măsurătoare de memorie"""
        current_memory = self.get_current_memory_mb()
        current_time = time.time()
        
        self.measurements.append({
            'timestamp': current_time,
            'memory_mb': current_memory,
            'memory_percent': self.get_memory_percent()
        })
        
        # Actualizează peak memory
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
            
        # Limitează numărul de măsurători
        if len(self.measurements) > self.measurement_limit:
            self.measurements = self.measurements[-self.measurement_limit:]
            
        return current_memory
        
    def get_memory_stats(self) -> Dict[str, Any]:
        """Obține statistici despre memorie"""
        current_memory = self.get_current_memory_mb()
        
        # Calculează trend-ul recent
        recent_measurements = self.measurements[-10:] if len(self.measurements) >= 10 else self.measurements
        trend = "stable"
        
        if len(recent_measurements) >= 2:
            first_memory = recent_measurements[0]['memory_mb']
            last_memory = recent_measurements[-1]['memory_mb']
            change_percent = ((last_memory - first_memory) / first_memory) * 100
            
            if change_percent > 5:
                trend = "increasing"
            elif change_percent < -5:
                trend = "decreasing"
                
        return {
            'current_memory_mb': round(current_memory, 2),
            'baseline_memory_mb': round(self.baseline_memory, 2),
            'peak_memory_mb': round(self.peak_memory, 2),
            'memory_percent': round(self.get_memory_percent(), 2),
            'growth_mb': round(current_memory - self.baseline_memory, 2),
            'trend': trend,
            'measurements_count': len(self.measurements)
        }

class FileCleanupManager:
    """Manager pentru cleanup-ul fișierelor temporare"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.tracked_files = {}  # file_path -> creation_time
        self.cleanup_age_seconds = 3600  # 1 oră
        
    def track_file(self, file_path: str, max_age_seconds: Optional[int] = None):
        """Urmărește un fișier pentru cleanup automat"""
        self.tracked_files[file_path] = {
            'created_at': time.time(),
            'max_age': max_age_seconds or self.cleanup_age_seconds
        }
        
    def cleanup_old_files(self) -> int:
        """Curăță fișierele vechi și returnează numărul de fișiere șterse"""
        current_time = time.time()
        cleaned_count = 0
        
        for file_path, file_info in list(self.tracked_files.items()):
            age = current_time - file_info['created_at']
            
            if age > file_info['max_age']:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"🧹 Cleaned up old file: {os.path.basename(file_path)}")
                        cleaned_count += 1
                    del self.tracked_files[file_path]
                except Exception as e:
                    logger.warning(f"⚠️ Could not cleanup file {file_path}: {e}")
                    
        return cleaned_count
        
    def cleanup_directory(self, directory: str, max_age_seconds: int = 3600) -> int:
        """Curăță toate fișierele vechi dintr-un director"""
        cleaned_count = 0
        current_time = time.time()
        
        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    
                    if file_age > max_age_seconds:
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Could not remove {file_path}: {e}")
                            
        except Exception as e:
            logger.warning(f"⚠️ Could not clean directory {directory}: {e}")
            
        return cleaned_count

class MemoryManager:
    """
    Advanced Memory Manager pentru Free Tier hosting
    
    Caracteristici:
    - Monitoring continuu al memoriei
    - Cleanup automat la praguri definite
    - Gestionarea fișierelor temporare
    - Prioritizarea cleanup-urilor
    - Garbage collection optimizat
    - Alerting pentru memory leaks
    """
    
    def __init__(self, max_memory_mb: int = 200):
        self.max_memory_mb = max_memory_mb
        self.warning_threshold = max_memory_mb * 0.8  # 80% warning
        self.critical_threshold = max_memory_mb * 0.95  # 95% critical
        
        # Componente
        self.monitor = MemoryMonitor()
        self.file_cleanup = FileCleanupManager()
        
        # Allocations tracking
        self.allocations: Dict[str, MemoryAllocation] = {}
        self.weak_references = weakref.WeakValueDictionary()
        
        # Cleanup settings
        self.auto_cleanup_enabled = True
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  # 1 minut
        self.last_gc_collect = time.time()
        self.gc_interval = 300  # 5 minute
        
        # Statistics
        self.stats = {
            'cleanups_performed': 0,
            'memory_freed_mb': 0.0,
            'files_cleaned': 0,
            'gc_collections': 0,
            'allocations_tracked': 0
        }
        
        # Background cleanup thread
        self.cleanup_thread = None
        self.should_stop = False
        
        if config:
            perf_config = config.get('performance', {})
            self.max_memory_mb = perf_config.get('memory_limit_mb', max_memory_mb)
            
        self._start_background_cleanup()
        
        logger.info(f"💾 Memory Manager initialized - Limit: {self.max_memory_mb}MB")
        
    def track_allocation(self, 
                        allocation_id: str,
                        estimated_size_mb: float,
                        priority: MemoryPriority = MemoryPriority.MEDIUM,
                        cleanup_callback: Optional[Callable] = None,
                        obj: Any = None) -> bool:
        """
        Urmărește o alocare de memorie
        
        Args:
            allocation_id: ID unic pentru alocare
            estimated_size_mb: Mărimea estimată în MB
            priority: Prioritatea pentru cleanup
            cleanup_callback: Funcția de apelat pentru cleanup
            obj: Obiectul de urmărit (optional, pentru weak references)
            
        Returns:
            True dacă alocarea poate fi făcută
        """
        
        current_memory = self.monitor.record_measurement()
        
        # Verifică dacă avem suficientă memorie
        if current_memory + estimated_size_mb > self.max_memory_mb:
            logger.warning(f"⚠️ Memory limit would be exceeded: {current_memory:.1f} + {estimated_size_mb:.1f} > {self.max_memory_mb}")
            
            # Încearcă cleanup urgent
            freed_mb = await self.cleanup_memory(force=True, target_mb=estimated_size_mb)
            
            # Verifică din nou după cleanup
            current_memory = self.monitor.record_measurement()
            if current_memory + estimated_size_mb > self.max_memory_mb:
                return False
                
        # Înregistrează alocarea
        allocation = MemoryAllocation(
            id=allocation_id,
            size_mb=estimated_size_mb,
            created_at=time.time(),
            last_accessed=time.time(),
            priority=priority,
            cleanup_callback=cleanup_callback
        )
        
        self.allocations[allocation_id] = allocation
        
        # Weak reference dacă avem obiectul
        if obj is not None:
            self.weak_references[allocation_id] = obj
            
        self.stats['allocations_tracked'] += 1
        
        logger.debug(f"📝 Tracked allocation {allocation_id}: {estimated_size_mb:.1f}MB")
        return True
        
    def release_allocation(self, allocation_id: str):
        """Eliberează o alocare urmărită"""
        if allocation_id in self.allocations:
            allocation = self.allocations[allocation_id]
            
            # Apelează callback-ul de cleanup dacă există
            if allocation.cleanup_callback:
                try:
                    allocation.cleanup_callback()
                    logger.debug(f"🧹 Called cleanup callback for {allocation_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Cleanup callback failed for {allocation_id}: {e}")
                    
            del self.allocations[allocation_id]
            
            # Șterge și weak reference-ul
            if allocation_id in self.weak_references:
                del self.weak_references[allocation_id]
                
            logger.debug(f"✅ Released allocation {allocation_id}: {allocation.size_mb:.1f}MB")
            
    async def cleanup_memory(self, 
                           force: bool = False, 
                           target_mb: Optional[float] = None,
                           priority_threshold: MemoryPriority = MemoryPriority.MEDIUM) -> float:
        """
        Efectuează cleanup de memorie
        
        Args:
            force: Forțează cleanup-ul chiar dacă nu e necesar
            target_mb: Cantitatea de memorie de eliberat
            priority_threshold: Prioritatea minimă pentru cleanup
            
        Returns:
            Cantitatea de memorie eliberată (estimativ)
        """
        
        start_memory = self.monitor.record_measurement()
        
        if not force and start_memory < self.warning_threshold:
            return 0.0
            
        logger.info(f"🧹 Starting memory cleanup - Current: {start_memory:.1f}MB")
        
        freed_mb = 0.0
        
        # 1. Cleanup allocations by priority
        freed_mb += self._cleanup_allocations_by_priority(priority_threshold, target_mb)
        
        # 2. Cleanup old files
        freed_mb += self._cleanup_files()
        
        # 3. Force garbage collection
        freed_mb += self._force_garbage_collection()
        
        # 4. Cleanup dead weak references
        self._cleanup_dead_references()
        
        end_memory = self.monitor.record_measurement()
        actual_freed = start_memory - end_memory
        
        self.stats['cleanups_performed'] += 1
        self.stats['memory_freed_mb'] += max(actual_freed, 0)
        self.last_cleanup = time.time()
        
        logger.info(f"✅ Memory cleanup completed - Freed: {actual_freed:.1f}MB (estimated: {freed_mb:.1f}MB)")
        
        return actual_freed
        
    def _cleanup_allocations_by_priority(self, 
                                       priority_threshold: MemoryPriority,
                                       target_mb: Optional[float] = None) -> float:
        """Cleanup allocations bazat pe prioritate"""
        freed_mb = 0.0
        current_time = time.time()
        
        # Sortează allocations după prioritate și vârstă
        sorted_allocations = sorted(
            self.allocations.items(),
            key=lambda x: (x[1].priority.value, current_time - x[1].last_accessed),
            reverse=True
        )
        
        for allocation_id, allocation in sorted_allocations:
            if allocation.priority.value <= priority_threshold.value:
                # Verifică dacă obiectul mai există (pentru weak references)
                if allocation_id in self.weak_references:
                    obj = self.weak_references.get(allocation_id)
                    if obj is None:
                        # Obiectul a fost deja garbage collected
                        self.release_allocation(allocation_id)
                        freed_mb += allocation.size_mb
                        continue
                        
                # Cleanup bazat pe vârstă (mai vechi de 1 oră pentru LOW priority)
                age = current_time - allocation.created_at
                if allocation.priority == MemoryPriority.LOW and age > 3600:
                    self.release_allocation(allocation_id)
                    freed_mb += allocation.size_mb
                elif allocation.priority == MemoryPriority.MEDIUM and age > 1800:  # 30 min
                    self.release_allocation(allocation_id)
                    freed_mb += allocation.size_mb
                elif allocation.priority == MemoryPriority.HIGH and age > 600:  # 10 min
                    self.release_allocation(allocation_id)
                    freed_mb += allocation.size_mb
                    
                # Stop dacă am atins target-ul
                if target_mb and freed_mb >= target_mb:
                    break
                    
        return freed_mb
        
    def _cleanup_files(self) -> float:
        """Cleanup fișiere temporare"""
        try:
            # Cleanup fișierele urmărite
            files_cleaned = self.file_cleanup.cleanup_old_files()
            
            # Cleanup director temporar general
            files_cleaned += self.file_cleanup.cleanup_directory(
                self.file_cleanup.temp_dir, 
                max_age_seconds=3600  # 1 oră
            )
            
            self.stats['files_cleaned'] += files_cleaned
            
            # Estimează memoria eliberată (aproximativ 1MB per fișier)
            estimated_freed = files_cleaned * 1.0
            
            if files_cleaned > 0:
                logger.info(f"🧹 Cleaned up {files_cleaned} temporary files")
                
            return estimated_freed
            
        except Exception as e:
            logger.warning(f"⚠️ File cleanup failed: {e}")
            return 0.0
            
    def _force_garbage_collection(self) -> float:
        """Forțează garbage collection"""
        try:
            start_memory = self.monitor.get_current_memory_mb()
            
            # Forțează garbage collection
            collected = gc.collect()
            
            end_memory = self.monitor.get_current_memory_mb()
            freed_mb = max(0, start_memory - end_memory)
            
            self.stats['gc_collections'] += 1
            self.last_gc_collect = time.time()
            
            if freed_mb > 0.5:  # Log doar dacă am eliberat ceva semnificativ
                logger.info(f"🗑️ Garbage collection freed {freed_mb:.1f}MB ({collected} objects)")
                
            return freed_mb
            
        except Exception as e:
            logger.warning(f"⚠️ Garbage collection failed: {e}")
            return 0.0
            
    def _cleanup_dead_references(self):
        """Curăță weak references moarte"""
        dead_refs = []
        
        for allocation_id in list(self.weak_references.keys()):
            if self.weak_references.get(allocation_id) is None:
                dead_refs.append(allocation_id)
                
        for allocation_id in dead_refs:
            if allocation_id in self.allocations:
                self.release_allocation(allocation_id)
                
        if dead_refs:
            logger.debug(f"🧹 Cleaned {len(dead_refs)} dead weak references")
            
    def _start_background_cleanup(self):
        """Pornește thread-ul de cleanup în background"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.cleanup_thread = threading.Thread(
                target=self._background_cleanup_loop,
                daemon=True,
                name="MemoryCleanup"
            )
            self.cleanup_thread.start()
            
    def _background_cleanup_loop(self):
        """Loop principal pentru cleanup în background"""
        while not self.should_stop:
            try:
                current_time = time.time()
                current_memory = self.monitor.record_measurement()
                
                # Verifică dacă e timpul pentru cleanup
                if current_time - self.last_cleanup >= self.cleanup_interval:
                    if current_memory > self.warning_threshold:
                        priority = MemoryPriority.HIGH if current_memory > self.critical_threshold else MemoryPriority.MEDIUM
                        asyncio.run(self.cleanup_memory(priority_threshold=priority))
                        
                # Garbage collection periodic
                if current_time - self.last_gc_collect >= self.gc_interval:
                    self._force_garbage_collection()
                    
                # Sleep pentru a nu consuma prea mult CPU
                time.sleep(30)  # Verifică la fiecare 30 secunde
                
            except Exception as e:
                logger.error(f"❌ Background cleanup error: {e}")
                time.sleep(60)  # Sleep mai lung în caz de eroare
                
    async def get_memory_status(self) -> Dict[str, Any]:
        """Obține statusul complet al memoriei"""
        current_memory = self.monitor.record_measurement()
        memory_stats = self.monitor.get_memory_stats()
        
        # Calculează utilizarea
        usage_percent = (current_memory / self.max_memory_mb) * 100
        
        # Determină statusul
        if current_memory > self.critical_threshold:
            status = "critical"
        elif current_memory > self.warning_threshold:
            status = "warning"
        else:
            status = "healthy"
            
        return {
            'status': status,
            'current_memory_mb': current_memory,
            'max_memory_mb': self.max_memory_mb,
            'usage_percent': round(usage_percent, 2),
            'warning_threshold_mb': self.warning_threshold,
            'critical_threshold_mb': self.critical_threshold,
            'tracked_allocations': len(self.allocations),
            'tracked_files': len(self.file_cleanup.tracked_files),
            'memory_stats': memory_stats,
            'cleanup_stats': self.stats
        }
        
    def stop(self):
        """Oprește background cleanup"""
        self.should_stop = True
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)

# Singleton instance pentru MemoryManager
memory_manager = MemoryManager()
