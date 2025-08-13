# core/refactored/download_orchestrator.py - Orchestrator pentru Descărcări
# Versiunea: 4.0.0 - Arhitectura Refactorizată

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

try:
    from platforms.base.abstract_platform import (
        AbstractPlatform, PlatformCapability, ContentType, 
        VideoMetadata, DownloadResult, QualityLevel,
        PlatformError, UnsupportedURLError, DownloadError
    )
    from core.refactored.platform_registry import platform_registry, PlatformStatus
except ImportError:
    # Fallback pentru development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import (
        AbstractPlatform, PlatformCapability, ContentType,
        VideoMetadata, DownloadResult, QualityLevel,
        PlatformError, UnsupportedURLError, DownloadError
    )
    from core.refactored.platform_registry import platform_registry, PlatformStatus

logger = logging.getLogger(__name__)

class DownloadStatus(Enum):
    """Statusurile unei descărcări"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTING_METADATA = "extracting_metadata"
    DOWNLOADING = "downloading"
    POST_PROCESSING = "post_processing"
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

@dataclass
class DownloadRequest:
    """Request pentru descărcare"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    quality: Optional[QualityLevel] = None
    format_preference: Optional[str] = None
    output_path: Optional[str] = None
    priority: DownloadPriority = DownloadPriority.NORMAL
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    
    # Callback-uri pentru progres
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configurări avansate
    max_retries: int = 3
    timeout: int = 300  # 5 minute
    custom_headers: Optional[Dict[str, str]] = None
    extract_audio_only: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertește request-ul la dicționar pentru logging"""
        return {
            'id': self.id,
            'url': self.url,
            'quality': self.quality.value if self.quality else None,
            'format_preference': self.format_preference,
            'priority': self.priority.value,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'created_at': self.created_at.isoformat(),
            'max_retries': self.max_retries,
            'timeout': self.timeout
        }

@dataclass
class DownloadJob:
    """Job de descărcare cu status și metadata"""
    request: DownloadRequest
    status: DownloadStatus = DownloadStatus.PENDING
    platform_name: Optional[str] = None
    platform_instance: Optional[AbstractPlatform] = None
    
    # Progress tracking
    progress_percentage: float = 0.0
    current_step: str = ""
    estimated_time_remaining: Optional[int] = None
    
    # Rezultate
    metadata: Optional[VideoMetadata] = None
    download_result: Optional[DownloadResult] = None
    
    # Error handling
    error: Optional[Exception] = None
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    
    # Performance metrics
    queue_time: Optional[float] = None
    processing_time: Optional[float] = None
    download_speed: Optional[float] = None
    
    def update_progress(self, percentage: float, step: str = "", eta: Optional[int] = None):
        """Actualizează progresul job-ului"""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        if step:
            self.current_step = step
        if eta is not None:
            self.estimated_time_remaining = eta
        
        # Apelează callback-ul de progres dacă există
        if self.request.progress_callback:
            try:
                self.request.progress_callback({
                    'job_id': self.request.id,
                    'progress': self.progress_percentage,
                    'step': self.current_step,
                    'eta': self.estimated_time_remaining
                })
            except Exception as e:
                logger.warning(f"⚠️ Progress callback failed for {self.request.id}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertește job-ul la dicționar pentru API"""
        return {
            'id': self.request.id,
            'url': self.request.url,
            'status': self.status.value,
            'platform': self.platform_name,
            'progress': self.progress_percentage,
            'current_step': self.current_step,
            'eta': self.estimated_time_remaining,
            'retry_count': self.retry_count,
            'created_at': self.request.created_at.isoformat(),
            'started_at': self.request.started_at.isoformat() if self.request.started_at else None,
            'completed_at': self.request.completed_at.isoformat() if self.request.completed_at else None,
            'error': str(self.error) if self.error else None,
            'metadata': self.metadata.to_dict() if self.metadata else None,
            'download_result': self.download_result.to_dict() if self.download_result else None
        }

