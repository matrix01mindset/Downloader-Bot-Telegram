# utils/security/security_monitor.py - Sistem de Monitorizare și Protecție Securitate
# Versiunea: 1.0.0 - Protecție Avansată

import os
import time
import json
import hashlib
import logging
import asyncio
import requests
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Nivelurile de amenințare"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AttackType(Enum):
    """Tipurile de atacuri"""
    BRUTE_FORCE = "brute_force"
    DDoS = "ddos"
    INJECTION = "injection"
    PATH_TRAVERSAL = "path_traversal"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    TOKEN_THEFT = "token_theft"
    WEBHOOK_HIJACK = "webhook_hijack"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

@dataclass
class SecurityThreat:
    """O amenințare de securitate detectată"""
    threat_type: AttackType
    level: ThreatLevel
    source_ip: Optional[str]
    user_id: Optional[int]
    timestamp: datetime
    details: Dict[str, Any]
    mitigated: bool = False
    mitigation_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_type": self.threat_type.value,
            "level": self.level.value,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "mitigated": self.mitigated,
            "mitigation_actions": self.mitigation_actions
        }

@dataclass
class SecurityRule:
    """O regulă de securitate"""
    name: str
    description: str
    condition: Callable[[Dict[str, Any]], bool]
    threat_type: AttackType
    threat_level: ThreatLevel
    auto_mitigate: bool = True
    mitigation_actions: List[str] = field(default_factory=list)

