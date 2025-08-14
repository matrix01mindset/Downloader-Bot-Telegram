# utils/security/input_sanitizer.py - Sistem de Sanitizare și Validare Input
# Versiunea: 1.0.0 - Protecție Avansată

import re
import html
import urllib.parse
import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Nivelurile de validare"""
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"

class InputType(Enum):
    """Tipurile de input"""
    URL = "url"
    TEXT = "text"
    USERNAME = "username"
    FILENAME = "filename"
    PATH = "path"
    JSON = "json"
    HTML = "html"
    SQL = "sql"
    COMMAND = "command"
    EMAIL = "email"
    PHONE = "phone"

@dataclass
class ValidationResult:
    """Rezultatul validării"""
    is_valid: bool
    sanitized_value: Any
    threats_detected: List[str]
    risk_score: int  # 0-100
    recommendations: List[str]

class InputSanitizer:
    """Sistem avansat de sanitizare și validare input"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.validation_level = validation_level
        
        # Patterns pentru detectarea atacurilor
        self.sql_injection_patterns = [
            r"('|(\-\-)|(;)|(\||\|)|(\*|\*))",
            r"(union|select|insert|delete|update|drop|create|alter|exec|execute)",
            r"(script|javascript|vbscript|onload|onerror|onclick)",
            r"(\<|\>|\&lt\;|\&gt\;)",
            r"(eval\(|expression\(|url\(|import\()"
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<style[^>]*>.*?</style>",
            r"expression\(",
            r"url\(\s*['\"]?\s*javascript:",
            r"@import"
        ]
        
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"%252e%252e%252f",
            r"%c0%ae%c0%ae%c0%af",
            r"\\\\?\\",
            r"/etc/passwd",
            r"/proc/",
            r"C:\\Windows",
            r"..\\..\\windows"
        ]
        
        self.command_injection_patterns = [
            r"[;&|`$(){}\[\]]",
            r"(rm|del|format|fdisk|kill|shutdown|reboot)",
            r"(wget|curl|nc|netcat|telnet|ssh)",
            r"(cat|type|more|less|head|tail)",
            r"(echo|print|printf).*[>&|]",
            r"\$\(.*\)",
            r"`.*`",
            r"\|\||"
        ]
        
        # Extensii periculoase
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.msi', '.run',
            '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl', '.sh',
            '.ps1', '.psm1', '.psd1', '.ps1xml', '.psc1', '.psc2'
        }
        
        # Caractere periculoase
        self.dangerous_chars = {
            '<', '>', '&', '"', "'", '`', '$', '(', ')', '{', '}',
            '[', ']', ';', '|', '&', '*', '?', '~', '^', '!'
        }
        
        logger.info(f"🛡️ InputSanitizer initialized with {validation_level.value} validation level")
    
    def sanitize_and_validate(self, value: Any, input_type: InputType, 
                            max_length: Optional[int] = None) -> ValidationResult:
        """Sanitizează și validează un input"""
        threats_detected = []
        recommendations = []
        risk_score = 0
        
        if value is None:
            return ValidationResult(
                is_valid=True,
                sanitized_value=None,
                threats_detected=[],
                risk_score=0,
                recommendations=[]
            )
        
        # Convertește la string pentru procesare
        original_value = str(value)
        sanitized_value = original_value
        
        try:
            # Verifică lungimea
            if max_length and len(original_value) > max_length:
                threats_detected.append(f"Input too long: {len(original_value)} > {max_length}")
                risk_score += 20
                sanitized_value = sanitized_value[:max_length]
                recommendations.append("Input truncated to maximum length")
            
            # Detectează encoding suspicious
            if self._detect_suspicious_encoding(original_value):
                threats_detected.append("Suspicious encoding detected")
                risk_score += 30
                recommendations.append("Review input encoding")
            
            # Validare specifică tipului
            if input_type == InputType.URL:
                sanitized_value, url_threats, url_risk = self._sanitize_url(sanitized_value)
                threats_detected.extend(url_threats)
                risk_score += url_risk
            
            elif input_type == InputType.FILENAME:
                sanitized_value, file_threats, file_risk = self._sanitize_filename(sanitized_value)
                threats_detected.extend(file_threats)
                risk_score += file_risk
            
            elif input_type == InputType.PATH:
                sanitized_value, path_threats, path_risk = self._sanitize_path(sanitized_value)
                threats_detected.extend(path_threats)
                risk_score += path_risk
            
            elif input_type == InputType.HTML:
                sanitized_value, html_threats, html_risk = self._sanitize_html(sanitized_value)
                threats_detected.extend(html_threats)
                risk_score += html_risk
            
            elif input_type == InputType.JSON:
                sanitized_value, json_threats, json_risk = self._sanitize_json(sanitized_value)
                threats_detected.extend(json_threats)
                risk_score += json_risk
            
            elif input_type == InputType.COMMAND:
                sanitized_value, cmd_threats, cmd_risk = self._sanitize_command(sanitized_value)
                threats_detected.extend(cmd_threats)
                risk_score += cmd_risk
            
            elif input_type == InputType.EMAIL:
                sanitized_value, email_threats, email_risk = self._sanitize_email(sanitized_value)
                threats_detected.extend(email_threats)
                risk_score += email_risk
            
            # Detectează SQL injection
            sql_threats, sql_risk = self._detect_sql_injection(sanitized_value)
            threats_detected.extend(sql_threats)
            risk_score += sql_risk
            
            # Detectează XSS
            xss_threats, xss_risk = self._detect_xss(sanitized_value)
            threats_detected.extend(xss_threats)
            risk_score += xss_risk
            
            # Detectează path traversal
            traversal_threats, traversal_risk = self._detect_path_traversal(sanitized_value)
            threats_detected.extend(traversal_threats)
            risk_score += traversal_risk
            
            # Detectează command injection
            cmd_inj_threats, cmd_inj_risk = self._detect_command_injection(sanitized_value)
            threats_detected.extend(cmd_inj_threats)
            risk_score += cmd_inj_risk
            
            # Aplicare sanitizare finală bazată pe nivel
            if self.validation_level == ValidationLevel.PARANOID:
                sanitized_value = self._paranoid_sanitize(sanitized_value)
                recommendations.append("Applied paranoid sanitization")
            elif self.validation_level == ValidationLevel.STRICT:
                sanitized_value = self._strict_sanitize(sanitized_value)
                recommendations.append("Applied strict sanitization")
            
            # Determină dacă input-ul este valid
            is_valid = True
            if self.validation_level == ValidationLevel.PARANOID and risk_score > 10:
                is_valid = False
            elif self.validation_level == ValidationLevel.STRICT and risk_score > 30:
                is_valid = False
            elif risk_score > 70:
                is_valid = False
            
            # Limitează risk score la 100
            risk_score = min(risk_score, 100)
            
            if threats_detected:
                logger.warning(f"🚨 Input validation threats detected: {threats_detected}")
            
            return ValidationResult(
                is_valid=is_valid,
                sanitized_value=sanitized_value,
                threats_detected=threats_detected,
                risk_score=risk_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"❌ Error in input sanitization: {e}")
            return ValidationResult(
                is_valid=False,
                sanitized_value=original_value,
                threats_detected=[f"Sanitization error: {str(e)}"],
                risk_score=100,
                recommendations=["Manual review required"]
            )
    
    def _detect_suspicious_encoding(self, value: str) -> bool:
        """Detectează encoding suspicious"""
        try:
            # Verifică pentru multiple encoding
            decoded_once = urllib.parse.unquote(value)
            decoded_twice = urllib.parse.unquote(decoded_once)
            
            if decoded_once != decoded_twice:
                return True
            
            # Verifică pentru caractere de control
            if any(ord(c) < 32 and c not in '\t\n\r' for c in value):
                return True
            
            # Verifică pentru secvențe Unicode suspicious
            if r'\u' in value.lower() or r'\x' in value.lower():
                return True
                
            return False
            
        except Exception:
            return True
    
    def _sanitize_url(self, url: str) -> Tuple[str, List[str], int]:
        """Sanitizează și validează URL"""
        threats = []
        risk_score = 0
        
        try:
            # Verifică scheme-uri periculoase
            dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
            url_lower = url.lower()
            
            for scheme in dangerous_schemes:
                if url_lower.startswith(scheme):
                    threats.append(f"Dangerous URL scheme: {scheme}")
                    risk_score += 50
            
            # Verifică pentru caractere periculoase în URL
            if any(char in url for char in ['<', '>', '"', "'", '`']):
                threats.append("Dangerous characters in URL")
                risk_score += 30
            
            # Sanitizează URL
            sanitized = urllib.parse.quote(url, safe=':/?#[]@!$&\'()*+,;=')
            
            return sanitized, threats, risk_score
            
        except Exception as e:
            return url, [f"URL sanitization error: {str(e)}"], 50
    
    def _sanitize_filename(self, filename: str) -> Tuple[str, List[str], int]:
        """Sanitizează și validează nume de fișier"""
        threats = []
        risk_score = 0
        
        try:
            # Verifică extensii periculoase
            file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
            if file_ext in self.dangerous_extensions:
                threats.append(f"Dangerous file extension: {file_ext}")
                risk_score += 70
            
            # Verifică caractere periculoase
            dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ';', '&']
            for char in dangerous_chars:
                if char in filename:
                    threats.append(f"Dangerous character in filename: {char}")
                    risk_score += 20
            
            # Sanitizează filename
            sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
            
            # Verifică pentru nume rezervate Windows
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                            'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
            
            name_without_ext = sanitized.split('.')[0].upper()
            if name_without_ext in reserved_names:
                threats.append(f"Reserved filename: {name_without_ext}")
                risk_score += 40
                sanitized = f"safe_{sanitized}"
            
            return sanitized, threats, risk_score
            
        except Exception as e:
            return filename, [f"Filename sanitization error: {str(e)}"], 50
    
    def _sanitize_path(self, path: str) -> Tuple[str, List[str], int]:
        """Sanitizează și validează cale"""
        threats = []
        risk_score = 0
        
        try:
            # Normalizează calea
            import os.path
            normalized = os.path.normpath(path)
            
            # Verifică pentru path traversal
            if '..' in normalized:
                threats.append("Path traversal attempt detected")
                risk_score += 80
            
            # Verifică pentru căi absolute periculoase
            dangerous_paths = ['/etc/', '/proc/', '/sys/', 'C:\\Windows\\', 'C:\\System32\\']
            for dangerous_path in dangerous_paths:
                if dangerous_path.lower() in normalized.lower():
                    threats.append(f"Access to dangerous path: {dangerous_path}")
                    risk_score += 90
            
            return normalized, threats, risk_score
            
        except Exception as e:
            return path, [f"Path sanitization error: {str(e)}"], 50
    
    def _sanitize_html(self, html_content: str) -> Tuple[str, List[str], int]:
        """Sanitizează conținut HTML"""
        threats = []
        risk_score = 0
        
        try:
            # Escape HTML
            sanitized = html.escape(html_content)
            
            # Verifică pentru tag-uri periculoase
            dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'meta', 'style']
            for tag in dangerous_tags:
                if f'<{tag}' in html_content.lower():
                    threats.append(f"Dangerous HTML tag: {tag}")
                    risk_score += 40
            
            return sanitized, threats, risk_score
            
        except Exception as e:
            return html_content, [f"HTML sanitization error: {str(e)}"], 50
    
    def _sanitize_json(self, json_str: str) -> Tuple[str, List[str], int]:
        """Sanitizează și validează JSON"""
        threats = []
        risk_score = 0
        
        try:
            # Încearcă să parseze JSON
            parsed = json.loads(json_str)
            
            # Verifică pentru structuri prea adânci
            def check_depth(obj, current_depth=0, max_depth=10):
                if current_depth > max_depth:
                    return True
                if isinstance(obj, dict):
                    return any(check_depth(v, current_depth + 1, max_depth) for v in obj.values())
                elif isinstance(obj, list):
                    return any(check_depth(item, current_depth + 1, max_depth) for item in obj)
                return False
            
            if check_depth(parsed):
                threats.append("JSON structure too deep")
                risk_score += 30
            
            # Re-serializează pentru sanitizare
            sanitized = json.dumps(parsed, ensure_ascii=True)
            
            return sanitized, threats, risk_score
            
        except json.JSONDecodeError:
            threats.append("Invalid JSON format")
            return json_str, threats, 60
        except Exception as e:
            return json_str, [f"JSON sanitization error: {str(e)}"], 50
    
    def _sanitize_command(self, command: str) -> Tuple[str, List[str], int]:
        """Sanitizează comandă"""
        threats = []
        risk_score = 0
        
        # Comenzile sunt extrem de periculoase
        threats.append("Command input detected - high risk")
        risk_score += 90
        
        # Înlocuiește caractere periculoase
        sanitized = re.sub(r'[;&|`$(){}\[\]]', '', command)
        
        return sanitized, threats, risk_score
    
    def _sanitize_email(self, email: str) -> Tuple[str, List[str], int]:
        """Sanitizează adresă email"""
        threats = []
        risk_score = 0
        
        try:
            # Verifică format basic email
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                threats.append("Invalid email format")
                risk_score += 40
            
            # Verifică pentru caractere periculoase
            if any(char in email for char in ['<', '>', '"', "'", ';', '&']):
                threats.append("Dangerous characters in email")
                risk_score += 30
            
            return email.lower().strip(), threats, risk_score
            
        except Exception as e:
            return email, [f"Email sanitization error: {str(e)}"], 50
    
    def _detect_sql_injection(self, value: str) -> Tuple[List[str], int]:
        """Detectează SQL injection"""
        threats = []
        risk_score = 0
        
        value_lower = value.lower()
        
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                threats.append(f"SQL injection pattern detected: {pattern}")
                risk_score += 40
        
        return threats, risk_score
    
    def _detect_xss(self, value: str) -> Tuple[List[str], int]:
        """Detectează XSS"""
        threats = []
        risk_score = 0
        
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(f"XSS pattern detected: {pattern}")
                risk_score += 50
        
        return threats, risk_score
    
    def _detect_path_traversal(self, value: str) -> Tuple[List[str], int]:
        """Detectează path traversal"""
        threats = []
        risk_score = 0
        
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(f"Path traversal pattern detected: {pattern}")
                risk_score += 60
        
        return threats, risk_score
    
    def _detect_command_injection(self, value: str) -> Tuple[List[str], int]:
        """Detectează command injection"""
        threats = []
        risk_score = 0
        
        for pattern in self.command_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                threats.append(f"Command injection pattern detected: {pattern}")
                risk_score += 70
        
        return threats, risk_score
    
    def _strict_sanitize(self, value: str) -> str:
        """Sanitizare strictă"""
        # Înlocuiește caractere periculoase
        for char in self.dangerous_chars:
            value = value.replace(char, '')
        
        # Limitează la caractere alfanumerice și câteva caractere sigure
        value = re.sub(r'[^\w\s\-_\.]', '', value)
        
        return value.strip()
    
    def _paranoid_sanitize(self, value: str) -> str:
        """Sanitizare paranoidă"""
        # Păstrează doar caractere alfanumerice și spații
        value = re.sub(r'[^\w\s]', '', value)
        
        # Înlocuiește spații multiple cu unul singur
        value = re.sub(r'\s+', ' ', value)
        
        return value.strip()
    
    def generate_safe_token(self, length: int = 32) -> str:
        """Generează un token sigur"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash pentru date sensibile"""
        salt = secrets.token_bytes(32)
        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt, 100000).hex()

# Instanță globală
input_sanitizer = InputSanitizer()

# Funcții de conveniență
def sanitize_url(url: str) -> ValidationResult:
    """Sanitizează URL"""
    return input_sanitizer.sanitize_and_validate(url, InputType.URL)

def sanitize_filename(filename: str) -> ValidationResult:
    """Sanitizează nume fișier"""
    return input_sanitizer.sanitize_and_validate(filename, InputType.FILENAME)

def sanitize_text(text: str, max_length: Optional[int] = None) -> ValidationResult:
    """Sanitizează text"""
    return input_sanitizer.sanitize_and_validate(text, InputType.TEXT, max_length)

def is_safe_input(value: Any, input_type: InputType) -> bool:
    """Verifică dacă un input este sigur"""
    result = input_sanitizer.sanitize_and_validate(value, input_type)
    return result.is_valid and result.risk_score < 30