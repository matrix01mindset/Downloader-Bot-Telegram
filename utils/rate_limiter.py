
# utils/rate_limiter.py - Rate Limiting pentru protecție anti-spam
# Versiunea: 1.0.0

import time
import threading
from collections import defaultdict
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SimpleRateLimiter:
    """Rate limiter simplu pentru protecție anti-spam"""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Inițializează rate limiter-ul
        
        Args:
            max_requests: Numărul maxim de cereri permise
            time_window: Fereastra de timp în secunde
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
        logger.info(f"🛡️ Rate limiter initialized: {max_requests} requests per {time_window}s")
    
    def is_allowed(self, user_id: str) -> bool:
        """
        Verifică dacă utilizatorul poate face o cerere
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            True dacă cererea este permisă, False altfel
        """
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Curăță cererile vechi
            user_requests[:] = [req_time for req_time in user_requests 
                              if now - req_time < self.time_window]
            
            # Verifică limita
            if len(user_requests) >= self.max_requests:
                logger.warning(f"🚫 Rate limit exceeded for user {user_id}: {len(user_requests)}/{self.max_requests}")
                return False
            
            # Adaugă cererea curentă
            user_requests.append(now)
            logger.debug(f"✅ Request allowed for user {user_id}: {len(user_requests)}/{self.max_requests}")
            return True
    
    def get_remaining_requests(self, user_id: str) -> int:
        """
        Returnează numărul de cereri rămase pentru utilizator
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            Numărul de cereri rămase
        """
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            
            # Curăță cererile vechi
            user_requests[:] = [req_time for req_time in user_requests 
                              if now - req_time < self.time_window]
            
            return max(0, self.max_requests - len(user_requests))
    
    def get_reset_time(self, user_id: str) -> float:
        """
        Returnează timpul până la resetarea limitei pentru utilizator
        
        Args:
            user_id: ID-ul utilizatorului
            
        Returns:
            Timpul în secunde până la resetare
        """
        with self.lock:
            user_requests = self.requests[user_id]
            
            if not user_requests:
                return 0.0
            
            oldest_request = min(user_requests)
            reset_time = oldest_request + self.time_window - time.time()
            
            return max(0.0, reset_time)
    
    def clear_user(self, user_id: str):
        """
        Curăță istoricul pentru un utilizator specific
        
        Args:
            user_id: ID-ul utilizatorului
        """
        with self.lock:
            if user_id in self.requests:
                del self.requests[user_id]
                logger.info(f"🗑️ Cleared rate limit history for user {user_id}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Returnează statistici despre rate limiter
        
        Returns:
            Dicționar cu statistici
        """
        with self.lock:
            now = time.time()
            active_users = 0
            total_requests = 0
            
            for user_id, user_requests in self.requests.items():
                # Curăță cererile vechi
                user_requests[:] = [req_time for req_time in user_requests 
                                  if now - req_time < self.time_window]
                
                if user_requests:
                    active_users += 1
                    total_requests += len(user_requests)
            
            return {
                'active_users': active_users,
                'total_requests': total_requests,
                'max_requests_per_window': self.max_requests,
                'time_window_seconds': self.time_window
            }

# Instanță globală pentru folosire în aplicație
rate_limiter = SimpleRateLimiter(
    max_requests=5,  # 5 cereri
    time_window=60   # per minut
)
