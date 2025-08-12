# tests/test_memory_manager.py - Unit tests for Memory Manager
# Versiunea: 2.0.0 - Arhitectura Modulară

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import system under test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.memory_manager import (
    MemoryManager, MemoryMonitor, FileCleanupManager, 
    MemoryPriority, MemoryAllocation, memory_manager
)


class TestMemoryMonitor:
    """Test suite pentru MemoryMonitor"""
    
    @pytest.fixture
    def monitor(self):
        """Crează o instanță fresh de MemoryMonitor"""
        with patch('psutil.Process') as mock_process:
            mock_process_instance = Mock()
            mock_process_instance.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
            mock_process_instance.memory_percent.return_value = 25.0
            mock_process.return_value = mock_process_instance
            
            return MemoryMonitor()
            
    def test_memory_monitor_initialization(self, monitor):
        """Test inițializarea MemoryMonitor"""
        assert monitor.baseline_memory > 0
        assert monitor.peak_memory >= monitor.baseline_memory
        assert len(monitor.measurements) == 0
        assert monitor.measurement_limit == 1000
        
    def test_get_current_memory_mb(self, monitor):
        """Test obținerea memoriei curente"""
        memory = monitor.get_current_memory_mb()
        assert memory > 0
        assert isinstance(memory, float)
        
    def test_get_memory_percent(self, monitor):
        """Test obținerea procentajului de memorie"""
        percent = monitor.get_memory_percent()
        assert 0 <= percent <= 100
        assert isinstance(percent, float)
        
    def test_record_measurement(self, monitor):
        """Test înregistrarea măsurătorilor"""
        initial_count = len(monitor.measurements)
        
        current_memory = monitor.record_measurement()
        
        assert len(monitor.measurements) == initial_count + 1
        assert current_memory > 0
        
        # Verifică că peak memory se actualizează
        old_peak = monitor.peak_memory
        with patch.object(monitor, 'get_current_memory_mb', return_value=old_peak + 10):
            monitor.record_measurement()
            assert monitor.peak_memory > old_peak
            
    def test_measurements_limit(self, monitor):
        """Test limitarea numărului de măsurători"""
        # Adaugă mai multe măsurători decât limita
        for _ in range(monitor.measurement_limit + 100):
            monitor.record_measurement()
            
        assert len(monitor.measurements) == monitor.measurement_limit
        
    def test_get_memory_stats(self, monitor):
        """Test obținerea statisticilor de memorie"""
        # Înregistrează câteva măsurători
        for _ in range(10):
            monitor.record_measurement()
            
        stats = monitor.get_memory_stats()
        
        assert 'current_memory_mb' in stats
        assert 'baseline_memory_mb' in stats
        assert 'peak_memory_mb' in stats
        assert 'memory_percent' in stats
        assert 'growth_mb' in stats
        assert 'trend' in stats
        assert 'measurements_count' in stats
        
        assert stats['measurements_count'] == 10
        assert stats['trend'] in ['stable', 'increasing', 'decreasing']


