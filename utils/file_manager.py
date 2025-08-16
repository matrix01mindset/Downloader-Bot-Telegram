# utils/file_manager.py - File Manager Avansat
# Versiunea: 3.0.0 - Arhitectura Nouă

import os
import asyncio
import tempfile
import shutil
import time
import hashlib
import mimetypes
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field

from utils.monitoring import monitoring, trace_operation

logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """Informații despre un fișier gestionat"""
    path: str
    size: int
    created_at: float
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FileManagerStats:
    """Statistici pentru file manager"""
    files_created: int = 0
    files_deleted: int = 0
    bytes_processed: int = 0
    cleanup_runs: int = 0
    errors_count: int = 0
    
class FileManager:
    """
    Manager avansat pentru fișiere temporare
    Gestionează cleanup automat, organizare și monitorizare
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Configurări
        self.temp_dir = config.get('temp_dir', '/tmp')
        self.max_temp_files = config.get('max_temp_files', 100)
        self.cleanup_older_than = config.get('cleanup_older_than', 300)  # 5 minute
        self.max_file_size = config.get('max_file_size_mb', 45) * 1024 * 1024  # MB to bytes
        self.allowed_extensions = config.get('allowed_extensions', [
            '.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v', '.3gp'
        ])
        
        # Directorul principal pentru fișiere temporare
        self.base_temp_dir = self._ensure_temp_directory()
        
        # Tracking fișiere active
        self.active_files: Dict[str, FileInfo] = {}
        
        # Statistici
        self.stats = FileManagerStats()
        
        # Task pentru cleanup periodic
        self.cleanup_task = None
        self.cleanup_interval = config.get('cleanup_interval', 30)  # secunde
        
        logger.info(f"✅ File Manager initialized - Base dir: {self.base_temp_dir}")
        
    def _ensure_temp_directory(self) -> str:
        """Asigură că directorul temporar există și este accesibil"""
        try:
            # Încearcă directorul specificat
            if self.temp_dir and os.path.exists(self.temp_dir):
                test_dir = os.path.join(self.temp_dir, 'telegram_bot_temp')
            else:
                # Fallback la directorul temporar sistem
                test_dir = os.path.join(tempfile.gettempdir(), 'telegram_bot_temp')
                
            # Creează directorul cu subdirectoare
            os.makedirs(test_dir, exist_ok=True)
            
            # Test de scriere
            test_file = os.path.join(test_dir, '.write_test')
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('test')
            os.remove(test_file)
            
            logger.info(f"Temp directory verified: {test_dir}")
            return test_dir
            
        except Exception as e:
            logger.error(f"Error setting up temp directory: {e}")
            # Ultimul fallback - creează în directorul curent
            fallback_dir = os.path.join(os.getcwd(), 'temp_files')
            os.makedirs(fallback_dir, exist_ok=True)
            logger.warning(f"Using fallback temp directory: {fallback_dir}")
            return fallback_dir
            
    def _generate_safe_filename(self, original_name: str, video_id: str = None) -> str:
        """Generează nume sigur pentru fișier"""
        try:
            # Extrage extensia
            _, ext = os.path.splitext(original_name)
            if not ext:
                ext = '.mp4'  # default extension
                
            # Verifică extensia
            if ext.lower() not in self.allowed_extensions:
                ext = '.mp4'
                
            # Generează nume bazat pe ID-ul video sau hash
            if video_id:
                safe_name = self._sanitize_filename(video_id)
            else:
                # Generează hash din numele original și timestamp
                hash_input = f"{original_name}_{time.time()}"
                safe_name = hashlib.md5(hash_input.encode()).hexdigest()[:12]
                
            return f"{safe_name}{ext}"
            
        except Exception as e:
            logger.warning(f"Error generating safe filename: {e}")
            # Fallback extreme
            timestamp = int(time.time())
            return f"video_{timestamp}.mp4"
            
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitizează numele fișierului"""
        # Înlocuiește caractere problematice
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Limitează lungimea
        if len(filename) > 50:
            filename = filename[:50]
            
        # Elimină spații multiple și trim
        filename = ' '.join(filename.split())
        
        return filename or 'unnamed'
        
    @trace_operation("file_manager.create_temp_file")
    async def create_temp_file(self, prefix: str = 'video', 
                             suffix: str = '.mp4',
                             video_id: str = None) -> str:
        """Creează un fișier temporar și îl înregistrează pentru tracking"""
        try:
            # Verifică limita de fișiere
            if len(self.active_files) >= self.max_temp_files:
                logger.warning("Max temp files reached, triggering cleanup")
                await self.cleanup_old_files(force=True)
                
            # Generează numele fișierului
            if video_id:
                filename = self._generate_safe_filename(f"{prefix}_{video_id}", video_id)
            else:
                timestamp = int(time.time())
                filename = self._generate_safe_filename(f"{prefix}_{timestamp}")
                
            # Creează calea completă
            file_path = os.path.join(self.base_temp_dir, filename)
            
            # Verifică dacă fișierul există deja
            counter = 1
            original_path = file_path
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_path)
                file_path = f"{name}_{counter}{ext}"
                counter += 1
                
            # Creează fișierul
            Path(file_path).touch()
            
            # Înregistrează fișierul
            file_info = FileInfo(
                path=file_path,
                size=0,
                created_at=time.time(),
                mime_type=mimetypes.guess_type(file_path)[0]
            )
            
            self.active_files[file_path] = file_info
            self.stats.files_created += 1
            
            logger.debug(f"Created temp file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error creating temp file: {e}")
            self.stats.errors_count += 1
            raise
            
    @trace_operation("file_manager.register_file")
    async def register_file(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Înregistrează un fișier existent pentru tracking"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False
                
            # Obține informații despre fișier
            stat_info = os.stat(file_path)
            file_size = stat_info.st_size
            
            # Verifică dimensiunea
            if file_size > self.max_file_size:
                logger.warning(f"File too large: {file_size} bytes > {self.max_file_size}")
                return False
                
            # Calculează checksum pentru fișiere mari
            checksum = None
            if file_size > 1024 * 1024:  # > 1MB
                checksum = await self._calculate_checksum(file_path)
                
            # Înregistrează fișierul
            file_info = FileInfo(
                path=file_path,
                size=file_size,
                created_at=time.time(),
                mime_type=mimetypes.guess_type(file_path)[0],
                checksum=checksum,
                metadata=metadata or {}
            )
            
            self.active_files[file_path] = file_info
            self.stats.bytes_processed += file_size
            
            logger.debug(f"Registered file: {file_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error registering file {file_path}: {e}")
            self.stats.errors_count += 1
            return False
            
    async def _calculate_checksum(self, file_path: str) -> Optional[str]:
        """Calculează checksum MD5 pentru un fișier"""
        try:
            hash_md5 = hashlib.md5()
            
            async def read_file():
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hash_md5.update(chunk)
                return hash_md5.hexdigest()
                
            return await asyncio.to_thread(read_file)
            
        except Exception as e:
            logger.debug(f"Error calculating checksum for {file_path}: {e}")
            return None
            
    @trace_operation("file_manager.cleanup_file")
    async def cleanup_file(self, file_path: str) -> bool:
        """Curăță un fișier specific"""
        try:
            # Încearcă să ștergi fișierul
            if os.path.exists(file_path):
                # Pentru Windows, încearcă să închidă handle-urile
                if os.name == 'nt':
                    try:
                        # Forțează garbage collection
                        import gc
                        gc.collect()
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.debug(f"Nu s-a putut forța garbage collection: {e}")
                        
                await asyncio.to_thread(os.remove, file_path)
                logger.debug(f"Deleted file: {file_path}")
                
            # Elimină din tracking
            if file_path in self.active_files:
                file_info = self.active_files.pop(file_path)
                self.stats.files_deleted += 1
                
                if monitoring:
                    monitoring.record_metric("file_manager.file_deleted", 1)
                    monitoring.record_metric("file_manager.bytes_cleaned", file_info.size)
                    
            return True
            
        except PermissionError as e:
            logger.warning(f"Permission denied deleting {file_path}: {e}")
            # Încearcă din nou după o pauză
            await asyncio.sleep(1)
            try:
                await asyncio.to_thread(os.remove, file_path)
                if file_path in self.active_files:
                    self.active_files.pop(file_path)
                return True
            except Exception as e:
                logger.error(f"Failed to delete {file_path} after retry: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")
            self.stats.errors_count += 1
            return False
            
    @trace_operation("file_manager.cleanup_old_files")
    async def cleanup_old_files(self, force: bool = False) -> int:
        """Curăță fișierele vechi"""
        try:
            current_time = time.time()
            cutoff_time = current_time - self.cleanup_older_than
            
            files_to_cleanup = []
            
            # Identifică fișierele de curățat
            for file_path, file_info in list(self.active_files.items()):
                should_cleanup = force or file_info.created_at < cutoff_time
                
                if should_cleanup:
                    files_to_cleanup.append(file_path)
                    
            # Curăță fișierele
            cleaned_count = 0
            for file_path in files_to_cleanup:
                if await self.cleanup_file(file_path):
                    cleaned_count += 1
                    
            # Curăță și fișierele orfane din directorul temp
            orphaned_cleaned = await self._cleanup_orphaned_files()
            
            self.stats.cleanup_runs += 1
            total_cleaned = cleaned_count + orphaned_cleaned
            
            if total_cleaned > 0:
                logger.info(f"Cleanup completed: {total_cleaned} files removed "
                          f"({cleaned_count} tracked + {orphaned_cleaned} orphaned)")
                          
            if monitoring:
                monitoring.record_metric("file_manager.cleanup_runs", 1)
                monitoring.record_metric("file_manager.files_cleaned", total_cleaned)
                
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            self.stats.errors_count += 1
            return 0
            
    async def _cleanup_orphaned_files(self) -> int:
        """Curăță fișierele orfane din directorul temp"""
        try:
            if not os.path.exists(self.base_temp_dir):
                return 0
                
            current_time = time.time()
            cutoff_time = current_time - (self.cleanup_older_than * 2)  # Dublu timeout pentru orfane
            
            cleaned_count = 0
            
            # Scanează directorul
            for filename in os.listdir(self.base_temp_dir):
                file_path = os.path.join(self.base_temp_dir, filename)
                
                # Skip dacă e deja tracked
                if file_path in self.active_files:
                    continue
                    
                try:
                    # Verifică vârsta fișierului
                    stat_info = os.stat(file_path)
                    if stat_info.st_mtime < cutoff_time:
                        await asyncio.to_thread(os.remove, file_path)
                        cleaned_count += 1
                        logger.debug(f"Removed orphaned file: {file_path}")
                        
                except Exception as e:
                    logger.debug(f"Error removing orphaned file {file_path}: {e}")
                    
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning orphaned files: {e}")
            return 0
            
    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """Obține informații despre un fișier tracked"""
        return self.active_files.get(file_path)
        
    async def update_file_size(self, file_path: str) -> bool:
        """Actualizează dimensiunea unui fișier tracked"""
        try:
            if file_path not in self.active_files:
                return False
                
            if os.path.exists(file_path):
                new_size = os.path.getsize(file_path)
                self.active_files[file_path].size = new_size
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error updating file size for {file_path}: {e}")
            return False
            
    def get_temp_dir(self) -> str:
        """Returnează directorul temporar de bază"""
        return self.base_temp_dir
        
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statisticile file manager-ului"""
        active_files_size = sum(info.size for info in self.active_files.values())
        
        return {
            'active_files_count': len(self.active_files),
            'active_files_size_mb': round(active_files_size / (1024 * 1024), 2),
            'files_created': self.stats.files_created,
            'files_deleted': self.stats.files_deleted,
            'bytes_processed_mb': round(self.stats.bytes_processed / (1024 * 1024), 2),
            'cleanup_runs': self.stats.cleanup_runs,
            'errors_count': self.stats.errors_count,
            'temp_dir': self.base_temp_dir,
            'max_temp_files': self.max_temp_files,
            'cleanup_older_than': self.cleanup_older_than
        }
        
    async def start_periodic_cleanup(self):
        """Pornește task-ul de cleanup periodic"""
        if self.cleanup_task is not None:
            return
            
        async def periodic_cleanup():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval)
                    await self.cleanup_old_files()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
                    await asyncio.sleep(60)  # Back off on error
                    
        self.cleanup_task = asyncio.create_task(periodic_cleanup())
        logger.info(f"Started periodic cleanup task (interval: {self.cleanup_interval}s)")
        
    async def stop_periodic_cleanup(self):
        """Oprește task-ul de cleanup periodic"""
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("Stopped periodic cleanup task")
            
    async def cleanup_all(self):
        """Curăță toate fișierele și oprește task-urile"""
        logger.info("Starting full cleanup...")
        
        # Oprește task-ul periodic
        await self.stop_periodic_cleanup()
        
        # Curăță toate fișierele
        all_files = list(self.active_files.keys())
        cleaned_count = 0
        
        for file_path in all_files:
            if await self.cleanup_file(file_path):
                cleaned_count += 1
                
        # Încearcă să ștergi directorul temp dacă e gol
        try:
            if os.path.exists(self.base_temp_dir):
                remaining_files = os.listdir(self.base_temp_dir)
                if not remaining_files:
                    os.rmdir(self.base_temp_dir)
                    logger.info(f"Removed empty temp directory: {self.base_temp_dir}")
                else:
                    logger.info(f"Temp directory not empty: {len(remaining_files)} files remaining")
        except Exception as e:
            logger.debug(f"Could not remove temp directory: {e}")
            
        logger.info(f"Full cleanup completed: {cleaned_count} files removed")
        return cleaned_count
        
    def __del__(self):
        """Destructor - curăță resursele"""
        try:
            if hasattr(self, 'cleanup_task') and self.cleanup_task and not self.cleanup_task.done():
                self.cleanup_task.cancel()
        except Exception as e:
            logger.debug(f"Eroare la curățarea resurselor în destructor: {e}")
