import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class NetworkRequest:
    """Reprezintă o cerere de rețea pentru procesare în batch"""
    url: str
    method: str = 'GET'
    data: Optional[Dict] = None
    json: Optional[Dict] = None
    headers: Optional[Dict] = None
    timeout: int = 30
    files: Optional[Dict] = None
    callback: Optional[callable] = None
    request_id: Optional[str] = None

class AsyncDownloadManager:
    """Manager pentru optimizarea apelurilor de rețea cu async/await"""
    
    def __init__(self, max_concurrent_requests: int = 10, batch_size: int = 5):
        self.logger = logging.getLogger(__name__)
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_size = batch_size
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_queue: List[NetworkRequest] = []
        self.results: Dict[str, Any] = {}
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.start_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close_session()
        
    async def start_session(self):
        """Inițializează sesiunea aiohttp"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_requests,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=60,
                connect=20,
                sock_read=30
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'TelegramBot/1.0 (Async)'
                }
            )
            
            self.logger.info(f"Sesiune async inițializată cu {self.max_concurrent_requests} conexiuni concurente")
    
    async def close_session(self):
        """Închide sesiunea aiohttp"""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("Sesiune async închisă")
    
    async def make_request(self, request: NetworkRequest) -> Dict[str, Any]:
        """Execută o cerere de rețea async"""
        if not self.session:
            await self.start_session()
            
        try:
            start_time = datetime.now()
            
            # Pregătește parametrii cererii
            kwargs = {
                'timeout': aiohttp.ClientTimeout(total=request.timeout)
            }
            
            if request.headers:
                kwargs['headers'] = request.headers
                
            if request.json:
                kwargs['json'] = request.json
            elif request.data:
                kwargs['data'] = request.data
                
            if request.files:
                # Pentru upload de fișiere
                form_data = aiohttp.FormData()
                for key, value in request.files.items():
                    form_data.add_field(key, value)
                if request.data:
                    for key, value in request.data.items():
                        form_data.add_field(key, value)
                kwargs['data'] = form_data
            
            # Execută cererea
            async with self.session.request(request.method, request.url, **kwargs) as response:
                response_time = (datetime.now() - start_time).total_seconds()
                
                # Citește răspunsul
                if response.content_type == 'application/json':
                    content = await response.json()
                else:
                    content = await response.text()
                
                result = {
                    'status_code': response.status,
                    'content': content,
                    'headers': dict(response.headers),
                    'response_time': response_time,
                    'success': response.status < 400,
                    'request_id': request.request_id
                }
                
                if request.callback:
                    await request.callback(result)
                    
                self.logger.debug(f"Cerere {request.method} {request.url} completată în {response_time:.2f}s")
                return result
                
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout pentru {request.method} {request.url}")
            return {
                'status_code': 408,
                'content': 'Request Timeout',
                'success': False,
                'error': 'timeout',
                'request_id': request.request_id
            }
        except Exception as e:
            self.logger.error(f"Eroare în cererea {request.method} {request.url}: {str(e)}")
            return {
                'status_code': 500,
                'content': str(e),
                'success': False,
                'error': str(e),
                'request_id': request.request_id
            }
    
    async def batch_requests(self, requests: List[NetworkRequest]) -> List[Dict[str, Any]]:
        """Execută multiple cereri în paralel cu limitare de concurență"""
        if not requests:
            return []
            
        self.logger.info(f"Procesez batch de {len(requests)} cereri")
        
        # Limitează concurența
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def limited_request(req):
            async with semaphore:
                return await self.make_request(req)
        
        # Execută toate cererile în paralel
        tasks = [limited_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesează rezultatele
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'status_code': 500,
                    'content': str(result),
                    'success': False,
                    'error': str(result),
                    'request_id': requests[i].request_id
                })
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.get('success', False))
        self.logger.info(f"Batch completat: {successful}/{len(requests)} cereri reușite")
        
        return processed_results
    
    def add_to_queue(self, request: NetworkRequest):
        """Adaugă o cerere la coada de procesare"""
        self.request_queue.append(request)
        
    async def process_queue(self) -> List[Dict[str, Any]]:
        """Procesează toate cererile din coadă"""
        if not self.request_queue:
            return []
            
        requests_to_process = self.request_queue.copy()
        self.request_queue.clear()
        
        return await self.batch_requests(requests_to_process)
    
    async def send_telegram_message_async(self, token: str, chat_id: str, text: str, 
                                        parse_mode: str = None, reply_markup: str = None) -> bool:
        """Versiune async pentru trimiterea mesajelor Telegram"""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        data = {
            'chat_id': chat_id,
            'text': text
        }
        
        if parse_mode:
            data['parse_mode'] = parse_mode
        if reply_markup:
            data['reply_markup'] = reply_markup
            
        request = NetworkRequest(
            url=url,
            method='POST',
            json=data,
            timeout=30
        )
        
        result = await self.make_request(request)
        
        if result['success']:
            self.logger.info(f"Mesaj trimis cu succes către chat_id {chat_id}")
            return True
        else:
            # Fallback fără parse_mode
            if parse_mode:
                self.logger.warning(f"Eroare cu {parse_mode}, încerc fără parse_mode")
                data_fallback = {
                    'chat_id': chat_id,
                    'text': text
                }
                if reply_markup:
                    data_fallback['reply_markup'] = reply_markup
                    
                request_fallback = NetworkRequest(
                    url=url,
                    method='POST',
                    json=data_fallback,
                    timeout=30
                )
                
                result_fallback = await self.make_request(request_fallback)
                
                if result_fallback['success']:
                    self.logger.info(f"Mesaj trimis cu succes către chat_id {chat_id} fără parse_mode")
                    return True
                    
            self.logger.error(f"Eroare la trimiterea mesajului: {result.get('content', 'Unknown error')}")
            return False

# Instanță globală pentru reutilizare
_global_download_manager: Optional[AsyncDownloadManager] = None

async def get_download_manager() -> AsyncDownloadManager:
    """Returnează instanța globală a download manager-ului"""
    global _global_download_manager
    if _global_download_manager is None:
        _global_download_manager = AsyncDownloadManager()
        await _global_download_manager.start_session()
    return _global_download_manager

async def cleanup_download_manager():
    """Curăță instanța globală"""
    global _global_download_manager
    if _global_download_manager:
        await _global_download_manager.close_session()
        _global_download_manager = None