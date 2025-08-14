# utils/security/auth_manager.py - Sistem de Autentificare și Autorizare Avansat
# Versiunea: 1.0.0 - Securitate Robustă

import os
import time
import hmac
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """Rolurile utilizatorilor"""
    ADMIN = "admin"
    USER = "user"
    RESTRICTED = "restricted"
    BANNED = "banned"

class AuthLevel(Enum):
    """Nivelurile de autentificare"""
    NONE = "none"
    BASIC = "basic"
    ENHANCED = "enhanced"
    STRICT = "strict"

@dataclass
class UserSession:
    """Sesiunea unui utilizator"""
    user_id: int
    role: UserRole
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    session_token: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    failed_attempts: int = 0
    is_active: bool = True
    
    def is_expired(self, timeout: int = 3600) -> bool:
        """Verifică dacă sesiunea a expirat"""
        return (datetime.now() - self.last_activity).total_seconds() > timeout
    
    def update_activity(self):
        """Actualizează ultima activitate"""
        self.last_activity = datetime.now()

@dataclass
class SecurityEvent:
    """Eveniment de securitate"""
    event_type: str
    user_id: Optional[int]
    ip_address: Optional[str]
    timestamp: datetime
    details: Dict[str, Any]
    severity: str = "info"  # info, warning, critical