class TestFileCleanupManager:
    """Test suite pentru FileCleanupManager"""
    
    @pytest.fixture
    def cleanup_manager(self, tmp_path):
        """Crează FileCleanupManager cu director temporar"""
        return FileCleanupManager(str(tmp_path))
        
    def test_file_cleanup_manager_init(self, cleanup_manager):
        """Test inițializarea FileCleanupManager"""
        assert cleanup_manager.temp_dir is not None
        assert cleanup_manager.cleanup_age_seconds == 3600
        assert len(cleanup_manager.tracked_files) == 0
        
    def test_track_file(self, cleanup_manager):
        """Test urmărirea unui fișier"""
        file_path = "/tmp/test_file.txt"
        cleanup_manager.track_file(file_path)
        
        assert file_path in cleanup_manager.tracked_files
        
        file_info = cleanup_manager.tracked_files[file_path]
        assert 'created_at' in file_info
        assert 'max_age' in file_info
        assert file_info['max_age'] == 3600
        
    def test_track_file_custom_age(self, cleanup_manager):
        """Test urmărirea cu vârstă custom"""
        file_path = "/tmp/custom_file.txt"
        custom_age = 1800  # 30 minute
        
        cleanup_manager.track_file(file_path, custom_age)
        
        file_info = cleanup_manager.tracked_files[file_path]
        assert file_info['max_age'] == custom_age
        
    def test_cleanup_old_files(self, cleanup_manager, tmp_path):
        """Test curățarea fișierelor vechi"""
        # Creează fișiere de test
        old_file = tmp_path / "old_file.txt"
        old_file.write_text("old content")
        
        new_file = tmp_path / "new_file.txt"
        new_file.write_text("new content")
        
        # Urmărește fișierele cu vârste diferite
        cleanup_manager.track_file(str(old_file), 1)  # 1 secundă
        cleanup_manager.track_file(str(new_file), 3600)  # 1 oră
        
        # Așteaptă să treacă timpul pentru fișierul vechi
        time.sleep(1.1)
        
        cleaned_count = cleanup_manager.cleanup_old_files()
        
        assert cleaned_count == 1
        assert not old_file.exists()
        assert new_file.exists()
        assert str(old_file) not in cleanup_manager.tracked_files
        
    def test_cleanup_directory(self, cleanup_manager, tmp_path):
        """Test curățarea unui director"""
        # Creează fișiere în director
        old_file = tmp_path / "old.txt"
        old_file.write_text("old")
        
        # Modifică timpul de creare pentru a simula fișier vechi
        old_time = time.time() - 7200  # 2 ore în urmă
        os.utime(str(old_file), (old_time, old_time))
        
        new_file = tmp_path / "new.txt" 
        new_file.write_text("new")
        
        cleaned_count = cleanup_manager.cleanup_directory(str(tmp_path), 3600)  # 1 oră
        
        assert cleaned_count == 1
        assert not old_file.exists()
        assert new_file.exists()


