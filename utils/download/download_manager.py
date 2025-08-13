# utils/download/download_manager.py - Manager Universal pentru Descărcări
# Versiunea: 4.0.0 - Arhitectura Refactorizată

import asyncio
import aiohttp
import aiofiles
import logging
import time
import hashlib
import os
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse, unquote
import mimetypes
from collections import defaultdict, deque

try:
    from platforms.base.abstract_platform import (
        QualityLevel, MediaFormat, DownloadResult,
        PlatformError, DownloadError
    )
except ImportError:
    # Fallback pentru development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import (
        QualityLevel, MediaFormat, DownloadResult,
        PlatformError, DownloadError
    )

logger = logging.getLogger(__name__)

class DownloadStatus(Enum):
    """Statusurile unei descărcări"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class DownloadPriority(Enum):
    """Prioritățile descărcărilor"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class CompressionType(Enum):
    """Tipurile de compresie"""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "brotli"

@dataclass
class DownloadProgress:
    """Progresul unei descărcări"""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_bytes_per_sec: float = 0.0
    eta_seconds: float = 0.0
    percentage: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    def update(self, downloaded: int, total: int = None):
        """Actualizează progresul"""
        self.downloaded_bytes = downloaded
        if total is not None:
            self.total_bytes = total
        
        now = datetime.now()
        time_diff = (now - self.last_update).total_seconds()
        
        if time_diff > 0:
            bytes_diff = downloaded - getattr(self, '_last_downloaded', 0)
            self.speed_bytes_per_sec = bytes_diff / time_diff
            
            if self.total_bytes > 0:
                self.percentage = (downloaded / self.total_bytes) * 100
                remaining_bytes = self.total_bytes - downloaded
                if self.speed_bytes_per_sec > 0:
                    self.eta_seconds = remaining_bytes / self.speed_bytes_per_sec
        
        self._last_downloaded = downloaded
        self.last_update = now
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'downloaded_bytes': self.downloaded_bytes,
            'total_bytes': self.total_bytes,
            'speed_bytes_per_sec': self.speed_bytes_per_sec,
            'eta_seconds': self.eta_seconds,
            'percentage': self.percentage,
            'speed_human': self._format_speed(self.speed_bytes_per_sec),
            'eta_human': self._format_time(self.eta_seconds),
            'size_human': f"{self._format_bytes(self.downloaded_bytes)}/{self._format_bytes(self.total_bytes)}"
        }
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Formatează bytes în format human-readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
    
    def _format_speed(self, speed: float) -> str:
        """Formatează viteza în format human-readable"""
        return f"{self._format_bytes(speed)}/s"
    
    def _format_time(self, seconds: float) -> str:
        """Formatează timpul în format human-readable"""
        if seconds <= 0:
            return "Unknown"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

@dataclass
class DownloadConfig:
    """Configurația pentru descărcări"""
    max_concurrent_downloads: int = 3
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 300  # 5 minute
    chunk_size: int = 8192  # 8KB
    max_file_size: int = 1024 * 1024 * 1024  # 1GB
    download_directory: str = "downloads"
    temp_directory: str = "temp"
    user_agent: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    verify_ssl: bool = True
    follow_redirects: bool = True
    resume_downloads: bool = True
    auto_retry: bool = True
    compression: CompressionType = CompressionType.NONE
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None

@dataclass
class DownloadTask:
    """Task de descărcare"""
    id: str
    url: str
    filename: str
    output_path: str
    priority: DownloadPriority = DownloadPriority.NORMAL
    status: DownloadStatus = DownloadStatus.PENDING
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    metadata: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    temp_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'url': self.url,
            'filename': self.filename,
            'output_path': self.output_path,
            'priority': self.priority.value,
            'status': self.status.value,
            'progress': self.progress.to_dict(),
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }

