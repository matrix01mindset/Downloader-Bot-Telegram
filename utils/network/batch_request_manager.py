import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

@dataclass
class BatchRequest:
    """Reprezintă o cerere pentru procesare în batch"""
    request_id: str
    url: str
    method: str = 'GET'
    data: Optional[Dict] = None
    json_data: Optional[Dict] = None
    headers: Optional[Dict] = None
    timeout: int = 30
    priority: int = 1  # 1=high, 2=medium, 3=low
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)
    max_retries: int = 3
    retry_count: int = 0

class BatchRequestManager:
    """Manager pentru optimizarea cererilor în batch-uri"""
    
    def __init__(self, 
                 batch_size: int = 10,
                 batch_timeout: float = 2.0,
                 max_concurrent_batches: int = 3,
                 enable_caching: bool = True):
        self.logger = logging.getLogger(__name__)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_concurrent_batches = max_concurrent_batches
        self.enable_caching = enable_caching
        
        # Cozi pentru diferite priorități
        self.high_priority_queue: List[BatchRequest] = []
        self.medium_priority_queue: List[BatchRequest] = []
        self.low_priority_queue: List[BatchRequest] = []
        
        # Cache pentru răspunsuri
        self.response_cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        
        # Rezultate și callback-uri
        self.pending_results: Dict[str, asyncio.Future] = {}
        self.batch_stats: Dict[str, Any] = defaultdict(int)
        
        # Control pentru procesare
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None
        
    def _generate_cache_key(self, request: BatchRequest) -> str:
        """Generează o cheie de cache pentru cerere"""
        key_data = {
            'url': request.url,
            'method': request.method,
            'data': request.data,
            'json': request.json_data
        }
        return f"{request.method}:{request.url}:{hash(json.dumps(key_data, sort_keys=True))}"
    
    def _is_cache_valid(self, cache_key: str, ttl_minutes: int = 5) -> bool:
        """Verifică dacă cache-ul este valid"""
        if not self.enable_caching or cache_key not in self.cache_ttl:
            return False
            
        expiry_time = self.cache_ttl[cache_key] + timedelta(minutes=ttl_minutes)
        return datetime.now() < expiry_time
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Returnează răspunsul din cache dacă este valid"""
        if self._is_cache_valid(cache_key):
            self.batch_stats['cache_hits'] += 1
            return self.response_cache.get(cache_key)
        return None
    
    def _store_in_cache(self, cache_key: str, response: Any):
        """Stochează răspunsul în cache"""
        if self.enable_caching:
            self.response_cache[cache_key] = response
            self.cache_ttl[cache_key] = datetime.now()
            self.batch_stats['cache_stores'] += 1
    
    def _get_queue_by_priority(self, priority: int) -> List[BatchRequest]:
        """Returnează coada corespunzătoare priorității"""
        if priority == 1:
            return self.high_priority_queue
        elif priority == 2:
            return self.medium_priority_queue
        else:
            return self.low_priority_queue
    
    async def add_request(self, request: BatchRequest) -> asyncio.Future:
        """Adaugă o cerere la coadă și returnează un Future pentru rezultat"""
        # Verifică cache-ul
        cache_key = self._generate_cache_key(request)
        cached_response = self._get_from_cache(cache_key)
        
        if cached_response is not None:
            future = asyncio.Future()
            future.set_result(cached_response)
            self.logger.debug(f"Răspuns găsit în cache pentru {request.request_id}")
            return future
        
        # Adaugă la coadă
        queue = self._get_queue_by_priority(request.priority)
        queue.append(request)
        
        # Creează Future pentru rezultat
        future = asyncio.Future()
        self.pending_results[request.request_id] = future
        
        self.logger.debug(f"Cerere {request.request_id} adăugată la coada de prioritate {request.priority}")
        
        # Pornește procesarea dacă nu este deja activă
        if not self.is_processing:
            await self._start_processing()
            
        return future
    
    async def _start_processing(self):
        """Pornește procesarea batch-urilor"""
        if self.is_processing:
            return
            
        self.is_processing = True
        self.processing_task = asyncio.create_task(self._process_batches())
        self.logger.info("Procesarea batch-urilor a început")
    
    async def _process_batches(self):
        """Procesează batch-urile în mod continuu"""
        from .async_download_manager import get_download_manager
        
        try:
            while self.is_processing:
                # Colectează cereri pentru batch
                batch_requests = self._collect_batch_requests()
                
                if not batch_requests:
                    # Așteaptă puțin dacă nu sunt cereri
                    await asyncio.sleep(0.1)
                    continue
                
                self.logger.info(f"Procesez batch de {len(batch_requests)} cereri")
                
                # Procesează batch-ul
                await self._process_batch(batch_requests)
                
                # Statistici
                self.batch_stats['batches_processed'] += 1
                self.batch_stats['total_requests'] += len(batch_requests)
                
        except Exception as e:
            self.logger.error(f"Eroare în procesarea batch-urilor: {str(e)}")
        finally:
            self.is_processing = False
    
    def _collect_batch_requests(self) -> List[BatchRequest]:
        """Colectează cereri pentru următorul batch"""
        batch_requests = []
        
        # Prioritizează cererile de prioritate înaltă
        for queue in [self.high_priority_queue, self.medium_priority_queue, self.low_priority_queue]:
            while queue and len(batch_requests) < self.batch_size:
                batch_requests.append(queue.pop(0))
        
        return batch_requests
    
    async def _process_batch(self, batch_requests: List[BatchRequest]):
        """Procesează un batch de cereri"""
        from .async_download_manager import get_download_manager, NetworkRequest
        
        download_manager = await get_download_manager()
        
        # Convertește la NetworkRequest
        network_requests = []
        for req in batch_requests:
            network_req = NetworkRequest(
                url=req.url,
                method=req.method,
                data=req.data,
                json=req.json_data,
                headers=req.headers,
                timeout=req.timeout,
                request_id=req.request_id
            )
            network_requests.append(network_req)
        
        # Execută batch-ul
        try:
            results = await download_manager.batch_requests(network_requests)
            
            # Procesează rezultatele
            for i, result in enumerate(results):
                request = batch_requests[i]
                future = self.pending_results.get(request.request_id)
                
                if future and not future.done():
                    if result.get('success', False):
                        # Stochează în cache
                        cache_key = self._generate_cache_key(request)
                        self._store_in_cache(cache_key, result)
                        
                        # Setează rezultatul
                        future.set_result(result)
                        
                        # Callback
                        if request.callback:
                            try:
                                await request.callback(result)
                            except Exception as e:
                                self.logger.error(f"Eroare în callback pentru {request.request_id}: {str(e)}")
                                
                    else:
                        # Retry logic
                        if request.retry_count < request.max_retries:
                            request.retry_count += 1
                            queue = self._get_queue_by_priority(request.priority)
                            queue.append(request)
                            self.logger.warning(f"Retry {request.retry_count}/{request.max_retries} pentru {request.request_id}")
                        else:
                            future.set_result(result)
                            self.logger.error(f"Cererea {request.request_id} a eșuat după {request.max_retries} încercări")
                
                # Curăță rezultatul pending
                if request.request_id in self.pending_results:
                    del self.pending_results[request.request_id]
                    
        except Exception as e:
            self.logger.error(f"Eroare în procesarea batch-ului: {str(e)}")
            
            # Setează eroare pentru toate Future-urile
            for request in batch_requests:
                future = self.pending_results.get(request.request_id)
                if future and not future.done():
                    future.set_exception(e)
                    del self.pending_results[request.request_id]
    
    async def stop_processing(self):
        """Oprește procesarea batch-urilor"""
        self.is_processing = False
        if self.processing_task:
            await self.processing_task
            self.processing_task = None
        self.logger.info("Procesarea batch-urilor a fost oprită")
    
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statistici despre procesare"""
        return {
            'batches_processed': self.batch_stats['batches_processed'],
            'total_requests': self.batch_stats['total_requests'],
            'cache_hits': self.batch_stats['cache_hits'],
            'cache_stores': self.batch_stats['cache_stores'],
            'pending_requests': len(self.pending_results),
            'queue_sizes': {
                'high_priority': len(self.high_priority_queue),
                'medium_priority': len(self.medium_priority_queue),
                'low_priority': len(self.low_priority_queue)
            },
            'cache_size': len(self.response_cache)
        }
    
    def clear_cache(self):
        """Curăță cache-ul"""
        self.response_cache.clear()
        self.cache_ttl.clear()
        self.batch_stats['cache_cleared'] = self.batch_stats.get('cache_cleared', 0) + 1
        self.logger.info("Cache-ul a fost curățat")

# Instanță globală pentru reutilizare
_global_batch_manager: Optional[BatchRequestManager] = None

def get_batch_manager() -> BatchRequestManager:
    """Returnează instanța globală a batch manager-ului"""
    global _global_batch_manager
    if _global_batch_manager is None:
        _global_batch_manager = BatchRequestManager()
    return _global_batch_manager

async def cleanup_batch_manager():
    """Curăță instanța globală"""
    global _global_batch_manager
    if _global_batch_manager:
        await _global_batch_manager.stop_processing()
        _global_batch_manager = None