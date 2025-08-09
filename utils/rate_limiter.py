# utils/rate_limiter.py - Advanced Rate Limiting pentru Free Tier
# Versiunea: 2.0.0 - Arhitectura Modulară

import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict, deque
from enum import Enum
import hashlib

try:
    from utils.config import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)

class RateLimitType(Enum):
    """Tipuri de rate limiting"""
    PER_USER = "per_user"
    PER_PLATFORM = "per_platform" 
    PER_IP = "per_ip"
    GLOBAL = "global"
    PER_USER_PER_PLATFORM = "per_user_per_platform"

class RateLimitAlgorithm(Enum):
    """Algoritmi de rate limiting"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"

class RateLimitRule:
    """Regulă de rate limiting"""
    
    def __init__(self, 
                 limit: int,
                 window_seconds: int,
                 burst_allowance: int = 0,
                 algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW):
        self.limit = limit
        self.window_seconds = window_seconds
        self.burst_allowance = burst_allowance
        self.algorithm = algorithm
        self.created_at = time.time()

class TokenBucket:
    """Implementare Token Bucket Algorithm"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
        
    def can_consume(self, tokens: int = 1) -> bool:
        """Verifică dacă putem consuma tokens"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
        
    def _refill(self):
        """Reumple bucket-ul cu tokens"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculează tokens de adăugat
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
    def get_wait_time(self, tokens: int = 1) -> float:
        """Calculează timpul de așteptare pentru a avea suficiente tokens"""
        self._refill()
        
        if self.tokens >= tokens:
            return 0.0
            
        needed_tokens = tokens - self.tokens
        return needed_tokens / self.refill_rate

class SlidingWindow:
    """Implementare Sliding Window Algorithm"""
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = deque()
        
    def can_request(self) -> bool:
        """Verifică dacă putem face un request"""
        current_time = time.time()
        
        # Curăță request-urile vechi
        cutoff_time = current_time - self.window_seconds
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
            
        # Verifică limita
        if len(self.requests) < self.limit:
            self.requests.append(current_time)
            return True
            
        return False
        
    def get_wait_time(self) -> float:
        """Calculează timpul de așteptare"""
        if len(self.requests) < self.limit:
            return 0.0
            
        # Timpul până când cel mai vechi request expiră
        oldest_request = self.requests[0]
        return (oldest_request + self.window_seconds) - time.time()
        
    def get_remaining_quota(self) -> int:
        """Returnează quota rămasă"""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # Curăță request-urile vechi
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
            
        return max(0, self.limit - len(self.requests))

class FixedWindow:
    """Implementare Fixed Window Algorithm"""
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.current_window_start = time.time()
        self.current_count = 0
        
    def can_request(self) -> bool:
        """Verifică dacă putem face un request"""
        current_time = time.time()
        
        # Verifică dacă am trecut la o nouă fereastră
        if current_time >= self.current_window_start + self.window_seconds:
            self.current_window_start = current_time
            self.current_count = 0
            
        # Verifică limita
        if self.current_count < self.limit:
            self.current_count += 1
            return True
            
        return False
        
    def get_wait_time(self) -> float:
        """Calculează timpul de așteptare"""
        current_time = time.time()
        
        if self.current_count < self.limit:
            return 0.0
            
        # Timpul până la următoarea fereastră
        return (self.current_window_start + self.window_seconds) - current_time

class LeakyBucket:
    """Implementare Leaky Bucket Algorithm"""
    
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.current_volume = 0.0
        self.leak_rate = leak_rate  # units per second
        self.last_leak = time.time()
        
    def can_add(self, volume: int = 1) -> bool:
        """Verifică dacă putem adăuga în bucket"""
        self._leak()
        
        if self.current_volume + volume <= self.capacity:
            self.current_volume += volume
            return True
            
        return False
        
    def _leak(self):
        """Scurge din bucket"""
        now = time.time()
        elapsed = now - self.last_leak
        
        # Calculează cât să scurgem
        leak_amount = elapsed * self.leak_rate
        self.current_volume = max(0, self.current_volume - leak_amount)
        self.last_leak = now
        
    def get_wait_time(self, volume: int = 1) -> float:
        """Calculează timpul de așteptare"""
        self._leak()
        
        if self.current_volume + volume <= self.capacity:
            return 0.0
            
        # Timpul necesar pentru a scurge suficient
        needed_space = (self.current_volume + volume) - self.capacity
        return needed_space / self.leak_rate

