# core/retry_manager.py - Advanced Retry Logic cu strategii specifice
# Versiunea: 2.0.0 - Arhitectura Modulară

import asyncio
import logging
import time
import random
from typing import Dict, List, Callable, Any, Optional
from abc import ABC, abstractmethod
from enum import Enum

try:
    from utils.config import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Tipuri de erori pentru retry strategies"""
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit" 
    PARSING_ERROR = "parsing_error"
    PLATFORM_ERROR = "platform_error"
    AUTHENTICATION_ERROR = "authentication_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"
    UNKNOWN_ERROR = "unknown_error"

class RetryStrategy(ABC):
    """Abstract base class pentru retry strategies"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        
    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determină dacă să reîncerce după această eroare"""
        pass
        
    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Calculează delay-ul pentru următoarea încercare"""
        pass
        
    def get_max_attempts(self) -> int:
        """Returnează numărul maxim de încercări"""
        return self.max_attempts

class NoRetryStrategy(RetryStrategy):
    """Nu reîncerca niciodată - pentru erori permanente"""
    
    def __init__(self):
        super().__init__(max_attempts=0)
        
    def should_retry(self, error: Exception, attempt: int) -> bool:
        return False
        
    def get_delay(self, attempt: int) -> float:
        return 0.0

class LinearRetryStrategy(RetryStrategy):
    """Retry cu delay linear (constant)"""
    
    def __init__(self, max_attempts: int = 3, delay: float = 10.0):
        super().__init__(max_attempts, delay)
        
    def should_retry(self, error: Exception, attempt: int) -> bool:
        return attempt < self.max_attempts
        
    def get_delay(self, attempt: int) -> float:
        return self.base_delay