class SecurityMonitor:
    """Monitor de securitate în timp real"""
    
    def __init__(self):
        self.threats: List[SecurityThreat] = []
        self.blocked_ips: Set[str] = set()
        self.blocked_users: Set[int] = set()
        self.suspicious_ips: Dict[str, int] = defaultdict(int)
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.webhook_integrity_checks: List[Dict[str, Any]] = []
        
        # Configurări
        self.max_requests_per_minute = 30
        self.max_failed_attempts = 5
        self.suspicious_threshold = 10
        self.webhook_check_interval = 300  # 5 minute
        
        # Reguli de securitate
        self.security_rules = self._initialize_security_rules()
        
        # Token și webhook pentru monitorizare
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.expected_webhook_url = os.getenv('WEBHOOK_URL')
        
        # Fișier pentru persistența amenințărilor
        self.threats_file = Path("logs/security_threats.json")
        self.threats_file.parent.mkdir(exist_ok=True)
        
        # Încarcă amenințările existente
        self._load_threats()
        
        # Thread pentru monitorizare continuă
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._continuous_monitoring, daemon=True)
        self.monitor_thread.start()
        
        logger.info("🛡️ SecurityMonitor initialized and active")
    
    def _initialize_security_rules(self) -> List[SecurityRule]:
        """Inițializează regulile de securitate"""
        rules = []
        
        # Regulă pentru detectarea brute force
        rules.append(SecurityRule(
            name="brute_force_detection",
            description="Detectează atacuri brute force",
            condition=lambda data: data.get('failed_attempts', 0) >= self.max_failed_attempts,
            threat_type=AttackType.BRUTE_FORCE,
            threat_level=ThreatLevel.HIGH,
            mitigation_actions=["block_ip", "alert_admin"]
        ))
        
        # Regulă pentru detectarea DDoS
        rules.append(SecurityRule(
            name="ddos_detection",
            description="Detectează atacuri DDoS",
            condition=lambda data: data.get('requests_per_minute', 0) > self.max_requests_per_minute,
            threat_type=AttackType.DDoS,
            threat_level=ThreatLevel.CRITICAL,
            mitigation_actions=["block_ip", "rate_limit", "alert_admin"]
        ))
        
        # Regulă pentru detectarea path traversal
        rules.append(SecurityRule(
            name="path_traversal_detection",
            description="Detectează atacuri path traversal",
            condition=lambda data: any(pattern in str(data.get('request_data', '')) 
                                     for pattern in ['../', '..\\', '%2e%2e', '%252e%252e']),
            threat_type=AttackType.PATH_TRAVERSAL,
            threat_level=ThreatLevel.HIGH,
            mitigation_actions=["block_ip", "log_incident"]
        ))
        
        # Regulă pentru detectarea injection
        rules.append(SecurityRule(
            name="injection_detection",
            description="Detectează atacuri de injecție",
            condition=lambda data: any(pattern in str(data.get('request_data', '')).lower() 
                                     for pattern in ['<script', 'javascript:', 'eval(', 'union select', "'; drop"]),
            threat_type=AttackType.INJECTION,
            threat_level=ThreatLevel.HIGH,
            mitigation_actions=["block_ip", "sanitize_input"]
        ))
        
        # Regulă pentru detectarea accesului neautorizat
        rules.append(SecurityRule(
            name="unauthorized_access_detection",
            description="Detectează încercări de acces neautorizat",
            condition=lambda data: data.get('unauthorized_attempt', False),
            threat_type=AttackType.UNAUTHORIZED_ACCESS,
            threat_level=ThreatLevel.MEDIUM,
            mitigation_actions=["log_incident", "increase_monitoring"]
        ))
        
        return rules
    
    def _load_threats(self):
        """Încarcă amenințările din fișier"""
        try:
            if self.threats_file.exists():
                with open(self.threats_file, 'r', encoding='utf-8') as f:
                    threats_data = json.load(f)
                
                for threat_data in threats_data:
                    threat = SecurityThreat(
                        threat_type=AttackType(threat_data['threat_type']),
                        level=ThreatLevel(threat_data['level']),
                        source_ip=threat_data.get('source_ip'),
                        user_id=threat_data.get('user_id'),
                        timestamp=datetime.fromisoformat(threat_data['timestamp']),
                        details=threat_data['details'],
                        mitigated=threat_data.get('mitigated', False),
                        mitigation_actions=threat_data.get('mitigation_actions', [])
                    )
                    self.threats.append(threat)
                
                logger.info(f"📊 Loaded {len(self.threats)} security threats from file")
        except Exception as e:
            logger.error(f"❌ Error loading threats: {e}")
    
    def _save_threats(self):
        """Salvează amenințările în fișier"""
        try:
            threats_data = [threat.to_dict() for threat in self.threats[-1000:]]  # Păstrează ultimele 1000
            
            with open(self.threats_file, 'w', encoding='utf-8') as f:
                json.dump(threats_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ Error saving threats: {e}")
    
    def analyze_request(self, request_data: Dict[str, Any]) -> Optional[SecurityThreat]:
        """Analizează o cerere pentru amenințări de securitate"""
        ip_address = request_data.get('ip_address')
        user_id = request_data.get('user_id')
        
        # Actualizează istoricul de cereri
        if ip_address:
            self.request_history[ip_address].append(time.time())
            
            # Calculează cereri pe minut
            now = time.time()
            recent_requests = [t for t in self.request_history[ip_address] if now - t < 60]
            request_data['requests_per_minute'] = len(recent_requests)
        
        # Verifică fiecare regulă de securitate
        for rule in self.security_rules:
            try:
                if rule.condition(request_data):
                    threat = SecurityThreat(
                        threat_type=rule.threat_type,
                        level=rule.threat_level,
                        source_ip=ip_address,
                        user_id=user_id,
                        timestamp=datetime.now(),
                        details={
                            'rule_triggered': rule.name,
                            'rule_description': rule.description,
                            'request_data': request_data
                        }
                    )
                    
                    self.threats.append(threat)
                    
                    # Auto-mitigare dacă este activată
                    if rule.auto_mitigate:
                        self._mitigate_threat(threat, rule.mitigation_actions)
                    
                    # Salvează amenințările
                    self._save_threats()
                    
                    logger.warning(f"🚨 Security threat detected: {rule.name} from {ip_address}")
                    return threat
                    
            except Exception as e:
                logger.error(f"❌ Error evaluating security rule {rule.name}: {e}")
        
        return None
    
    def _mitigate_threat(self, threat: SecurityThreat, actions: List[str]):
        """Aplică măsuri de mitigare pentru o amenințare"""
        applied_actions = []
        
        for action in actions:
            try:
                if action == "block_ip" and threat.source_ip:
                    self.blocked_ips.add(threat.source_ip)
                    applied_actions.append(f"Blocked IP: {threat.source_ip}")
                    logger.warning(f"🚫 Blocked IP: {threat.source_ip}")
                
                elif action == "block_user" and threat.user_id:
                    self.blocked_users.add(threat.user_id)
                    applied_actions.append(f"Blocked user: {threat.user_id}")
                    logger.warning(f"🚫 Blocked user: {threat.user_id}")
                
                elif action == "rate_limit" and threat.source_ip:
                    # Implementează rate limiting mai strict
                    self.suspicious_ips[threat.source_ip] += 1
                    applied_actions.append(f"Applied rate limiting to: {threat.source_ip}")
                
                elif action == "alert_admin":
                    self._send_admin_alert(threat)
                    applied_actions.append("Admin alert sent")
                
                elif action == "log_incident":
                    self._log_security_incident(threat)
                    applied_actions.append("Incident logged")
                
                elif action == "increase_monitoring":
                    # Mărește nivelul de monitorizare pentru această IP
                    if threat.source_ip:
                        self.suspicious_ips[threat.source_ip] += 1
                    applied_actions.append("Increased monitoring")
                
            except Exception as e:
                logger.error(f"❌ Error applying mitigation action {action}: {e}")
        
        threat.mitigated = True
        threat.mitigation_actions = applied_actions
    
    def _send_admin_alert(self, threat: SecurityThreat):
        """Trimite alertă către admin"""
        try:
            admin_user_id = os.getenv('ADMIN_USER_ID')
            if not admin_user_id or not self.telegram_token:
                return
            
            message = f"🚨 SECURITY ALERT 🚨\n\n"
            message += f"Threat Type: {threat.threat_type.value}\n"
            message += f"Level: {threat.level.value}\n"
            message += f"Source IP: {threat.source_ip}\n"
            message += f"User ID: {threat.user_id}\n"
            message += f"Time: {threat.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            message += f"Details: {json.dumps(threat.details, indent=2)}"
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': admin_user_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                logger.info("📧 Admin alert sent successfully")
            else:
                logger.error(f"❌ Failed to send admin alert: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error sending admin alert: {e}")
    
    def _log_security_incident(self, threat: SecurityThreat):
        """Înregistrează un incident de securitate"""
        try:
            incident_file = Path("logs/security_incidents.log")
            incident_file.parent.mkdir(exist_ok=True)
            
            with open(incident_file, 'a', encoding='utf-8') as f:
                incident_data = {
                    'timestamp': threat.timestamp.isoformat(),
                    'threat_type': threat.threat_type.value,
                    'level': threat.level.value,
                    'source_ip': threat.source_ip,
                    'user_id': threat.user_id,
                    'details': threat.details
                }
                f.write(json.dumps(incident_data) + '\n')
                
        except Exception as e:
            logger.error(f"❌ Error logging security incident: {e}")
    
    def check_webhook_integrity(self) -> bool:
        """Verifică integritatea webhook-ului"""
        try:
            if not self.telegram_token:
                return False
            
            response = requests.get(
                f"https://api.telegram.org/bot{self.telegram_token}/getWebhookInfo",
                timeout=10
            )
            
            if response.status_code == 200:
                webhook_info = response.json()
                
                if webhook_info.get('ok'):
                    current_url = webhook_info['result'].get('url', '')
                    
                    check_result = {
                        'timestamp': datetime.now().isoformat(),
                        'expected_url': self.expected_webhook_url,
                        'current_url': current_url,
                        'is_valid': current_url == self.expected_webhook_url
                    }
                    
                    self.webhook_integrity_checks.append(check_result)
                    
                    # Păstrează doar ultimele 100 de verificări
                    if len(self.webhook_integrity_checks) > 100:
                        self.webhook_integrity_checks = self.webhook_integrity_checks[-100:]
                    
                    if not check_result['is_valid']:
                        # Webhook compromis!
                        threat = SecurityThreat(
                            threat_type=AttackType.WEBHOOK_HIJACK,
                            level=ThreatLevel.CRITICAL,
                            source_ip=None,
                            user_id=None,
                            timestamp=datetime.now(),
                            details={
                                'expected_url': self.expected_webhook_url,
                                'actual_url': current_url,
                                'webhook_info': webhook_info['result']
                            }
                        )
                        
                        self.threats.append(threat)
                        self._mitigate_threat(threat, ["alert_admin", "log_incident"])
                        
                        logger.critical(f"🚨 WEBHOOK HIJACKED! Expected: {self.expected_webhook_url}, Got: {current_url}")
                        return False
                    
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error checking webhook integrity: {e}")
            return False
    
    def _continuous_monitoring(self):
        """Monitorizare continuă în background"""
        logger.info("🔍 Starting continuous security monitoring")
        
        while self.monitoring_active:
            try:
                # Verifică integritatea webhook-ului
                self.check_webhook_integrity()
                
                # Curăță datele vechi
                self._cleanup_old_data()
                
                # Așteaptă până la următoarea verificare
                time.sleep(self.webhook_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in continuous monitoring: {e}")
                time.sleep(60)  # Așteaptă 1 minut înainte de retry
    
    def _cleanup_old_data(self):
        """Curăță datele vechi"""
        try:
            # Curăță amenințările mai vechi de 30 de zile
            cutoff_date = datetime.now() - timedelta(days=30)
            self.threats = [t for t in self.threats if t.timestamp > cutoff_date]
            
            # Curăță istoricul de cereri mai vechi de 1 oră
            cutoff_time = time.time() - 3600
            for ip, requests in self.request_history.items():
                while requests and requests[0] < cutoff_time:
                    requests.popleft()
            
            # Resetează contoarele de IP-uri suspecte
            for ip in list(self.suspicious_ips.keys()):
                if self.suspicious_ips[ip] > 0:
                    self.suspicious_ips[ip] = max(0, self.suspicious_ips[ip] - 1)
                if self.suspicious_ips[ip] == 0:
                    del self.suspicious_ips[ip]
                    
        except Exception as e:
            logger.error(f"❌ Error in cleanup: {e}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Verifică dacă o IP este blocată"""
        return ip_address in self.blocked_ips
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Verifică dacă un utilizator este blocat"""
        return user_id in self.blocked_users
    
    def unblock_ip(self, ip_address: str):
        """Deblochează o IP"""
        self.blocked_ips.discard(ip_address)
        logger.info(f"✅ Unblocked IP: {ip_address}")
    
    def unblock_user(self, user_id: int):
        """Deblochează un utilizator"""
        self.blocked_users.discard(user_id)
        logger.info(f"✅ Unblocked user: {user_id}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Returnează statusul de securitate"""
        recent_threats = [t for t in self.threats if t.timestamp > datetime.now() - timedelta(hours=24)]
        
        threat_counts = defaultdict(int)
        for threat in recent_threats:
            threat_counts[threat.threat_type.value] += 1
        
        return {
            "monitoring_active": self.monitoring_active,
            "total_threats": len(self.threats),
            "recent_threats_24h": len(recent_threats),
            "blocked_ips": len(self.blocked_ips),
            "blocked_users": len(self.blocked_users),
            "suspicious_ips": len(self.suspicious_ips),
            "threat_breakdown": dict(threat_counts),
            "last_webhook_check": self.webhook_integrity_checks[-1] if self.webhook_integrity_checks else None,
            "webhook_integrity_ok": self.webhook_integrity_checks[-1]['is_valid'] if self.webhook_integrity_checks else None
        }
    
    def get_recent_threats(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returnează amenințările recente"""
        recent_threats = sorted(self.threats, key=lambda t: t.timestamp, reverse=True)[:limit]
        return [threat.to_dict() for threat in recent_threats]
    
    def stop_monitoring(self):
        """Oprește monitorizarea"""
        self.monitoring_active = False
        logger.info("🛑 Security monitoring stopped")

# Instanță globală
security_monitor = SecurityMonitor()

# Funcții de conveniență
def analyze_request(request_data: Dict[str, Any]) -> Optional[SecurityThreat]:
    """Analizează o cerere pentru amenințări"""
    return security_monitor.analyze_request(request_data)

def is_ip_blocked(ip_address: str) -> bool:
    """Verifică dacă o IP este blocată"""
    return security_monitor.is_ip_blocked(ip_address)

def is_user_blocked(user_id: int) -> bool:
    """Verifică dacă un utilizator este blocat"""
    return security_monitor.is_user_blocked(user_id)

def check_webhook_integrity() -> bool:
    """Verifică integritatea webhook-ului"""
    return security_monitor.check_webhook_integrity()