class RateLimiter:
    """
    Advanced Rate Limiter optimizat pentru Free Tier hosting
    
    Caracteristici:
    - Multiple algoritmi (Token Bucket, Sliding Window, Fixed Window, Leaky Bucket)
    - Rate limiting per user, platform, IP, global
    - Burst protection
    - Dynamic rate limiting bazat pe load
    - Memory efficient pentru Free Tier
    - Auto-cleanup pentru a evita memory leaks
    """
    
    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.limiters: Dict[str, Dict[str, Any]] = defaultdict(dict)  # type -> key -> limiter
        
        # Statistici pentru monitoring
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'blocked_requests': 0,
            'rules_count': 0,
            'active_limiters': 0
        }
        
        # Configurare cleanup
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minute
        self.limiter_ttl = 3600  # 1 oră pentru inactive limiters
        
        self._initialize_default_rules()
        
        logger.info("🛡️ Rate Limiter initialized with {} default rules".format(len(self.rules)))
        
    def _initialize_default_rules(self):
        """Inițializează regulile default de rate limiting"""
        
        # Încarcă din configurație
        if config:
            rate_config = config.get('rate_limiting', {})
            enabled = rate_config.get('enabled', True)
            
            if not enabled:
                logger.info("⚠️ Rate limiting is disabled in configuration")
                return
        else:
            rate_config = {}
            
        # Regulile default optimizate pentru Free Tier
        default_rules = {
            # Per user global
            f"{RateLimitType.PER_USER.value}_global": RateLimitRule(
                limit=rate_config.get('per_user_per_minute', 5),
                window_seconds=60,
                burst_allowance=rate_config.get('burst_allowance', 3),
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW
            ),
            
            # Global pentru toate requesturile 
            f"{RateLimitType.GLOBAL.value}_all": RateLimitRule(
                limit=rate_config.get('global_per_minute', 50),  # Pentru Free Tier
                window_seconds=60,
                burst_allowance=10,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET
            ),
            
            # Per platformă pentru a evita spam pe o anumită platformă
            f"{RateLimitType.PER_PLATFORM.value}_downloads": RateLimitRule(
                limit=20,  # 20 downloads per minut per platformă
                window_seconds=60,
                burst_allowance=5,
                algorithm=RateLimitAlgorithm.LEAKY_BUCKET
            ),
            
            # Per user per platformă (mai restrictiv)
            f"{RateLimitType.PER_USER_PER_PLATFORM.value}_downloads": RateLimitRule(
                limit=3,  # 3 downloads per minut per user per platformă
                window_seconds=60,
                burst_allowance=2,
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW
            )
        }
        
        self.rules.update(default_rules)
        self.stats['rules_count'] = len(self.rules)
        
        logger.info("✅ Rate limiting rules configured")
        
    def add_rule(self, rule_id: str, rule: RateLimitRule):
        """Adaugă o regulă personalizată de rate limiting"""
        self.rules[rule_id] = rule
        self.stats['rules_count'] = len(self.rules)
        logger.info(f"📝 Added rate limiting rule: {rule_id}")
        
    def get_limiter_key(self, limiter_type: RateLimitType, 
                       user_id: Optional[Union[str, int]] = None,
                       platform: Optional[str] = None,
                       ip_address: Optional[str] = None) -> str:
        """Generează cheia pentru limiter bazată pe tip și parametri"""
        
        key_parts = [limiter_type.value]
        
        if limiter_type == RateLimitType.PER_USER:
            key_parts.append(str(user_id))
        elif limiter_type == RateLimitType.PER_PLATFORM:
            key_parts.append(str(platform))
        elif limiter_type == RateLimitType.PER_IP:
            key_parts.append(str(ip_address))
        elif limiter_type == RateLimitType.PER_USER_PER_PLATFORM:
            key_parts.extend([str(user_id), str(platform)])
        elif limiter_type == RateLimitType.GLOBAL:
            key_parts.append("all")
            
        return "_".join(key_parts)
        
    def _get_or_create_limiter(self, rule_id: str, key: str):
        """Obține sau creează un limiter pentru o cheie specifică"""
        
        if rule_id not in self.rules:
            logger.warning(f"⚠️ Rate limiting rule not found: {rule_id}")
            return None
            
        rule = self.rules[rule_id]
        
        # Verifică dacă limiterul există deja
        if key in self.limiters[rule_id]:
            limiter_data = self.limiters[rule_id][key]
            limiter_data['last_used'] = time.time()  # Update last used
            return limiter_data['limiter']
            
        # Creează un limiter nou bazat pe algoritm
        if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            limiter = TokenBucket(
                capacity=rule.limit + rule.burst_allowance,
                refill_rate=rule.limit / rule.window_seconds
            )
        elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            limiter = SlidingWindow(
                limit=rule.limit + rule.burst_allowance,
                window_seconds=rule.window_seconds
            )
        elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            limiter = FixedWindow(
                limit=rule.limit + rule.burst_allowance,
                window_seconds=rule.window_seconds
            )
        elif rule.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            limiter = LeakyBucket(
                capacity=rule.limit + rule.burst_allowance,
                leak_rate=rule.limit / rule.window_seconds
            )
        else:
            logger.error(f"❌ Unknown rate limiting algorithm: {rule.algorithm}")
            return None
            
        # Salvează limiterul
        self.limiters[rule_id][key] = {
            'limiter': limiter,
            'created_at': time.time(),
            'last_used': time.time()
        }
        
        self.stats['active_limiters'] = sum(len(limiters) for limiters in self.limiters.values())
        
        return limiter
        
    async def check_rate_limit(self, 
                             user_id: Optional[Union[str, int]] = None,
                             platform: Optional[str] = None,
                             ip_address: Optional[str] = None,
                             request_count: int = 1) -> Dict[str, Any]:
        """
        Verifică toate regulile de rate limiting aplicabile
        
        Args:
            user_id: ID-ul utilizatorului
            platform: Numele platformei
            ip_address: Adresa IP
            request_count: Numărul de request-uri (default: 1)
            
        Returns:
            Dict cu rezultatul verificării și informații despre limite
        """
        
        self.stats['total_requests'] += 1
        
        # Cleanup periodic
        await self._maybe_cleanup()
        
        # Verifică toate regulile aplicabile
        checks = []
        
        # Global check
        global_key = self.get_limiter_key(RateLimitType.GLOBAL)
        global_rule_id = f"{RateLimitType.GLOBAL.value}_all"
        checks.append((global_rule_id, global_key, "Global"))
        
        # Per user check
        if user_id is not None:
            user_key = self.get_limiter_key(RateLimitType.PER_USER, user_id=user_id)
            user_rule_id = f"{RateLimitType.PER_USER.value}_global"
            checks.append((user_rule_id, user_key, f"User {user_id}"))
            
        # Per platform check
        if platform is not None:
            platform_key = self.get_limiter_key(RateLimitType.PER_PLATFORM, platform=platform)
            platform_rule_id = f"{RateLimitType.PER_PLATFORM.value}_downloads"
            checks.append((platform_rule_id, platform_key, f"Platform {platform}"))
            
        # Per user per platform check
        if user_id is not None and platform is not None:
            user_platform_key = self.get_limiter_key(
                RateLimitType.PER_USER_PER_PLATFORM, 
                user_id=user_id, 
                platform=platform
            )
            user_platform_rule_id = f"{RateLimitType.PER_USER_PER_PLATFORM.value}_downloads"
            checks.append((user_platform_rule_id, user_platform_key, f"User {user_id} on {platform}"))
        
        # Execută toate verificările
        failed_checks = []
        wait_times = []
        
        for rule_id, key, description in checks:
            limiter = self._get_or_create_limiter(rule_id, key)
            
            if limiter is None:
                continue
                
            # Verifică limita
            if hasattr(limiter, 'can_consume'):  # Token Bucket
                allowed = limiter.can_consume(request_count)
                wait_time = limiter.get_wait_time(request_count) if not allowed else 0
            elif hasattr(limiter, 'can_request'):  # Sliding Window
                allowed = all(limiter.can_request() for _ in range(request_count))
                wait_time = limiter.get_wait_time() if not allowed else 0
            elif hasattr(limiter, 'can_add'):  # Leaky Bucket
                allowed = limiter.can_add(request_count)
                wait_time = limiter.get_wait_time(request_count) if not allowed else 0
            else:
                logger.error(f"❌ Unknown limiter type for rule {rule_id}")
                continue
                
            if not allowed:
                failed_checks.append({
                    'rule_id': rule_id,
                    'description': description,
                    'wait_time': wait_time
                })
                wait_times.append(wait_time)
                
        # Rezultatul final
        if failed_checks:
            self.stats['blocked_requests'] += 1
            max_wait_time = max(wait_times)
            
            return {
                'allowed': False,
                'wait_time': max_wait_time,
                'failed_checks': failed_checks,
                'retry_after': int(max_wait_time) + 1
            }
        else:
            self.stats['allowed_requests'] += 1
            
            return {
                'allowed': True,
                'wait_time': 0,
                'failed_checks': [],
                'retry_after': 0
            }
            
    async def _maybe_cleanup(self):
        """Curăță limiterii inactivi pentru a evita memory leaks"""
        current_time = time.time()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
            
        logger.debug("🧹 Starting rate limiter cleanup...")
        
        cleaned_count = 0
        
        for rule_id, limiters in list(self.limiters.items()):
            for key, limiter_data in list(limiters.items()):
                # Șterge limiterii vechi nefolosiți
                if current_time - limiter_data['last_used'] > self.limiter_ttl:
                    del limiters[key]
                    cleaned_count += 1
                    
            # Șterge categoriile goale
            if not limiters:
                del self.limiters[rule_id]
                
        self.last_cleanup = current_time
        self.stats['active_limiters'] = sum(len(limiters) for limiters in self.limiters.values())
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} inactive rate limiters")
            
    def get_quota_info(self, 
                      user_id: Optional[Union[str, int]] = None,
                      platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Obține informații despre quota și limite pentru un utilizator/platformă
        
        Args:
            user_id: ID-ul utilizatorului
            platform: Numele platformei
            
        Returns:
            Dict cu informații despre quota
        """
        
        quota_info = {}
        
        # Global quota
        global_key = self.get_limiter_key(RateLimitType.GLOBAL)
        global_rule_id = f"{RateLimitType.GLOBAL.value}_all"
        
        if global_rule_id in self.limiters and global_key in self.limiters[global_rule_id]:
            limiter = self.limiters[global_rule_id][global_key]['limiter']
            if hasattr(limiter, 'get_remaining_quota'):
                quota_info['global_remaining'] = limiter.get_remaining_quota()
                
        # User quota
        if user_id is not None:
            user_key = self.get_limiter_key(RateLimitType.PER_USER, user_id=user_id)
            user_rule_id = f"{RateLimitType.PER_USER.value}_global"
            
            if user_rule_id in self.limiters and user_key in self.limiters[user_rule_id]:
                limiter = self.limiters[user_rule_id][user_key]['limiter']
                if hasattr(limiter, 'get_remaining_quota'):
                    quota_info['user_remaining'] = limiter.get_remaining_quota()
                    
        return quota_info
        
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statistici despre rate limiting"""
        total_requests = self.stats['total_requests']
        
        if total_requests > 0:
            success_rate = (self.stats['allowed_requests'] / total_requests) * 100
            block_rate = (self.stats['blocked_requests'] / total_requests) * 100
        else:
            success_rate = 100.0
            block_rate = 0.0
            
        return {
            'total_requests': total_requests,
            'allowed_requests': self.stats['allowed_requests'],
            'blocked_requests': self.stats['blocked_requests'],
            'success_rate': round(success_rate, 2),
            'block_rate': round(block_rate, 2),
            'active_rules': self.stats['rules_count'],
            'active_limiters': self.stats['active_limiters'],
            'memory_usage_kb': self._estimate_memory_usage()
        }
        
    def _estimate_memory_usage(self) -> int:
        """Estimează memoria folosită de rate limiter (în KB)"""
        # Estimare simplă bazată pe numărul de limiteri activi
        base_memory = 10  # KB pentru structurile de bază
        per_limiter_memory = 0.5  # KB per limiter
        
        total_limiters = sum(len(limiters) for limiters in self.limiters.values())
        estimated_memory = base_memory + (total_limiters * per_limiter_memory)
        
        return int(estimated_memory)

# Singleton instance pentru RateLimiter
rate_limiter = RateLimiter()