class ExponentialBackoffStrategy(RetryStrategy):
    """Retry cu exponential backoff cu jitter"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 2.0, 
                 max_delay: float = 60.0, jitter: bool = True):
        super().__init__(max_attempts, base_delay)
        self.max_delay = max_delay
        self.jitter = jitter
        
    def should_retry(self, error: Exception, attempt: int) -> bool:
        # Nu reîncerca pentru erori permanente
        error_msg = str(error).lower()
        permanent_errors = [
            'private', 'unavailable', 'not found', 'deleted', 
            'copyright', 'blocked', 'forbidden'
        ]
        
        if any(perm_error in error_msg for perm_error in permanent_errors):
            return False
            
        return attempt < self.max_attempts
        
    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay ** attempt, self.max_delay)
        
        if self.jitter:
            # Adaugă jitter pentru a evita thundering herd
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            
        return max(delay, 0.1)  # Minim 0.1 secunde

class RateLimitStrategy(RetryStrategy):
    """Strategie specială pentru rate limiting"""
    
    def __init__(self, max_attempts: int = 2, base_delay: float = 60.0):
        super().__init__(max_attempts, base_delay)
        
    def should_retry(self, error: Exception, attempt: int) -> bool:
        error_msg = str(error).lower()
        
        # Verifică dacă este cu adevărat rate limit error
        rate_limit_indicators = [
            'rate limit', 'too many requests', 'quota exceeded',
            'try again later', 'temporarily unavailable'
        ]
        
        if not any(indicator in error_msg for indicator in rate_limit_indicators):
            return False
            
        return attempt < self.max_attempts
        
    def get_delay(self, attempt: int) -> float:
        # Pentru rate limiting, delay-ul crește linear
        return self.base_delay * (attempt + 1)

class PlatformFallbackStrategy(RetryStrategy):
    """Strategie pentru încercarea pe alte platforme sau client types"""
    
    def __init__(self, max_attempts: int = 2, base_delay: float = 5.0):
        super().__init__(max_attempts, base_delay)
        
    def should_retry(self, error: Exception, attempt: int) -> bool:
        # Această strategie se ocupă cu fallback-uri, nu cu retry clasic
        return attempt < self.max_attempts
        
    def get_delay(self, attempt: int) -> float:
        return self.base_delay

class AdaptiveRetryStrategy(RetryStrategy):
    """Strategie adaptivă care se ajustează bazat pe istoric"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 2.0):
        super().__init__(max_attempts, base_delay)
        self.success_history = []  # Lista cu success rates recente
        self.error_history = {}    # Istoric de erori per tip
        
    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
            
        error_type = self._classify_error(error)
        
        # Ajustează strategia bazat pe istoricul de erori
        if error_type in self.error_history:
            error_count = self.error_history[error_type]
            if error_count > 10:  # Dacă avem multe erori de acest tip
                return attempt < max(1, self.max_attempts - 1)  # Reduce încercările
                
        return True
        
    def get_delay(self, attempt: int) -> float:
        # Ajustează delay-ul bazat pe success rate
        recent_success_rate = self._get_recent_success_rate()
        
        if recent_success_rate < 0.5:  # Success rate scăzut
            multiplier = 2.0  # Crește delay-ul
        elif recent_success_rate > 0.8:  # Success rate înalt
            multiplier = 0.5  # Reduce delay-ul
        else:
            multiplier = 1.0
            
        base_delay = min(self.base_delay ** attempt, 30.0) * multiplier
        return max(base_delay, 0.5)
        
    def record_attempt(self, success: bool, error: Optional[Exception] = None):
        """Înregistrează rezultatul unei încercări pentru learning"""
        self.success_history.append(success)
        
        # Păstrează doar ultimele 50 de încercări
        if len(self.success_history) > 50:
            self.success_history = self.success_history[-50:]
            
        if error:
            error_type = self._classify_error(error)
            self.error_history[error_type] = self.error_history.get(error_type, 0) + 1
            
    def _get_recent_success_rate(self) -> float:
        if not self.success_history:
            return 0.7  # Default optimistic
            
        recent_attempts = self.success_history[-10:]  # Ultimele 10
        return sum(recent_attempts) / len(recent_attempts)
        
    def _classify_error(self, error: Exception) -> str:
        error_msg = str(error).lower()
        
        if 'network' in error_msg or 'connection' in error_msg:
            return 'network'
        elif 'rate limit' in error_msg or 'quota' in error_msg:
            return 'rate_limit'
        elif 'parse' in error_msg or 'extract' in error_msg:
            return 'parsing'
        elif 'authentication' in error_msg or 'login' in error_msg:
            return 'auth'
        else:
            return 'unknown'