class TestMemoryManager:
    """Test suite pentru MemoryManager"""
    
    @pytest.fixture
    def manager(self):
        """Crează MemoryManager pentru testing"""
        with patch('psutil.Process'):
            # Oprește background threads pentru testing
            manager = MemoryManager(max_memory_mb=100)
            manager.should_stop = True  # Oprește background thread
            if manager.cleanup_thread:
                manager.cleanup_thread.join(timeout=1)
            return manager
            
    def test_memory_manager_initialization(self, manager):
        """Test inițializarea MemoryManager"""
        assert manager.max_memory_mb == 100
        assert manager.warning_threshold == 80  # 80% din 100MB
        assert manager.critical_threshold == 95  # 95% din 100MB
        assert len(manager.allocations) == 0
        
    def test_track_allocation_success(self, manager):
        """Test urmărirea unei alocări cu succes"""
        with patch.object(manager.monitor, 'record_measurement', return_value=50.0):
            result = manager.track_allocation(
                "test_allocation",
                10.0,  # 10MB
                MemoryPriority.MEDIUM
            )
            
            assert result is True
            assert "test_allocation" in manager.allocations
            
            allocation = manager.allocations["test_allocation"]
            assert allocation.id == "test_allocation"
            assert allocation.size_mb == 10.0
            assert allocation.priority == MemoryPriority.MEDIUM
            
    def test_track_allocation_memory_limit_exceeded(self, manager):
        """Test când alocarea ar depăși limita de memorie"""
        with patch.object(manager.monitor, 'record_measurement', return_value=95.0):
            with patch.object(manager, 'cleanup_memory', new=AsyncMock(return_value=0)):
                result = manager.track_allocation(
                    "large_allocation",
                    10.0,  # Ar depăși 100MB limit
                    MemoryPriority.HIGH
                )
                
                assert result is False
                assert "large_allocation" not in manager.allocations
                
    def test_release_allocation(self, manager):
        """Test eliberarea unei alocări"""
        # Adaugă o alocare cu callback
        callback_called = Mock()
        
        with patch.object(manager.monitor, 'record_measurement', return_value=50.0):
            manager.track_allocation(
                "test_allocation",
                10.0,
                MemoryPriority.MEDIUM,
                cleanup_callback=callback_called
            )
            
        assert "test_allocation" in manager.allocations
        
        manager.release_allocation("test_allocation")
        
        assert "test_allocation" not in manager.allocations
        callback_called.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cleanup_memory(self, manager):
        """Test cleanup-ul memoriei"""
        # Adaugă câteva alocări
        with patch.object(manager.monitor, 'record_measurement', return_value=50.0):
            manager.track_allocation("alloc1", 5.0, MemoryPriority.LOW)
            manager.track_allocation("alloc2", 5.0, MemoryPriority.MEDIUM)
            manager.track_allocation("alloc3", 5.0, MemoryPriority.HIGH)
            
        # Mock cleanup methods
        with patch.object(manager, '_cleanup_allocations_by_priority', return_value=10.0):
            with patch.object(manager, '_cleanup_files', return_value=5.0):
                with patch.object(manager, '_force_garbage_collection', return_value=3.0):
                    
                    freed_memory = await manager.cleanup_memory(force=True)
                    
                    assert isinstance(freed_memory, float)
                    assert manager.stats['cleanups_performed'] > 0
                    
    def test_cleanup_allocations_by_priority(self, manager):
        """Test cleanup-ul bazat pe prioritate"""
        # Adaugă alocări cu priorități diferite
        current_time = time.time()
        old_time = current_time - 7200  # 2 ore în urmă
        
        with patch.object(manager.monitor, 'record_measurement', return_value=50.0):
            # Alocare veche cu prioritate LOW
            manager.track_allocation("old_low", 5.0, MemoryPriority.LOW)
            manager.allocations["old_low"].created_at = old_time
            
            # Alocare nouă cu prioritate HIGH  
            manager.track_allocation("new_high", 5.0, MemoryPriority.HIGH)
            
        freed = manager._cleanup_allocations_by_priority(MemoryPriority.LOW)
        
        # Alocarea veche LOW ar trebui să fie curățată
        assert freed > 0
        assert "old_low" not in manager.allocations
        assert "new_high" in manager.allocations
        
    def test_force_garbage_collection(self, manager):
        """Test garbage collection forțat"""
        with patch('gc.collect', return_value=42) as mock_gc:
            with patch.object(manager.monitor, 'get_current_memory_mb', side_effect=[100.0, 95.0]):
                freed = manager._force_garbage_collection()
                
                mock_gc.assert_called_once()
                assert freed == 5.0  # Diferența între măsurători
                assert manager.stats['gc_collections'] == 1
                
    @pytest.mark.asyncio
    async def test_get_memory_status(self, manager):
        """Test obținerea statusului memoriei"""
        with patch.object(manager.monitor, 'record_measurement', return_value=75.0):
            with patch.object(manager.monitor, 'get_memory_stats', return_value={'test': 'stats'}):
                
                status = await manager.get_memory_status()
                
                assert 'status' in status
                assert 'current_memory_mb' in status
                assert 'max_memory_mb' in status
                assert 'usage_percent' in status
                assert 'tracked_allocations' in status
                assert 'memory_stats' in status
                assert 'cleanup_stats' in status
                
                # Verifică calculul statusului
                assert status['usage_percent'] == 75.0
                assert status['status'] == 'healthy'  # Sub warning threshold
                
    @pytest.mark.asyncio
    async def test_memory_status_warning(self, manager):
        """Test status warning la memoria înaltă"""
        with patch.object(manager.monitor, 'record_measurement', return_value=85.0):
            with patch.object(manager.monitor, 'get_memory_stats', return_value={}):
                
                status = await manager.get_memory_status()
                
                assert status['status'] == 'warning'
                
    @pytest.mark.asyncio
    async def test_memory_status_critical(self, manager):
        """Test status critical la memoria foarte înaltă"""
        with patch.object(manager.monitor, 'record_measurement', return_value=96.0):
            with patch.object(manager.monitor, 'get_memory_stats', return_value={}):
                
                status = await manager.get_memory_status()
                
                assert status['status'] == 'critical'
                
    def test_memory_allocation_with_weak_reference(self, manager):
        """Test alocările cu weak references"""
        test_obj = Mock()
        
        with patch.object(manager.monitor, 'record_measurement', return_value=50.0):
            result = manager.track_allocation(
                "weak_ref_test",
                5.0,
                MemoryPriority.MEDIUM,
                obj=test_obj
            )
            
            assert result is True
            assert "weak_ref_test" in manager.weak_references
            
        # Șterge obiectul și testează weak reference
        del test_obj
        
        manager._cleanup_dead_references()
        
        # Alocarea ar trebui să fie curățată automat
        assert "weak_ref_test" not in manager.allocations
        
    def test_background_cleanup_disabled_for_testing(self, manager):
        """Test că background cleanup nu interferează cu testele"""
        # Manager-ul ar trebui să aibă background cleanup oprit pentru testing
        assert manager.should_stop is True
        
    def test_stats_tracking(self, manager):
        """Test urmărirea statisticilor"""
        initial_stats = manager.stats.copy()
        
        # Simulează niște operațiuni
        with patch.object(manager.monitor, 'record_measurement', return_value=50.0):
            manager.track_allocation("test", 5.0, MemoryPriority.LOW)
            
        manager.release_allocation("test")
        
        # Statisticile ar trebui să fie actualizate
        assert manager.stats['allocations_tracked'] > initial_stats['allocations_tracked']