class AuthenticationManager:
    """Manager pentru autentificare și autorizare"""
    
    def __init__(self, auth_level: AuthLevel = AuthLevel.ENHANCED):
        self.auth_level = auth_level
        self.sessions: Dict[int, UserSession] = {}
        self.security_events: List[SecurityEvent] = []
        self.rate_limits: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Set[str] = set()
        self.blocked_users: Set[int] = set()
        
        # Configurări de securitate
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minute
        self.session_timeout = 3600  # 1 oră
        self.rate_limit_window = 60  # 1 minut
        self.max_requests_per_window = 20
        
        # Utilizatori autorizați (din variabile de mediu)
        self.authorized_users = self._load_authorized_users()
        self.admin_users = self._load_admin_users()
        
        # Secret pentru token-uri
        self.secret_key = os.getenv('AUTH_SECRET_KEY', secrets.token_hex(32))
        
        logger.info(f"🔐 AuthenticationManager initialized with level: {auth_level.value}")
        logger.info(f"📊 Authorized users: {len(self.authorized_users)}, Admins: {len(self.admin_users)}")
    
    def _load_authorized_users(self) -> Set[int]:
        """Încarcă utilizatorii autorizați din variabilele de mediu"""
        users_str = os.getenv('AUTHORIZED_USERS', '')
        if not users_str:
            return set()
        
        try:
            user_ids = [int(uid.strip()) for uid in users_str.split(',') if uid.strip()]
            return set(user_ids)
        except ValueError as e:
            logger.error(f"❌ Error parsing authorized users: {e}")
            return set()
    
    def _load_admin_users(self) -> Set[int]:
        """Încarcă utilizatorii admin din variabilele de mediu"""
        admins_str = os.getenv('ADMIN_USERS', '')
        if not admins_str:
            return set()
        
        try:
            admin_ids = [int(uid.strip()) for uid in admins_str.split(',') if uid.strip()]
            return set(admin_ids)
        except ValueError as e:
            logger.error(f"❌ Error parsing admin users: {e}")
            return set()
    
    def _generate_session_token(self, user_id: int) -> str:
        """Generează un token de sesiune securizat"""
        timestamp = str(int(time.time()))
        data = f"{user_id}:{timestamp}:{secrets.token_hex(16)}"
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{data}:{signature}"
    
    def _verify_session_token(self, token: str, user_id: int) -> bool:
        """Verifică validitatea unui token de sesiune"""
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return False
            
            token_user_id, timestamp, nonce, signature = parts
            
            if int(token_user_id) != user_id:
                return False
            
            # Verifică dacă token-ul nu a expirat (24 ore)
            if int(time.time()) - int(timestamp) > 86400:
                return False
            
            # Verifică semnătura
            data = f"{token_user_id}:{timestamp}:{nonce}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ Invalid session token format: {e}")
            return False
    
    def _log_security_event(self, event_type: str, user_id: Optional[int] = None,
                           ip_address: Optional[str] = None, details: Dict[str, Any] = None,
                           severity: str = "info"):
        """Înregistrează un eveniment de securitate"""
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.now(),
            details=details or {},
            severity=severity
        )
        
        self.security_events.append(event)
        
        # Păstrează doar ultimele 1000 de evenimente
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Log în funcție de severitate
        log_msg = f"🔒 Security Event: {event_type} - User: {user_id} - IP: {ip_address}"
        if severity == "critical":
            logger.critical(log_msg)
        elif severity == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Verifică rate limiting"""
        now = time.time()
        requests = self.rate_limits[identifier]
        
        # Curăță cererile vechi
        requests[:] = [req_time for req_time in requests 
                      if now - req_time < self.rate_limit_window]
        
        if len(requests) >= self.max_requests_per_window:
            return False
        
        requests.append(now)
        return True
    
    def authenticate_user(self, user_id: int, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[UserSession]]:
        """Autentifică un utilizator"""
        
        # Verifică dacă IP-ul este blocat
        if ip_address and ip_address in self.blocked_ips:
            self._log_security_event(
                "blocked_ip_attempt",
                user_id=user_id,
                ip_address=ip_address,
                severity="warning"
            )
            return False, "IP address is blocked", None
        
        # Verifică dacă utilizatorul este blocat
        if user_id in self.blocked_users:
            self._log_security_event(
                "blocked_user_attempt",
                user_id=user_id,
                ip_address=ip_address,
                severity="warning"
            )
            return False, "User is blocked", None
        
        # Verifică rate limiting
        rate_limit_key = f"user_{user_id}" if user_id else f"ip_{ip_address}"
        if not self._check_rate_limit(rate_limit_key):
            self._log_security_event(
                "rate_limit_exceeded",
                user_id=user_id,
                ip_address=ip_address,
                severity="warning"
            )
            return False, "Rate limit exceeded", None
        
        # Determină rolul utilizatorului
        if user_id in self.admin_users:
            role = UserRole.ADMIN
            permissions = {"download", "admin", "manage_users", "view_logs"}
        elif user_id in self.authorized_users or self.auth_level == AuthLevel.NONE:
            role = UserRole.USER
            permissions = {"download"}
        else:
            # Pentru niveluri de securitate stricte, respinge utilizatorii neautorizați
            if self.auth_level in [AuthLevel.ENHANCED, AuthLevel.STRICT]:
                self._log_security_event(
                    "unauthorized_access_attempt",
                    user_id=user_id,
                    ip_address=ip_address,
                    severity="warning"
                )
                return False, "User not authorized", None
            else:
                role = UserRole.RESTRICTED
                permissions = set()
        
        # Creează sesiunea
        session = UserSession(
            user_id=user_id,
            role=role,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            ip_address=ip_address,
            session_token=self._generate_session_token(user_id),
            permissions=permissions
        )
        
        self.sessions[user_id] = session
        
        self._log_security_event(
            "user_authenticated",
            user_id=user_id,
            ip_address=ip_address,
            details={"role": role.value, "permissions": list(permissions)}
        )
        
        return True, "Authentication successful", session
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """Verifică dacă utilizatorul are o anumită permisiune"""
        session = self.sessions.get(user_id)
        if not session or not session.is_active:
            return False
        
        if session.is_expired(self.session_timeout):
            self.logout_user(user_id)
            return False
        
        session.update_activity()
        return permission in session.permissions
    
    def logout_user(self, user_id: int):
        """Deconectează un utilizator"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            session.is_active = False
            
            self._log_security_event(
                "user_logout",
                user_id=user_id,
                ip_address=session.ip_address
            )
            
            del self.sessions[user_id]
    
    def block_user(self, user_id: int, reason: str = "Security violation"):
        """Blochează un utilizator"""
        self.blocked_users.add(user_id)
        self.logout_user(user_id)
        
        self._log_security_event(
            "user_blocked",
            user_id=user_id,
            details={"reason": reason},
            severity="critical"
        )
        
        logger.warning(f"🚫 User {user_id} blocked: {reason}")
    
    def block_ip(self, ip_address: str, reason: str = "Security violation"):
        """Blochează o adresă IP"""
        self.blocked_ips.add(ip_address)
        
        # Deconectează toate sesiunile de la această IP
        for user_id, session in list(self.sessions.items()):
            if session.ip_address == ip_address:
                self.logout_user(user_id)
        
        self._log_security_event(
            "ip_blocked",
            ip_address=ip_address,
            details={"reason": reason},
            severity="critical"
        )
        
        logger.warning(f"🚫 IP {ip_address} blocked: {reason}")
    
    def cleanup_expired_sessions(self):
        """Curăță sesiunile expirate"""
        expired_users = []
        for user_id, session in self.sessions.items():
            if session.is_expired(self.session_timeout):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.logout_user(user_id)
        
        if expired_users:
            logger.info(f"🧹 Cleaned up {len(expired_users)} expired sessions")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Returnează statistici de securitate"""
        active_sessions = len([s for s in self.sessions.values() if s.is_active])
        
        event_counts = defaultdict(int)
        for event in self.security_events[-100:]:  # Ultimele 100 evenimente
            event_counts[event.event_type] += 1
        
        return {
            "active_sessions": active_sessions,
            "blocked_users": len(self.blocked_users),
            "blocked_ips": len(self.blocked_ips),
            "total_events": len(self.security_events),
            "recent_events": dict(event_counts),
            "auth_level": self.auth_level.value,
            "authorized_users_count": len(self.authorized_users),
            "admin_users_count": len(self.admin_users)
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returnează evenimentele recente de securitate"""
        recent_events = self.security_events[-limit:]
        return [
            {
                "type": event.event_type,
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
                "severity": event.severity
            }
            for event in recent_events
        ]

# Instanță globală
auth_manager = AuthenticationManager()

# Funcții de conveniență
def authenticate_user(user_id: int, ip_address: Optional[str] = None) -> Tuple[bool, str, Optional[UserSession]]:
    """Funcție de conveniență pentru autentificare"""
    return auth_manager.authenticate_user(user_id, ip_address)

def check_permission(user_id: int, permission: str) -> bool:
    """Funcție de conveniență pentru verificarea permisiunilor"""
    return auth_manager.check_permission(user_id, permission)

def require_permission(permission: str):
    """Decorator pentru a necesita o anumită permisiune"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Încearcă să extragă user_id din argumentele funcției
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            
            if not user_id or not check_permission(user_id, permission):
                raise PermissionError(f"Permission '{permission}' required")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Cleanup periodic
async def periodic_cleanup():
    """Curățare periodică a sesiunilor expirate"""
    while True:
        try:
            auth_manager.cleanup_expired_sessions()
            await asyncio.sleep(300)  # La fiecare 5 minute
        except Exception as e:
            logger.error(f"❌ Error in periodic cleanup: {e}")
            await asyncio.sleep(60)