class DownloadQueue:
    """Coadă de descărcări cu prioritizare"""
    
    def __init__(self):
        self.queues = {
            DownloadPriority.URGENT: deque(),
            DownloadPriority.HIGH: deque(),
            DownloadPriority.NORMAL: deque(),
            DownloadPriority.LOW: deque()
        }
        self.tasks: Dict[str, DownloadTask] = {}
        self._lock = asyncio.Lock()
    
    async def add_task(self, task: DownloadTask):
        """Adaugă un task în coadă"""
        async with self._lock:
            self.tasks[task.id] = task
            self.queues[task.priority].append(task.id)
            logger.debug(f"📥 Added download task {task.id} with priority {task.priority.name}")
    
    async def get_next_task(self) -> Optional[DownloadTask]:
        """Obține următorul task din coadă (cel cu prioritatea cea mai mare)"""
        async with self._lock:
            for priority in [DownloadPriority.URGENT, DownloadPriority.HIGH, 
                           DownloadPriority.NORMAL, DownloadPriority.LOW]:
                if self.queues[priority]:
                    task_id = self.queues[priority].popleft()
                    task = self.tasks.get(task_id)
                    if task and task.status == DownloadStatus.PENDING:
                        return task
            return None
    
    async def remove_task(self, task_id: str):
        """Elimină un task din coadă"""
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # Încearcă să elimine din toate cozile
                for queue in self.queues.values():
                    try:
                        queue.remove(task_id)
                    except ValueError:
                        pass
                del self.tasks[task_id]
                logger.debug(f"🗑️ Removed download task {task_id}")
    
    async def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Obține un task după ID"""
        async with self._lock:
            return self.tasks.get(task_id)
    
    async def get_all_tasks(self) -> List[DownloadTask]:
        """Obține toate task-urile"""
        async with self._lock:
            return list(self.tasks.values())
    
    async def get_pending_count(self) -> int:
        """Obține numărul de task-uri în așteptare"""
        async with self._lock:
            return sum(len(queue) for queue in self.queues.values())
    
    async def clear(self):
        """Curăță toate cozile"""
        async with self._lock:
            for queue in self.queues.values():
                queue.clear()
            self.tasks.clear()

class DownloadManager:
    """
    Manager centralizat pentru descărcări care gestionează cozi de prioritate,
    descărcări concurente, retry logic, progress tracking și resuming.
    """
    
    def __init__(self, config: Optional[DownloadConfig] = None):
        self.config = config or DownloadConfig()
        
        # Coadă de descărcări
        self.queue = DownloadQueue()
        
        # Task-uri active
        self.active_downloads: Dict[str, asyncio.Task] = {}
        
        # Statistici
        self.stats = {
            'total_downloads': 0,
            'completed_downloads': 0,
            'failed_downloads': 0,
            'cancelled_downloads': 0,
            'total_bytes_downloaded': 0,
            'average_speed': 0.0,
            'active_downloads': 0
        }
        
        # Callback-uri globale
        self.global_callbacks = {
            'progress': [],
            'completion': [],
            'error': []
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self._shutdown = False
        
        # Rate limiting
        self.rate_limiter = defaultdict(lambda: {'last_request': 0, 'requests': 0})
        
        # User agents pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Asigură-te că directoarele există
        self._ensure_directories()
        
        logger.info("📥 Download Manager initialized")
    
    def _ensure_directories(self):
        """Asigură-te că directoarele necesare există"""
        Path(self.config.download_directory).mkdir(parents=True, exist_ok=True)
        Path(self.config.temp_directory).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Inițializează managerul de descărcări"""
        logger.info("🚀 Starting Download Manager...")
        
        # Start background tasks
        await self._start_background_tasks()
        
        logger.info("✅ Download Manager initialized")
    
    async def _start_background_tasks(self):
        """Pornește task-urile de background"""
        # Task pentru procesarea cozii
        queue_processor = asyncio.create_task(self._process_download_queue())
        self.background_tasks.append(queue_processor)
        
        # Task pentru cleanup
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.background_tasks.append(cleanup_task)
        
        # Task pentru actualizarea statisticilor
        stats_task = asyncio.create_task(self._update_stats_periodically())
        self.background_tasks.append(stats_task)
        
        logger.info("🔄 Started download manager background tasks")
    
    async def _process_download_queue(self):
        """Procesează coada de descărcări"""
        while not self._shutdown:
            try:
                # Verifică dacă putem porni o nouă descărcare
                if len(self.active_downloads) < self.config.max_concurrent_downloads:
                    task = await self.queue.get_next_task()
                    if task:
                        await self._start_download(task)
                
                await asyncio.sleep(1)  # Verifică la fiecare secundă
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in download queue processor: {e}")
                await asyncio.sleep(5)
    
    async def _start_download(self, task: DownloadTask):
        """Pornește o descărcare"""
        task.status = DownloadStatus.DOWNLOADING
        task.started_at = datetime.now()
        
        # Creează task-ul de descărcare
        download_task = asyncio.create_task(self._download_file(task))
        self.active_downloads[task.id] = download_task
        
        logger.info(f"🚀 Started download: {task.filename}")
        
        # Adaugă callback pentru finalizare
        download_task.add_done_callback(lambda t: asyncio.create_task(self._on_download_complete(task.id)))
    
    async def _download_file(self, task: DownloadTask):
        """Descarcă un fișier"""
        try:
            # Pregătește headers
            headers = self.config.headers.copy()
            headers.update(task.headers)
            
            if 'User-Agent' not in headers:
                headers['User-Agent'] = self.config.user_agent or self.user_agents[0]
            
            # Verifică dacă putem resume descărcarea
            resume_pos = 0
            if self.config.resume_downloads and task.temp_file and os.path.exists(task.temp_file):
                resume_pos = os.path.getsize(task.temp_file)
                headers['Range'] = f'bytes={resume_pos}-'
                logger.info(f"🔄 Resuming download from byte {resume_pos}")
            
            # Configurează timeout
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                cookies=self.config.cookies
            ) as session:
                async with session.get(
                    task.url,
                    ssl=self.config.verify_ssl,
                    allow_redirects=self.config.follow_redirects,
                    proxy=self.config.proxy
                ) as response:
                    
                    # Verifică status code
                    if response.status not in [200, 206]:  # 206 pentru partial content
                        raise DownloadError(f"HTTP {response.status}: {response.reason}")
                    
                    # Obține informații despre fișier
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        total_size = int(content_length) + resume_pos
                        task.progress.total_bytes = total_size
                    
                    # Verifică dimensiunea maximă
                    if task.progress.total_bytes > self.config.max_file_size:
                        raise DownloadError(f"File too large: {task.progress.total_bytes} bytes")
                    
                    # Determină numele fișierului temporar
                    if not task.temp_file:
                        task.temp_file = os.path.join(
                            self.config.temp_directory,
                            f"{task.id}.tmp"
                        )
                    
                    # Descarcă fișierul
                    mode = 'ab' if resume_pos > 0 else 'wb'
                    async with aiofiles.open(task.temp_file, mode) as file:
                        downloaded = resume_pos
                        
                        async for chunk in response.content.iter_chunked(self.config.chunk_size):
                            if task.status == DownloadStatus.CANCELLED:
                                raise asyncio.CancelledError("Download cancelled")
                            
                            if task.status == DownloadStatus.PAUSED:
                                # Așteaptă până când descărcarea este resumed
                                while task.status == DownloadStatus.PAUSED:
                                    await asyncio.sleep(1)
                            
                            await file.write(chunk)
                            downloaded += len(chunk)
                            
                            # Actualizează progresul
                            task.progress.update(downloaded, task.progress.total_bytes)
                            
                            # Apelează callback-ul de progres
                            await self._call_progress_callbacks(task)
                    
                    # Mută fișierul la destinația finală
                    final_path = os.path.join(task.output_path, task.filename)
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    
                    if os.path.exists(final_path):
                        # Generează nume unic
                        base, ext = os.path.splitext(final_path)
                        counter = 1
                        while os.path.exists(f"{base}_{counter}{ext}"):
                            counter += 1
                        final_path = f"{base}_{counter}{ext}"
                        task.filename = os.path.basename(final_path)
                    
                    os.rename(task.temp_file, final_path)
                    task.temp_file = None
                    
                    # Marchează ca completat
                    task.status = DownloadStatus.COMPLETED
                    task.completed_at = datetime.now()
                    
                    logger.info(f"✅ Download completed: {task.filename}")
                    
        except asyncio.CancelledError:
            task.status = DownloadStatus.CANCELLED
            logger.info(f"🛑 Download cancelled: {task.filename}")
            raise
        except Exception as e:
            task.error_message = str(e)
            
            if self.config.auto_retry and task.retry_count < self.config.max_retries:
                task.retry_count += 1
                task.status = DownloadStatus.RETRYING
                
                # Așteaptă înainte de retry
                delay = self.config.retry_delay * (2 ** (task.retry_count - 1))  # Exponential backoff
                await asyncio.sleep(delay)
                
                logger.warning(f"🔄 Retrying download ({task.retry_count}/{self.config.max_retries}): {task.filename}")
                
                # Repornește descărcarea
                await self._start_download(task)
            else:
                task.status = DownloadStatus.FAILED
                logger.error(f"❌ Download failed: {task.filename} - {e}")
                
                # Apelează callback-ul de eroare
                await self._call_error_callbacks(task, e)
    
    async def _on_download_complete(self, task_id: str):
        """Callback pentru finalizarea unei descărcări"""
        if task_id in self.active_downloads:
            del self.active_downloads[task_id]
        
        task = await self.queue.get_task(task_id)
        if task:
            # Actualizează statisticile
            if task.status == DownloadStatus.COMPLETED:
                self.stats['completed_downloads'] += 1
                self.stats['total_bytes_downloaded'] += task.progress.downloaded_bytes
                
                # Apelează callback-ul de completare
                await self._call_completion_callbacks(task)
            elif task.status == DownloadStatus.FAILED:
                self.stats['failed_downloads'] += 1
            elif task.status == DownloadStatus.CANCELLED:
                self.stats['cancelled_downloads'] += 1
    
    async def _call_progress_callbacks(self, task: DownloadTask):
        """Apelează callback-urile de progres"""
        callbacks = self.global_callbacks['progress'].copy()
        if self.config.progress_callback:
            callbacks.append(self.config.progress_callback)
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"❌ Progress callback failed: {e}")
    
    async def _call_completion_callbacks(self, task: DownloadTask):
        """Apelează callback-urile de completare"""
        callbacks = self.global_callbacks['completion'].copy()
        if self.config.completion_callback:
            callbacks.append(self.config.completion_callback)
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"❌ Completion callback failed: {e}")
    
    async def _call_error_callbacks(self, task: DownloadTask, error: Exception):
        """Apelează callback-urile de eroare"""
        callbacks = self.global_callbacks['error'].copy()
        if self.config.error_callback:
            callbacks.append(self.config.error_callback)
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task, error)
                else:
                    callback(task, error)
            except Exception as e:
                logger.error(f"❌ Error callback failed: {e}")
    
    async def _periodic_cleanup(self):
        """Cleanup periodic al fișierelor temporare și task-urilor vechi"""
        while not self._shutdown:
            try:
                await asyncio.sleep(3600)  # Cleanup la fiecare oră
                await self._cleanup_temp_files()
                await self._cleanup_old_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic cleanup: {e}")
    
    async def _cleanup_temp_files(self):
        """Curăță fișierele temporare orfane"""
        temp_dir = Path(self.config.temp_directory)
        if not temp_dir.exists():
            return
        
        active_temp_files = set()
        all_tasks = await self.queue.get_all_tasks()
        
        for task in all_tasks:
            if task.temp_file:
                active_temp_files.add(task.temp_file)
        
        cleaned_count = 0
        for temp_file in temp_dir.glob('*.tmp'):
            if str(temp_file) not in active_temp_files:
                try:
                    # Verifică dacă fișierul este mai vechi de 24 ore
                    if time.time() - temp_file.stat().st_mtime > 86400:
                        temp_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete temp file {temp_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} orphaned temp files")
    
    async def _cleanup_old_tasks(self):
        """Curăță task-urile vechi completate"""
        cutoff_time = datetime.now() - timedelta(days=7)  # Păstrează 7 zile
        
        all_tasks = await self.queue.get_all_tasks()
        old_tasks = []
        
        for task in all_tasks:
            if (task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED] and
                task.completed_at and task.completed_at < cutoff_time):
                old_tasks.append(task.id)
        
        for task_id in old_tasks:
            await self.queue.remove_task(task_id)
        
        if old_tasks:
            logger.info(f"🧹 Cleaned up {len(old_tasks)} old completed tasks")
    
    async def _update_stats_periodically(self):
        """Actualizează statisticile periodic"""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # Actualizează la fiecare minut
                await self._update_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error updating stats: {e}")
    
    async def _update_stats(self):
        """Actualizează statisticile"""
        self.stats['active_downloads'] = len(self.active_downloads)
        
        # Calculează viteza medie
        all_tasks = await self.queue.get_all_tasks()
        active_speeds = []
        
        for task in all_tasks:
            if task.status == DownloadStatus.DOWNLOADING and task.progress.speed_bytes_per_sec > 0:
                active_speeds.append(task.progress.speed_bytes_per_sec)
        
        if active_speeds:
            self.stats['average_speed'] = sum(active_speeds) / len(active_speeds)
        else:
            self.stats['average_speed'] = 0.0
    
    async def add_download(self, url: str, filename: str, output_path: str = None,
                          priority: DownloadPriority = DownloadPriority.NORMAL,
                          headers: Dict[str, str] = None,
                          metadata: Dict[str, Any] = None) -> str:
        """
        Adaugă o nouă descărcare în coadă.
        
        Args:
            url: URL-ul de descărcat
            filename: Numele fișierului
            output_path: Calea de output (default: config.download_directory)
            priority: Prioritatea descărcării
            headers: Headers suplimentare
            metadata: Metadata suplimentare
        
        Returns:
            ID-ul task-ului de descărcare
        """
        # Generează ID unic
        task_id = hashlib.md5(f"{url}{filename}{time.time()}".encode()).hexdigest()
        
        # Pregătește calea de output
        if output_path is None:
            output_path = self.config.download_directory
        
        # Creează task-ul
        task = DownloadTask(
            id=task_id,
            url=url,
            filename=filename,
            output_path=output_path,
            priority=priority,
            headers=headers or {},
            metadata=metadata or {}
        )
        
        # Adaugă în coadă
        await self.queue.add_task(task)
        
        self.stats['total_downloads'] += 1
        
        logger.info(f"📥 Added download: {filename} (ID: {task_id})")
        return task_id
    
    async def pause_download(self, task_id: str) -> bool:
        """Pune în pauză o descărcare"""
        task = await self.queue.get_task(task_id)
        if task and task.status == DownloadStatus.DOWNLOADING:
            task.status = DownloadStatus.PAUSED
            logger.info(f"⏸️ Paused download: {task.filename}")
            return True
        return False
    
    async def resume_download(self, task_id: str) -> bool:
        """Reia o descărcare pusă în pauză"""
        task = await self.queue.get_task(task_id)
        if task and task.status == DownloadStatus.PAUSED:
            task.status = DownloadStatus.DOWNLOADING
            logger.info(f"▶️ Resumed download: {task.filename}")
            return True
        return False
    
    async def cancel_download(self, task_id: str) -> bool:
        """Anulează o descărcare"""
        task = await self.queue.get_task(task_id)
        if not task:
            return False
        
        # Anulează task-ul activ dacă există
        if task_id in self.active_downloads:
            self.active_downloads[task_id].cancel()
        
        # Marchează ca anulat
        task.status = DownloadStatus.CANCELLED
        
        # Șterge fișierul temporar
        if task.temp_file and os.path.exists(task.temp_file):
            try:
                os.remove(task.temp_file)
            except Exception as e:
                logger.warning(f"⚠️ Could not delete temp file: {e}")
        
        logger.info(f"🛑 Cancelled download: {task.filename}")
        return True
    
    async def get_download_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obține statusul unei descărcări"""
        task = await self.queue.get_task(task_id)
        return task.to_dict() if task else None
    
    async def get_all_downloads(self) -> List[Dict[str, Any]]:
        """Obține toate descărcările"""
        tasks = await self.queue.get_all_tasks()
        return [task.to_dict() for task in tasks]
    
    async def get_active_downloads(self) -> List[Dict[str, Any]]:
        """Obține descărcările active"""
        tasks = await self.queue.get_all_tasks()
        active_tasks = [task for task in tasks if task.status == DownloadStatus.DOWNLOADING]
        return [task.to_dict() for task in active_tasks]
    
    def add_progress_callback(self, callback: Callable):
        """Adaugă un callback pentru progres"""
        self.global_callbacks['progress'].append(callback)
    
    def add_completion_callback(self, callback: Callable):
        """Adaugă un callback pentru completare"""
        self.global_callbacks['completion'].append(callback)
    
    def add_error_callback(self, callback: Callable):
        """Adaugă un callback pentru erori"""
        self.global_callbacks['error'].append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obține statisticile managerului"""
        return self.stats.copy()
    
    async def clear_completed_downloads(self):
        """Curăță toate descărcările completate"""
        tasks = await self.queue.get_all_tasks()
        completed_tasks = [task.id for task in tasks if task.status == DownloadStatus.COMPLETED]
        
        for task_id in completed_tasks:
            await self.queue.remove_task(task_id)
        
        logger.info(f"🧹 Cleared {len(completed_tasks)} completed downloads")
    
    async def shutdown(self):
        """Oprește managerul de descărcări"""
        logger.info("🛑 Shutting down Download Manager...")
        
        self._shutdown = True
        
        # Anulează toate descărcările active
        for task_id, download_task in self.active_downloads.items():
            download_task.cancel()
        
        # Anulează task-urile de background
        for task in self.background_tasks:
            task.cancel()
        
        # Așteaptă ca task-urile să se termine
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("✅ Download Manager shutdown complete")
    
    def __str__(self) -> str:
        active = len(self.active_downloads)
        total = self.stats['total_downloads']
        return f"DownloadManager(active={active}, total={total})"
    
    def __repr__(self) -> str:
        return (f"DownloadManager(active={len(self.active_downloads)}, "
                f"max_concurrent={self.config.max_concurrent_downloads}, "
                f"total={self.stats['total_downloads']})")


# Singleton instance pentru utilizare globală
download_manager = DownloadManager()