class DownloadOrchestrator:
    """
    Orchestrator centralizat pentru gestionarea descărcărilor.
    Coordonează între Platform Registry, queue management, retry logic,
    progress tracking și resource management.
    """
    
    def __init__(self, max_concurrent_downloads: int = 5, 
                 max_queue_size: int = 100,
                 default_timeout: int = 300):
        
        # Queue management
        self.download_queues: Dict[DownloadPriority, deque] = {
            priority: deque() for priority in DownloadPriority
        }
        self.max_queue_size = max_queue_size
        self.total_queued = 0
        
        # Active downloads
        self.active_downloads: Dict[str, DownloadJob] = {}
        self.max_concurrent_downloads = max_concurrent_downloads
        self.download_semaphore = asyncio.Semaphore(max_concurrent_downloads)
        
        # Job tracking
        self.completed_jobs: Dict[str, DownloadJob] = {}
        self.failed_jobs: Dict[str, DownloadJob] = {}
        self.job_history_limit = 1000
        
        # Configuration
        self.default_timeout = default_timeout
        self.retry_delays = [1, 2, 5, 10, 30]  # Exponential backoff
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'completed_downloads': 0,
            'failed_downloads': 0,
            'cancelled_downloads': 0,
            'retries_performed': 0,
            'average_download_time': 0.0,
            'average_queue_time': 0.0,
            'peak_concurrent_downloads': 0,
            'total_bytes_downloaded': 0
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.queue_processor_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Event hooks
        self.event_hooks: Dict[str, List[Callable]] = defaultdict(list)
        
        logger.info("🎭 Download Orchestrator initialized")
    
    async def initialize(self):
        """Inițializează orchestrator-ul"""
        logger.info("🚀 Starting Download Orchestrator...")
        
        # Asigură-te că Platform Registry este inițializat
        if not platform_registry.platforms:
            await platform_registry.initialize()
        
        # Start queue processor
        self.queue_processor_task = asyncio.create_task(self._process_download_queue())
        self.background_tasks.append(self.queue_processor_task)
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.background_tasks.append(cleanup_task)
        
        logger.info("✅ Download Orchestrator initialized")
    
    async def submit_download(self, request: DownloadRequest) -> str:
        """Trimite o cerere de descărcare în queue"""
        # Validare request
        if not request.url:
            raise ValueError("URL is required")
        
        # Verifică dacă queue-ul nu este plin
        if self.total_queued >= self.max_queue_size:
            raise RuntimeError(f"Download queue is full (max: {self.max_queue_size})")
        
        # Găsește platforma potrivită
        platform_name = platform_registry.find_platform_for_url(request.url)
        if not platform_name:
            raise UnsupportedURLError(f"No platform supports URL: {request.url}")
        
        # Creează job-ul
        job = DownloadJob(
            request=request,
            platform_name=platform_name,
            status=DownloadStatus.QUEUED
        )
        
        # Adaugă în queue bazat pe prioritate
        self.download_queues[request.priority].append(job)
        self.total_queued += 1
        self.stats['total_requests'] += 1
        
        # Trigger event
        await self._trigger_event('download_queued', job)
        
        logger.info(f"📥 Queued download {request.id} for {platform_name} (priority: {request.priority.name})")
        return request.id
    
    async def get_download_status(self, download_id: str) -> Optional[Dict[str, Any]]:
        """Obține statusul unei descărcări"""
        # Caută în active downloads
        if download_id in self.active_downloads:
            return self.active_downloads[download_id].to_dict()
        
        # Caută în completed jobs
        if download_id in self.completed_jobs:
            return self.completed_jobs[download_id].to_dict()
        
        # Caută în failed jobs
        if download_id in self.failed_jobs:
            return self.failed_jobs[download_id].to_dict()
        
        # Caută în queue
        for priority_queue in self.download_queues.values():
            for job in priority_queue:
                if job.request.id == download_id:
                    return job.to_dict()
        
        return None
    
    async def cancel_download(self, download_id: str) -> bool:
        """Anulează o descărcare"""
        # Caută în active downloads
        if download_id in self.active_downloads:
            job = self.active_downloads[download_id]
            job.status = DownloadStatus.CANCELLED
            job.request.completed_at = datetime.now()
            
            # Mută la failed jobs pentru tracking
            self.failed_jobs[download_id] = job
            del self.active_downloads[download_id]
            
            self.stats['cancelled_downloads'] += 1
            await self._trigger_event('download_cancelled', job)
            
            logger.info(f"❌ Cancelled active download {download_id}")
            return True
        
        # Caută în queue și elimină
        for priority_queue in self.download_queues.values():
            for i, job in enumerate(priority_queue):
                if job.request.id == download_id:
                    job.status = DownloadStatus.CANCELLED
                    job.request.completed_at = datetime.now()
                    
                    # Elimină din queue
                    del priority_queue[i]
                    self.total_queued -= 1
                    
                    # Adaugă la failed jobs
                    self.failed_jobs[download_id] = job
                    
                    self.stats['cancelled_downloads'] += 1
                    await self._trigger_event('download_cancelled', job)
                    
                    logger.info(f"❌ Cancelled queued download {download_id}")
                    return True
        
        return False
    
    async def _process_download_queue(self):
        """Procesează queue-ul de descărcări"""
        while not self._shutdown:
            try:
                # Găsește următorul job cu prioritate mare
                job = self._get_next_job()
                if not job:
                    await asyncio.sleep(1)
                    continue
                
                # Așteaptă să fie disponibil un slot
                await self.download_semaphore.acquire()
                
                try:
                    # Procesează job-ul
                    task = asyncio.create_task(self._process_download_job(job))
                    # Nu așteaptă task-ul să se termine pentru a procesa următorul
                    
                except Exception as e:
                    logger.error(f"❌ Error starting download job {job.request.id}: {e}")
                    self.download_semaphore.release()
                    await self._handle_job_failure(job, e)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in queue processor: {e}")
                await asyncio.sleep(5)
    
    def _get_next_job(self) -> Optional[DownloadJob]:
        """Obține următorul job din queue bazat pe prioritate"""
        # Procesează în ordinea priorității (URGENT -> HIGH -> NORMAL -> LOW)
        for priority in [DownloadPriority.URGENT, DownloadPriority.HIGH, 
                        DownloadPriority.NORMAL, DownloadPriority.LOW]:
            queue = self.download_queues[priority]
            if queue:
                job = queue.popleft()
                self.total_queued -= 1
                return job
        
        return None
    
    async def _process_download_job(self, job: DownloadJob):
        """Procesează un job de descărcare"""
        download_id = job.request.id
        start_time = time.time()
        
        try:
            # Marchează job-ul ca activ
            job.status = DownloadStatus.PROCESSING
            job.request.started_at = datetime.now()
            job.queue_time = start_time - job.request.created_at.timestamp()
            
            self.active_downloads[download_id] = job
            
            # Actualizează statistici
            current_active = len(self.active_downloads)
            if current_active > self.stats['peak_concurrent_downloads']:
                self.stats['peak_concurrent_downloads'] = current_active
            
            await self._trigger_event('download_started', job)
            
            # Obține instanța platformei
            platform_instance = platform_registry.get_platform_instance(job.platform_name)
            if not platform_instance:
                raise PlatformError(f"Platform {job.platform_name} not available")
            
            job.platform_instance = platform_instance
            
            # Execută descărcarea cu circuit breaker
            result = await platform_registry.execute_with_circuit_breaker(
                job.platform_name,
                self._execute_download_pipeline,
                job
            )
            
            # Succes
            job.status = DownloadStatus.COMPLETED
            job.request.completed_at = datetime.now()
            job.download_result = result
            job.processing_time = time.time() - start_time
            
            # Mută la completed jobs
            self.completed_jobs[download_id] = job
            del self.active_downloads[download_id]
            
            # Actualizează statistici
            self.stats['completed_downloads'] += 1
            self._update_average_download_time(job.processing_time)
            self._update_average_queue_time(job.queue_time)
            
            if result and result.file_size:
                self.stats['total_bytes_downloaded'] += result.file_size
            
            await self._trigger_event('download_completed', job)
            
            # Apelează callback-ul de completion
            if job.request.completion_callback:
                try:
                    await job.request.completion_callback(result)
                except Exception as e:
                    logger.warning(f"⚠️ Completion callback failed for {download_id}: {e}")
            
            logger.info(f"✅ Download completed: {download_id} in {job.processing_time:.2f}s")
            
        except Exception as e:
            await self._handle_job_failure(job, e)
        
        finally:
            # Eliberează semaforul
            self.download_semaphore.release()
            
            # Elimină din active downloads dacă încă există
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
    
    async def _execute_download_pipeline(self, job: DownloadJob) -> DownloadResult:
        """Execută pipeline-ul complet de descărcare"""
        platform = job.platform_instance
        request = job.request
        
        # Step 1: Extract metadata
        job.update_progress(10, "Extracting metadata...")
        job.status = DownloadStatus.EXTRACTING_METADATA
        
        metadata = await platform.extract_metadata(request.url)
        job.metadata = metadata
        
        # Step 2: Validate and prepare download
        job.update_progress(25, "Preparing download...")
        
        # Aplică configurările custom
        download_options = {
            'quality': request.quality,
            'format_preference': request.format_preference,
            'output_path': request.output_path,
            'extract_audio_only': request.extract_audio_only
        }
        
        if request.custom_headers:
            download_options['custom_headers'] = request.custom_headers
        
        # Step 3: Download content
        job.update_progress(30, "Downloading content...")
        job.status = DownloadStatus.DOWNLOADING
        
        # Progress callback pentru download
        def download_progress_callback(progress_info):
            # Mapează progresul de download la 30-90%
            download_progress = progress_info.get('percentage', 0)
            overall_progress = 30 + (download_progress * 0.6)
            
            speed = progress_info.get('speed')
            if speed:
                job.download_speed = speed
            
            eta = progress_info.get('eta')
            job.update_progress(overall_progress, "Downloading...", eta)
        
        download_options['progress_callback'] = download_progress_callback
        
        result = await platform.download_content(request.url, **download_options)
        
        # Step 4: Post-processing (dacă este necesar)
        job.update_progress(95, "Post-processing...")
        job.status = DownloadStatus.POST_PROCESSING
        
        # Aici se pot adăuga operații de post-processing
        # cum ar fi conversii de format, thumbnail generation, etc.
        
        job.update_progress(100, "Completed")
        
        return result
    
    async def _handle_job_failure(self, job: DownloadJob, error: Exception):
        """Gestionează eșecul unui job"""
        download_id = job.request.id
        job.error = error
        
        # Verifică dacă se poate reîncerca
        if (job.retry_count < job.request.max_retries and 
            not isinstance(error, UnsupportedURLError)):
            
            # Retry logic
            job.retry_count += 1
            job.last_retry_at = datetime.now()
            job.status = DownloadStatus.RETRYING
            
            # Exponential backoff
            delay_index = min(job.retry_count - 1, len(self.retry_delays) - 1)
            retry_delay = self.retry_delays[delay_index]
            
            self.stats['retries_performed'] += 1
            
            logger.warning(f"⚠️ Download {download_id} failed, retrying in {retry_delay}s (attempt {job.retry_count}/{job.request.max_retries}): {error}")
            
            # Programează retry-ul
            await asyncio.sleep(retry_delay)
            
            # Re-adaugă în queue cu prioritate mare
            original_priority = job.request.priority
            job.request.priority = DownloadPriority.HIGH
            
            self.download_queues[job.request.priority].appendleft(job)
            self.total_queued += 1
            
            await self._trigger_event('download_retry', job)
            
        else:
            # Eșec final
            job.status = DownloadStatus.FAILED
            job.request.completed_at = datetime.now()
            
            # Mută la failed jobs
            self.failed_jobs[download_id] = job
            
            self.stats['failed_downloads'] += 1
            
            await self._trigger_event('download_failed', job)
            
            # Apelează callback-ul de eroare
            if job.request.error_callback:
                try:
                    await job.request.error_callback(error)
                except Exception as e:
                    logger.warning(f"⚠️ Error callback failed for {download_id}: {e}")
            
            logger.error(f"❌ Download failed permanently: {download_id} - {error}")
    
    def _update_average_download_time(self, download_time: float):
        """Actualizează timpul mediu de descărcare"""
        completed = self.stats['completed_downloads']
        if completed == 1:
            self.stats['average_download_time'] = download_time
        else:
            current_avg = self.stats['average_download_time']
            self.stats['average_download_time'] = ((current_avg * (completed - 1)) + download_time) / completed
    
    def _update_average_queue_time(self, queue_time: float):
        """Actualizează timpul mediu de așteptare în queue"""
        completed = self.stats['completed_downloads']
        if completed == 1:
            self.stats['average_queue_time'] = queue_time
        else:
            current_avg = self.stats['average_queue_time']
            self.stats['average_queue_time'] = ((current_avg * (completed - 1)) + queue_time) / completed
    
    async def _trigger_event(self, event_name: str, job: DownloadJob):
        """Declanșează event hooks"""
        hooks = self.event_hooks.get(event_name, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(job)
                else:
                    hook(job)
            except Exception as e:
                logger.warning(f"⚠️ Event hook {event_name} failed: {e}")
    
    def add_event_hook(self, event_name: str, callback: Callable):
        """Adaugă un hook pentru evenimente"""
        self.event_hooks[event_name].append(callback)
        logger.info(f"📎 Added event hook for {event_name}")
    
    async def _periodic_cleanup(self):
        """Cleanup periodic al job-urilor vechi"""
        while not self._shutdown:
            try:
                await asyncio.sleep(3600)  # Cleanup la fiecare oră
                self._cleanup_old_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic cleanup: {e}")
    
    def _cleanup_old_jobs(self):
        """Curăță job-urile vechi pentru a economisi memoria"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Cleanup completed jobs
        old_completed = []
        for job_id, job in self.completed_jobs.items():
            if job.request.completed_at and job.request.completed_at < cutoff_time:
                old_completed.append(job_id)
        
        for job_id in old_completed[-self.job_history_limit:]:
            del self.completed_jobs[job_id]
        
        # Cleanup failed jobs
        old_failed = []
        for job_id, job in self.failed_jobs.items():
            if job.request.completed_at and job.request.completed_at < cutoff_time:
                old_failed.append(job_id)
        
        for job_id in old_failed[-self.job_history_limit:]:
            del self.failed_jobs[job_id]
        
        if old_completed or old_failed:
            logger.info(f"🧹 Cleaned up {len(old_completed)} completed and {len(old_failed)} failed jobs")
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Returnează statisticile orchestrator-ului"""
        queue_stats = {}
        for priority, queue in self.download_queues.items():
            queue_stats[priority.name.lower()] = len(queue)
        
        return {
            'stats': self.stats,
            'queue_stats': {
                'total_queued': self.total_queued,
                'by_priority': queue_stats,
                'max_queue_size': self.max_queue_size
            },
            'active_downloads': {
                'count': len(self.active_downloads),
                'max_concurrent': self.max_concurrent_downloads,
                'jobs': [job.to_dict() for job in self.active_downloads.values()]
            },
            'history': {
                'completed_jobs': len(self.completed_jobs),
                'failed_jobs': len(self.failed_jobs)
            }
        }
    
    async def shutdown(self):
        """Oprește orchestrator-ul"""
        logger.info("🛑 Shutting down Download Orchestrator...")
        
        self._shutdown = True
        
        # Anulează task-urile de background
        for task in self.background_tasks:
            task.cancel()
        
        # Așteaptă ca task-urile să se termine
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Anulează download-urile active
        for download_id in list(self.active_downloads.keys()):
            await self.cancel_download(download_id)
        
        logger.info("✅ Download Orchestrator shutdown complete")
    
    def __str__(self) -> str:
        return f"DownloadOrchestrator(active={len(self.active_downloads)}, queued={self.total_queued})"
    
    def __repr__(self) -> str:
        return (f"DownloadOrchestrator(active={len(self.active_downloads)}, "
                f"queued={self.total_queued}, max_concurrent={self.max_concurrent_downloads})")


# Singleton instance pentru utilizare globală
download_orchestrator = DownloadOrchestrator()