# utils/network/network_manager.py - Manager de Rețea pentru Conexiuni Optimizate
# Versiunea: 4.0.0 - Arhitectura Refactorizată

import asyncio
import aiohttp
import logging
import time
import random
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from collections import defaultdict, deque
import json
import ssl
import certifi

try:
    from platforms.base.abstract_platform import PlatformError, DownloadError
except ImportError:
    # Fallback pentru development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import PlatformError, DownloadError

logger = logging.getLogger(__name__)

class RequestMethod(Enum):
    """Metodele HTTP suportate"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    PATCH = "PATCH"

class ProxyType(Enum):
    """Tipurile de proxy suportate"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class RateLimitStrategy(Enum):
    """Strategiile de rate limiting"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    EXPONENTIAL_BACKOFF = "exponential_backoff"

@dataclass
class ProxyConfig:
    """Configurația pentru proxy"""
    url: str
    proxy_type: ProxyType
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True
    max_connections: int = 10
    timeout: int = 30
    last_used: datetime = field(default_factory=datetime.now)
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'type': self.proxy_type.value,
            'enabled': self.enabled,
            'success_rate': self.success_rate,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_used': self.last_used.isoformat()
        }

@dataclass
class RateLimitConfig:
    """Configurația pentru rate limiting"""
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    max_requests: int = 60  # Numărul maxim de cereri
    time_window: int = 60   # Fereastra de timp în secunde
    burst_limit: int = 10   # Limita pentru burst requests
    backoff_factor: float = 1.5  # Factorul pentru exponential backoff
    max_backoff: int = 300  # Backoff maxim în secunde

@dataclass
class NetworkRequest:
    """O cerere de rețea"""
    url: str
    method: RequestMethod = RequestMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Optional[Union[str, bytes, Dict[str, Any]]] = None
    json_data: Optional[Dict[str, Any]] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = True
    proxy: Optional[str] = None
    retry_count: int = 3
    retry_delay: float = 1.0
    priority: int = 1  # 1 = low, 5 = high
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'method': self.method.value,
            'headers': self.headers,
            'params': self.params,
            'timeout': self.timeout,
            'follow_redirects': self.follow_redirects,
            'verify_ssl': self.verify_ssl,
            'proxy': self.proxy,
            'retry_count': self.retry_count,
            'priority': self.priority,
            'metadata': self.metadata
        }

@dataclass
class NetworkResponse:
    """Răspunsul unei cereri de rețea"""
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    url: str
    request_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def json(self) -> Dict[str, Any]:
        """Parsează conținutul ca JSON"""
        try:
            return json.loads(self.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status_code': self.status_code,
            'headers': dict(self.headers),
            'url': self.url,
            'request_time': self.request_time,
            'success': self.success,
            'error_message': self.error_message,
            'content_length': len(self.content),
            'metadata': self.metadata
        }

class RateLimiter:
    """Rate limiter pentru controlul cererilor"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = defaultdict(deque)  # Domain -> deque of timestamps
        self.tokens = defaultdict(lambda: config.max_requests)  # Token bucket
        self.last_refill = defaultdict(lambda: time.time())
        self.backoff_until = defaultdict(lambda: 0)  # Domain -> timestamp
        
    async def acquire(self, domain: str) -> bool:
        """Încearcă să obțină permisiunea pentru o cerere"""
        now = time.time()
        
        # Verifică dacă suntem în backoff
        if now < self.backoff_until[domain]:
            return False
        
        if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._sliding_window_acquire(domain, now)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._token_bucket_acquire(domain, now)
        elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._fixed_window_acquire(domain, now)
        else:
            return True
    
    def _sliding_window_acquire(self, domain: str, now: float) -> bool:
        """Sliding window rate limiting"""
        requests = self.requests[domain]
        
        # Elimină cererile vechi
        while requests and requests[0] < now - self.config.time_window:
            requests.popleft()
        
        # Verifică dacă putem face cererea
        if len(requests) < self.config.max_requests:
            requests.append(now)
            return True
        
        return False
    
    def _token_bucket_acquire(self, domain: str, now: float) -> bool:
        """Token bucket rate limiting"""
        # Refill tokens
        time_passed = now - self.last_refill[domain]
        tokens_to_add = time_passed * (self.config.max_requests / self.config.time_window)
        self.tokens[domain] = min(self.config.max_requests, self.tokens[domain] + tokens_to_add)
        self.last_refill[domain] = now
        
        # Consumă un token
        if self.tokens[domain] >= 1:
            self.tokens[domain] -= 1
            return True
        
        return False
    
    def _fixed_window_acquire(self, domain: str, now: float) -> bool:
        """Fixed window rate limiting"""
        window_start = int(now // self.config.time_window) * self.config.time_window
        requests = self.requests[domain]
        
        # Curăță cererile din ferestre vechi
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Verifică dacă putem face cererea
        if len(requests) < self.config.max_requests:
            requests.append(now)
            return True
        
        return False
    
    def set_backoff(self, domain: str, duration: float):
        """Setează backoff pentru un domeniu"""
        self.backoff_until[domain] = time.time() + duration
        logger.warning(f"⏰ Rate limit backoff set for {domain}: {duration}s")
    
    def get_wait_time(self, domain: str) -> float:
        """Obține timpul de așteptare pentru următoarea cerere"""
        now = time.time()
        
        # Verifică backoff
        if now < self.backoff_until[domain]:
            return self.backoff_until[domain] - now
        
        if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            requests = self.requests[domain]
            if len(requests) >= self.config.max_requests:
                oldest_request = requests[0]
                return max(0, oldest_request + self.config.time_window - now)
        
        return 0.0

class UserAgentRotator:
    """Rotator pentru User-Agent strings"""
    
    def __init__(self):
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self.mobile_user_agents = [
            # iPhone
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            
            # Android Chrome
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            
            # iPad
            'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        ]
        
        self.current_index = 0
        self.mobile_index = 0
    
    def get_random_user_agent(self, mobile: bool = False) -> str:
        """Obține un User-Agent aleatoriu"""
        agents = self.mobile_user_agents if mobile else self.user_agents
        return random.choice(agents)
    
    def get_next_user_agent(self, mobile: bool = False) -> str:
        """Obține următorul User-Agent în rotație"""
        if mobile:
            agent = self.mobile_user_agents[self.mobile_index]
            self.mobile_index = (self.mobile_index + 1) % len(self.mobile_user_agents)
        else:
            agent = self.user_agents[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.user_agents)
        
        return agent

class ProxyManager:
    """Manager pentru proxy-uri"""
    
    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.current_index = 0
        self._lock = asyncio.Lock()
    
    async def add_proxy(self, proxy_config: ProxyConfig):
        """Adaugă un proxy"""
        async with self._lock:
            self.proxies.append(proxy_config)
            logger.info(f"🔗 Added proxy: {proxy_config.url}")
    
    async def remove_proxy(self, proxy_url: str):
        """Elimină un proxy"""
        async with self._lock:
            self.proxies = [p for p in self.proxies if p.url != proxy_url]
            logger.info(f"🗑️ Removed proxy: {proxy_url}")
    
    async def get_best_proxy(self) -> Optional[ProxyConfig]:
        """Obține cel mai bun proxy disponibil"""
        async with self._lock:
            available_proxies = [p for p in self.proxies if p.enabled]
            
            if not available_proxies:
                return None
            
            # Sortează după success rate și ultima utilizare
            available_proxies.sort(
                key=lambda p: (p.success_rate, -time.time() + p.last_used.timestamp()),
                reverse=True
            )
            
            return available_proxies[0]
    
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Obține următorul proxy în rotație"""
        async with self._lock:
            available_proxies = [p for p in self.proxies if p.enabled]
            
            if not available_proxies:
                return None
            
            proxy = available_proxies[self.current_index % len(available_proxies)]
            self.current_index += 1
            
            return proxy
    
    async def mark_proxy_success(self, proxy_url: str):
        """Marchează un proxy ca fiind de succes"""
        async with self._lock:
            for proxy in self.proxies:
                if proxy.url == proxy_url:
                    proxy.success_count += 1
                    proxy.last_used = datetime.now()
                    break
    
    async def mark_proxy_failure(self, proxy_url: str):
        """Marchează un proxy ca fiind eșuat"""
        async with self._lock:
            for proxy in self.proxies:
                if proxy.url == proxy_url:
                    proxy.failure_count += 1
                    # Dezactivează proxy-ul dacă are prea multe eșecuri
                    if proxy.success_rate < 0.5 and proxy.failure_count > 10:
                        proxy.enabled = False
                        logger.warning(f"⚠️ Disabled proxy due to low success rate: {proxy_url}")
                    break
    
    async def get_proxy_stats(self) -> List[Dict[str, Any]]:
        """Obține statisticile proxy-urilor"""
        async with self._lock:
            return [proxy.to_dict() for proxy in self.proxies]

class NetworkManager:
    """
    Manager centralizat pentru toate operațiunile de rețea.
    Oferă rate limiting, proxy rotation, User-Agent rotation,
    retry logic și connection pooling.
    """
    
    def __init__(self, rate_limit_config: Optional[RateLimitConfig] = None):
        # Configurare
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        
        # Componente
        self.rate_limiter = RateLimiter(self.rate_limit_config)
        self.user_agent_rotator = UserAgentRotator()
        self.proxy_manager = ProxyManager()
        
        # Session pool
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.session_configs: Dict[str, Dict[str, Any]] = {}
        
        # Statistici
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'proxy_requests': 0,
            'average_response_time': 0.0,
            'domains_accessed': set(),
            'errors_by_type': defaultdict(int)
        }
        
        # Cache pentru DNS și alte optimizări
        self.dns_cache: Dict[str, str] = {}
        
        # SSL context optimizat
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        logger.info("🌐 Network Manager initialized")
    
    async def initialize(self):
        """Inițializează managerul de rețea"""
        logger.info("🚀 Starting Network Manager...")
        
        # Creează session-ul default
        await self._create_default_session()
        
        logger.info("✅ Network Manager initialized")
    
    async def _create_default_session(self):
        """Creează session-ul HTTP default"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection pool size
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            ssl=self.ssl_context,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.user_agent_rotator.get_random_user_agent()}
        )
        
        self.sessions['default'] = session
        logger.info("🔗 Created default HTTP session")
    
    async def get_session(self, session_name: str = 'default', 
                         custom_config: Optional[Dict[str, Any]] = None) -> aiohttp.ClientSession:
        """Obține sau creează o sesiune HTTP"""
        if session_name not in self.sessions:
            await self._create_custom_session(session_name, custom_config or {})
        
        return self.sessions[session_name]
    
    async def _create_custom_session(self, name: str, config: Dict[str, Any]):
        """Creează o sesiune HTTP personalizată"""
        connector_config = config.get('connector', {})
        timeout_config = config.get('timeout', {})
        headers_config = config.get('headers', {})
        
        connector = aiohttp.TCPConnector(
            limit=connector_config.get('limit', 100),
            limit_per_host=connector_config.get('limit_per_host', 30),
            ttl_dns_cache=connector_config.get('ttl_dns_cache', 300),
            use_dns_cache=connector_config.get('use_dns_cache', True),
            ssl=self.ssl_context if connector_config.get('verify_ssl', True) else False,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=timeout_config.get('total', 30),
            connect=timeout_config.get('connect', 10)
        )
        
        default_headers = {'User-Agent': self.user_agent_rotator.get_random_user_agent()}
        default_headers.update(headers_config)
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=default_headers
        )
        
        self.sessions[name] = session
        self.session_configs[name] = config
        
        logger.info(f"🔗 Created custom HTTP session: {name}")
    
    async def make_request(self, request: NetworkRequest, 
                          session_name: str = 'default') -> NetworkResponse:
        """
        Efectuează o cerere HTTP cu toate optimizările.
        
        Args:
            request: Cererea de efectuat
            session_name: Numele sesiunii de utilizat
        
        Returns:
            NetworkResponse cu rezultatul
        """
        start_time = time.time()
        domain = urlparse(request.url).netloc
        
        self.stats['total_requests'] += 1
        self.stats['domains_accessed'].add(domain)
        
        try:
            # Rate limiting
            if not await self.rate_limiter.acquire(domain):
                wait_time = self.rate_limiter.get_wait_time(domain)
                if wait_time > 0:
                    self.stats['rate_limited_requests'] += 1
                    logger.debug(f"⏰ Rate limited for {domain}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    
                    # Încearcă din nou
                    if not await self.rate_limiter.acquire(domain):
                        raise PlatformError(f"Rate limit exceeded for {domain}")
            
            # Pregătește cererea
            prepared_request = await self._prepare_request(request)
            
            # Efectuează cererea cu retry logic
            response = await self._execute_request_with_retry(prepared_request, session_name)
            
            # Actualizează statisticile
            request_time = time.time() - start_time
            self._update_stats(True, request_time, None)
            
            return response
            
        except Exception as e:
            request_time = time.time() - start_time
            self._update_stats(False, request_time, e)
            
            # Setează backoff pentru domeniu în caz de eroare
            if isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                backoff_time = min(self.rate_limit_config.max_backoff, 
                                 self.rate_limit_config.backoff_factor * request.retry_delay)
                self.rate_limiter.set_backoff(domain, backoff_time)
            
            raise DownloadError(f"Network request failed: {e}")
    
    async def _prepare_request(self, request: NetworkRequest) -> NetworkRequest:
        """Pregătește cererea cu toate optimizările"""
        # Clonează cererea pentru a nu modifica originalul
        prepared = NetworkRequest(
            url=request.url,
            method=request.method,
            headers=request.headers.copy(),
            params=request.params.copy(),
            data=request.data,
            json_data=request.json_data,
            cookies=request.cookies.copy(),
            timeout=request.timeout,
            follow_redirects=request.follow_redirects,
            verify_ssl=request.verify_ssl,
            proxy=request.proxy,
            retry_count=request.retry_count,
            retry_delay=request.retry_delay,
            priority=request.priority,
            metadata=request.metadata.copy()
        )
        
        # Adaugă User-Agent dacă nu există
        if 'User-Agent' not in prepared.headers:
            mobile = 'mobile' in request.metadata.get('platform', '').lower()
            prepared.headers['User-Agent'] = self.user_agent_rotator.get_next_user_agent(mobile)
        
        # Adaugă headers comune
        if 'Accept' not in prepared.headers:
            prepared.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        
        if 'Accept-Language' not in prepared.headers:
            prepared.headers['Accept-Language'] = 'en-US,en;q=0.9,ro;q=0.8'
        
        if 'Accept-Encoding' not in prepared.headers:
            prepared.headers['Accept-Encoding'] = 'gzip, deflate, br'
        
        if 'DNT' not in prepared.headers:
            prepared.headers['DNT'] = '1'
        
        # Selectează proxy dacă nu este specificat
        if not prepared.proxy:
            proxy = await self.proxy_manager.get_next_proxy()
            if proxy:
                prepared.proxy = proxy.url
                prepared.metadata['proxy_config'] = proxy
        
        return prepared
    
    async def _execute_request_with_retry(self, request: NetworkRequest, 
                                        session_name: str) -> NetworkResponse:
        """Execută cererea cu retry logic"""
        last_error = None
        
        for attempt in range(request.retry_count + 1):
            try:
                response = await self._execute_single_request(request, session_name)
                
                # Marchează proxy-ul ca fiind de succes
                if request.proxy:
                    await self.proxy_manager.mark_proxy_success(request.proxy)
                
                return response
                
            except Exception as e:
                last_error = e
                
                # Marchează proxy-ul ca fiind eșuat
                if request.proxy:
                    await self.proxy_manager.mark_proxy_failure(request.proxy)
                
                # Nu mai încerca dacă este ultima încercare
                if attempt == request.retry_count:
                    break
                
                # Calculează delay pentru retry
                delay = request.retry_delay * (self.rate_limit_config.backoff_factor ** attempt)
                delay = min(delay, self.rate_limit_config.max_backoff)
                
                logger.warning(f"🔄 Request failed (attempt {attempt + 1}/{request.retry_count + 1}), retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
                
                # Încearcă cu un proxy diferit la următoarea încercare
                if request.proxy:
                    new_proxy = await self.proxy_manager.get_next_proxy()
                    if new_proxy:
                        request.proxy = new_proxy.url
                        request.metadata['proxy_config'] = new_proxy
        
        raise last_error or DownloadError("Request failed after all retries")
    
    async def _execute_single_request(self, request: NetworkRequest, 
                                     session_name: str) -> NetworkResponse:
        """Execută o singură cerere HTTP"""
        session = await self.get_session(session_name)
        start_time = time.time()
        
        # Pregătește argumentele pentru cerere
        kwargs = {
            'url': request.url,
            'headers': request.headers,
            'params': request.params,
            'cookies': request.cookies,
            'timeout': aiohttp.ClientTimeout(total=request.timeout),
            'allow_redirects': request.follow_redirects,
            'ssl': request.verify_ssl,
        }
        
        if request.proxy:
            kwargs['proxy'] = request.proxy
            self.stats['proxy_requests'] += 1
        
        if request.data is not None:
            kwargs['data'] = request.data
        
        if request.json_data is not None:
            kwargs['json'] = request.json_data
        
        # Efectuează cererea
        async with session.request(request.method.value, **kwargs) as response:
            content = await response.read()
            text = await response.text(errors='ignore')
            
            request_time = time.time() - start_time
            
            return NetworkResponse(
                status_code=response.status,
                headers=dict(response.headers),
                content=content,
                text=text,
                url=str(response.url),
                request_time=request_time,
                success=200 <= response.status < 400,
                metadata=request.metadata.copy()
            )
    
    def _update_stats(self, success: bool, request_time: float, error: Optional[Exception]):
        """Actualizează statisticile"""
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
            
            if error:
                error_type = type(error).__name__
                self.stats['errors_by_type'][error_type] += 1
        
        # Actualizează timpul mediu de răspuns
        total_requests = self.stats['successful_requests'] + self.stats['failed_requests']
        if total_requests > 0:
            current_avg = self.stats['average_response_time']
            self.stats['average_response_time'] = (
                (current_avg * (total_requests - 1) + request_time) / total_requests
            )
    
    async def get(self, url: str, **kwargs) -> NetworkResponse:
        """Efectuează o cerere GET"""
        request = NetworkRequest(url=url, method=RequestMethod.GET, **kwargs)
        return await self.make_request(request)
    
    async def post(self, url: str, data: Any = None, json_data: Dict[str, Any] = None, **kwargs) -> NetworkResponse:
        """Efectuează o cerere POST"""
        request = NetworkRequest(url=url, method=RequestMethod.POST, data=data, json_data=json_data, **kwargs)
        return await self.make_request(request)
    
    async def put(self, url: str, data: Any = None, json_data: Dict[str, Any] = None, **kwargs) -> NetworkResponse:
        """Efectuează o cerere PUT"""
        request = NetworkRequest(url=url, method=RequestMethod.PUT, data=data, json_data=json_data, **kwargs)
        return await self.make_request(request)
    
    async def delete(self, url: str, **kwargs) -> NetworkResponse:
        """Efectuează o cerere DELETE"""
        request = NetworkRequest(url=url, method=RequestMethod.DELETE, **kwargs)
        return await self.make_request(request)
    
    async def head(self, url: str, **kwargs) -> NetworkResponse:
        """Efectuează o cerere HEAD"""
        request = NetworkRequest(url=url, method=RequestMethod.HEAD, **kwargs)
        return await self.make_request(request)
    
    async def download_file(self, url: str, chunk_size: int = 8192, 
                           progress_callback: Optional[Callable] = None) -> bytes:
        """Descarcă un fișier în chunks cu progress tracking"""
        request = NetworkRequest(url=url, method=RequestMethod.GET)
        session = await self.get_session()
        
        async with session.get(url, headers=request.headers) as response:
            if response.status != 200:
                raise DownloadError(f"HTTP {response.status}: {response.reason}")
            
            content = bytearray()
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            async for chunk in response.content.iter_chunked(chunk_size):
                content.extend(chunk)
                downloaded += len(chunk)
                
                if progress_callback:
                    try:
                        if asyncio.iscoroutinefunction(progress_callback):
                            await progress_callback(downloaded, total_size)
                        else:
                            progress_callback(downloaded, total_size)
                    except Exception as e:
                        logger.warning(f"⚠️ Progress callback failed: {e}")
            
            return bytes(content)
    
    def add_proxy(self, proxy_url: str, proxy_type: ProxyType = ProxyType.HTTP, 
                 username: str = None, password: str = None):
        """Adaugă un proxy"""
        proxy_config = ProxyConfig(
            url=proxy_url,
            proxy_type=proxy_type,
            username=username,
            password=password
        )
        asyncio.create_task(self.proxy_manager.add_proxy(proxy_config))
    
    def set_rate_limit(self, max_requests: int, time_window: int, 
                      strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW):
        """Configurează rate limiting"""
        self.rate_limit_config.max_requests = max_requests
        self.rate_limit_config.time_window = time_window
        self.rate_limit_config.strategy = strategy
        
        # Recreează rate limiter-ul
        self.rate_limiter = RateLimiter(self.rate_limit_config)
        
        logger.info(f"🚦 Rate limit updated: {max_requests} requests per {time_window}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obține statisticile managerului de rețea"""
        stats = self.stats.copy()
        stats['domains_accessed'] = list(stats['domains_accessed'])
        stats['errors_by_type'] = dict(stats['errors_by_type'])
        return stats
    
    async def get_proxy_stats(self) -> List[Dict[str, Any]]:
        """Obține statisticile proxy-urilor"""
        return await self.proxy_manager.get_proxy_stats()
    
    async def clear_cache(self):
        """Curăță cache-urile"""
        self.dns_cache.clear()
        logger.info("🧹 Network caches cleared")
    
    async def shutdown(self):
        """Oprește managerul de rețea"""
        logger.info("🛑 Shutting down Network Manager...")
        
        # Închide toate sesiunile
        for session_name, session in self.sessions.items():
            await session.close()
            logger.debug(f"🔌 Closed session: {session_name}")
        
        self.sessions.clear()
        
        logger.info("✅ Network Manager shutdown complete")
    
    def __str__(self) -> str:
        total = self.stats['total_requests']
        success = self.stats['successful_requests']
        return f"NetworkManager(requests={total}, success_rate={success/total*100:.1f}% if total > 0 else 0.0}%)"
    
    def __repr__(self) -> str:
        return (f"NetworkManager(sessions={len(self.sessions)}, "
                f"proxies={len(self.proxy_manager.proxies)}, "
                f"requests={self.stats['total_requests']})")


# Singleton instance pentru utilizare globală
network_manager = NetworkManager()