@pytest.mark.integration
class TestMemoryManagerIntegration:
    """Teste de integrare pentru MemoryManager"""
    
    @pytest.mark.asyncio
    async def test_memory_pressure_scenario(self):
        """Test scenariul de presiune pe memorie"""
        with patch('psutil.Process'):
            manager = MemoryManager(max_memory_mb=50)  # Limită mică pentru test
            manager.should_stop = True  # Oprește background processing
            
            try:
                # Simulează presiune pe memorie
                with patch.object(manager.monitor, 'record_measurement', return_value=45.0):  # 90% din 50MB
                    
                    # Adaugă multe alocări
                    for i in range(10):
                        manager.track_allocation(f"alloc_{i}", 2.0, MemoryPriority.LOW)
                        
                    # Verifică că cleanup-ul funcționează
                    freed = await manager.cleanup_memory(force=True)
                    
                    assert freed >= 0
                    assert manager.stats['cleanups_performed'] > 0
                    
            finally:
                manager.stop()
                
    @pytest.mark.asyncio 
    async def test_allocation_lifecycle(self):
        """Test ciclul complet de viață al unei alocări"""
        with patch('psutil.Process'):
            manager = MemoryManager(max_memory_mb=100)
            manager.should_stop = True
            
            try:
                callback_called = Mock()
                test_obj = Mock()
                
                with patch.object(manager.monitor, 'record_measurement', return_value=30.0):
                    # 1. Track allocation
                    result = manager.track_allocation(
                        "lifecycle_test",
                        10.0,
                        MemoryPriority.HIGH,
                        cleanup_callback=callback_called,
                        obj=test_obj
                    )
                    
                    assert result is True
                    
                    # 2. Verify tracking
                    assert "lifecycle_test" in manager.allocations
                    assert "lifecycle_test" in manager.weak_references
                    
                    # 3. Get status
                    status = await manager.get_memory_status()
                    assert status['tracked_allocations'] == 1
                    
                    # 4. Release allocation
                    manager.release_allocation("lifecycle_test")
                    
                    # 5. Verify cleanup
                    assert "lifecycle_test" not in manager.allocations
                    callback_called.assert_called_once()
                    
            finally:
                manager.stop()


class TestMemoryAllocation:
    """Test pentru dataclass MemoryAllocation"""
    
    def test_memory_allocation_creation(self):
        """Test crearea unei instanțe MemoryAllocation"""
        allocation = MemoryAllocation(
            id="test_alloc",
            size_mb=10.0,
            created_at=time.time(),
            last_accessed=time.time(),
            priority=MemoryPriority.HIGH
        )
        
        assert allocation.id == "test_alloc"
        assert allocation.size_mb == 10.0
        assert allocation.priority == MemoryPriority.HIGH
        assert allocation.metadata == {}  # Default empty dict
        
    def test_memory_allocation_with_metadata(self):
        """Test MemoryAllocation cu metadata"""
        metadata = {"source": "test", "type": "video"}
        
        allocation = MemoryAllocation(
            id="test_alloc",
            size_mb=5.0,
            created_at=time.time(),
            last_accessed=time.time(),
            priority=MemoryPriority.LOW,
            metadata=metadata
        )
        
        assert allocation.metadata == metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