class RetryManager:
    """
    Manager centralizat pentru retry logic cu strategii multiple
    
    Funcționalități:
    - Strategii de retry diferite pentru diferite tipuri de erori
    - Monitoring și metrics pentru retry attempts
    - Configurare dynamică prin config.yaml
    - Learning adaptiv pentru optimizarea strategiilor
    """
    
    def __init__(self):
        self.strategies: Dict[ErrorType, RetryStrategy] = {}
        self.metrics = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'retry_by_type': {},
            'avg_retry_delay': 0.0
        }
        
        self._initialize_strategies()
        
        logger.info("🔄 Retry Manager initialized with {} strategies".format(len(self.strategies)))
        
    def _initialize_strategies(self):
        """Inițializează strategiile de retry"""
        
        # Încarcă configurațiile din config.yaml
        if config:
            retry_config = config.get('retry.strategies', {})
        else:
            retry_config = {}
            
        # Configurează strategiile default
        self.strategies = {
            ErrorType.NETWORK_ERROR: ExponentialBackoffStrategy(
                max_attempts=retry_config.get('network_error', {}).get('max_attempts', 3),
                base_delay=retry_config.get('network_error', {}).get('base_delay', 2),
                max_delay=retry_config.get('network_error', {}).get('max_delay', 30)
            ),
            
            ErrorType.RATE_LIMIT: RateLimitStrategy(
                max_attempts=retry_config.get('rate_limit', {}).get('max_attempts', 2),
                base_delay=retry_config.get('rate_limit', {}).get('delay', 60)
            ),
            
            ErrorType.PARSING_ERROR: NoRetryStrategy(),  # Nu reîncerca parsing errors
            
            ErrorType.PLATFORM_ERROR: PlatformFallbackStrategy(
                max_attempts=retry_config.get('platform_error', {}).get('max_attempts', 2),
                base_delay=retry_config.get('platform_error', {}).get('delay', 5)
            ),
            
            ErrorType.AUTHENTICATION_ERROR: LinearRetryStrategy(
                max_attempts=1,  # O singură reîncercare pentru auth
                delay=10.0
            ),
            
            ErrorType.QUOTA_EXCEEDED: RateLimitStrategy(
                max_attempts=1,
                base_delay=300.0  # 5 minute pentru quota
            ),
            
            ErrorType.TEMPORARY_UNAVAILABLE: ExponentialBackoffStrategy(
                max_attempts=3,
                base_delay=5.0,
                max_delay=60.0
            ),
            
            ErrorType.UNKNOWN_ERROR: AdaptiveRetryStrategy(
                max_attempts=2,
                base_delay=3.0
            )
        }
        
        logger.info("✅ Retry strategies configured")
        
    def classify_error(self, error: Exception) -> ErrorType:
        """
        Clasifică eroarea pentru a determina strategia de retry
        
        Args:
            error: Excepția de clasificat
            
        Returns:
            Tipul de eroare identificat
        """
        error_msg = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Network errors
        if any(keyword in error_msg for keyword in [
            'network', 'connection', 'timeout', 'unreachable', 'dns'
        ]) or any(keyword in error_type_name for keyword in [
            'connection', 'timeout', 'network'
        ]):
            return ErrorType.NETWORK_ERROR
            
        # Rate limiting
        if any(keyword in error_msg for keyword in [
            'rate limit', 'too many requests', 'quota exceeded',
            'try again later', '429'
        ]):
            return ErrorType.RATE_LIMIT
            
        # Parsing/extraction errors
        if any(keyword in error_msg for keyword in [
            'parse', 'extract', 'invalid format', 'corrupted data',
            'cannot parse', 'format not supported'
        ]):
            return ErrorType.PARSING_ERROR
            
        # Authentication errors
        if any(keyword in error_msg for keyword in [
            'authentication', 'login', 'unauthorized', 'forbidden',
            'access denied', '401', '403'
        ]):
            return ErrorType.AUTHENTICATION_ERROR
            
        # Quota exceeded
        if any(keyword in error_msg for keyword in [
            'quota', 'limit exceeded', 'daily limit', 'api limit'
        ]):
            return ErrorType.QUOTA_EXCEEDED
            
        # Temporary unavailable
        if any(keyword in error_msg for keyword in [
            'temporarily unavailable', 'service unavailable',
            'maintenance', 'down for maintenance', '503'
        ]):
            return ErrorType.TEMPORARY_UNAVAILABLE
            
        # Platform specific errors
        if any(keyword in error_msg for keyword in [
            'platform error', 'extractor', 'youtube', 'tiktok',
            'instagram', 'facebook', 'client error'
        ]):
            return ErrorType.PLATFORM_ERROR
            
        # Default to unknown
        return ErrorType.UNKNOWN_ERROR
        
    async def execute_with_retry(self, 
                                func: Callable,
                                *args,
                                error_type: Optional[ErrorType] = None,
                                **kwargs) -> Any:
        """
        Execută o funcție cu retry logic
        
        Args:
            func: Funcția de executat
            *args: Argumente pentru funcție
            error_type: Tipul de eroare așteptat (optional)
            **kwargs: Keyword arguments pentru funcție
            
        Returns:
            Rezultatul funcției
            
        Raises:
            Ultima eroare întâlnită dacă toate încercările eșuează
        """
        start_time = time.time()
        last_error = None
        
        # Dacă error_type nu este specificat, folosește strategia adaptivă
        strategy = self.strategies.get(error_type, self.strategies[ErrorType.UNKNOWN_ERROR])
        
        for attempt in range(strategy.get_max_attempts() + 1):
            try:
                logger.debug(f"🔄 Retry attempt {attempt + 1}/{strategy.get_max_attempts() + 1}")
                
                result = await func(*args, **kwargs)
                
                # Success! Înregistrează metrics
                if attempt > 0:
                    self.metrics['successful_retries'] += 1
                    self._record_retry_metrics(error_type, attempt, time.time() - start_time)
                    
                # Pentru adaptive strategy, înregistrează succesul
                if isinstance(strategy, AdaptiveRetryStrategy):
                    strategy.record_attempt(success=True)
                    
                logger.info(f"✅ Operation succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_error = e
                
                # Clasifică eroarea dacă nu a fost specificată
                if error_type is None:
                    detected_error_type = self.classify_error(e)
                    strategy = self.strategies.get(detected_error_type, strategy)
                    
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {str(e)[:100]}...")
                
                # Verifică dacă să reîncerce
                if not strategy.should_retry(e, attempt):
                    logger.info(f"🚫 Not retrying due to strategy rules")
                    break
                    
                if attempt < strategy.get_max_attempts():
                    delay = strategy.get_delay(attempt)
                    logger.info(f"⏳ Waiting {delay:.1f}s before retry {attempt + 2}...")
                    await asyncio.sleep(delay)
                    
                # Pentru adaptive strategy, înregistrează eșecul
                if isinstance(strategy, AdaptiveRetryStrategy):
                    strategy.record_attempt(success=False, error=e)
        
        # Toate încercările au eșuat
        self.metrics['failed_retries'] += 1
        self.metrics['total_retries'] += strategy.get_max_attempts()
        
        if error_type:
            error_type_key = error_type.value
        else:
            error_type_key = self.classify_error(last_error).value
            
        self.metrics['retry_by_type'][error_type_key] = \
            self.metrics['retry_by_type'].get(error_type_key, 0) + 1
        
        logger.error(f"❌ All {strategy.get_max_attempts() + 1} attempts failed")
        raise last_error
        
    def _record_retry_metrics(self, error_type: Optional[ErrorType], attempts: int, total_time: float):
        """Înregistrează metrici pentru retry attempts"""
        self.metrics['total_retries'] += attempts
        
        if error_type:
            error_type_key = error_type.value
            self.metrics['retry_by_type'][error_type_key] = \
                self.metrics['retry_by_type'].get(error_type_key, 0) + 1
                
        # Calculează average retry delay
        current_avg = self.metrics['avg_retry_delay']
        total_retries = self.metrics['total_retries']
        
        if total_retries > 0:
            self.metrics['avg_retry_delay'] = \
                (current_avg * (total_retries - attempts) + total_time) / total_retries
                
    def get_metrics(self) -> Dict[str, Any]:
        """Returnează metrici despre retry operations"""
        total_operations = self.metrics['successful_retries'] + self.metrics['failed_retries']
        success_rate = 0.0
        
        if total_operations > 0:
            success_rate = (self.metrics['successful_retries'] / total_operations) * 100
            
        return {
            'total_retry_operations': total_operations,
            'success_rate': round(success_rate, 2),
            'total_retries': self.metrics['total_retries'],
            'avg_retry_delay': round(self.metrics['avg_retry_delay'], 2),
            'retry_by_error_type': self.metrics['retry_by_type'],
            'strategies_count': len(self.strategies)
        }
        
    def update_strategy(self, error_type: ErrorType, strategy: RetryStrategy):
        """Actualizează strategia pentru un tip de eroare"""
        self.strategies[error_type] = strategy
        logger.info(f"📝 Updated retry strategy for {error_type.value}")

# Singleton instance pentru RetryManager
retry_manager = RetryManager()
