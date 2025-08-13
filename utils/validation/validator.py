# utils/validation/validator.py - Sistem de Validare pentru Arhitectura Refactorizată
# Versiunea: 4.0.0 - Validare Comprehensivă

import re
import os
import json
import hashlib
import mimetypes
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

try:
    from platforms.base.abstract_platform import PlatformCapability, ContentType, QualityLevel
except ImportError:
    # Fallback pentru development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import PlatformCapability, ContentType, QualityLevel

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Nivelurile de validare"""
    BASIC = "basic"          # Validare de bază
    STANDARD = "standard"    # Validare standard
    STRICT = "strict"        # Validare strictă
    PARANOID = "paranoid"    # Validare paranoidă

class ValidationResult(Enum):
    """Rezultatele validării"""
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"
    ERROR = "error"

class ValidationType(Enum):
    """Tipurile de validare"""
    URL = "url"
    FILE_PATH = "file_path"
    FILE_SIZE = "file_size"
    FILE_TYPE = "file_type"
    CONTENT_TYPE = "content_type"
    QUALITY = "quality"
    METADATA = "metadata"
    CONFIG = "config"
    PLATFORM = "platform"
    DOWNLOAD = "download"
    NETWORK = "network"
    SECURITY = "security"

@dataclass
class ValidationIssue:
    """O problemă de validare"""
    type: ValidationType
    level: ValidationResult
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None
    code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'level': self.level.value,
            'message': self.message,
            'field': self.field,
            'value': str(self.value) if self.value is not None else None,
            'suggestion': self.suggestion,
            'code': self.code
        }

@dataclass
class ValidationReport:
    """Raportul de validare"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_time: float = 0.0
    
    def add_issue(self, issue: ValidationIssue):
        """Adaugă o problemă la raport"""
        self.issues.append(issue)
        
        if issue.level == ValidationResult.WARNING:
            self.warnings.append(issue)
        elif issue.level in [ValidationResult.INVALID, ValidationResult.ERROR]:
            self.errors.append(issue)
            self.is_valid = False
    
    def has_errors(self) -> bool:
        """Verifică dacă sunt erori"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Verifică dacă sunt avertismente"""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Obține un rezumat al validării"""
        if self.is_valid and not self.has_warnings():
            return "✅ Validation passed"
        elif self.is_valid and self.has_warnings():
            return f"⚠️ Validation passed with {len(self.warnings)} warnings"
        else:
            return f"❌ Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'summary': self.get_summary(),
            'issues': [issue.to_dict() for issue in self.issues],
            'warnings_count': len(self.warnings),
            'errors_count': len(self.errors),
            'validation_time': self.validation_time,
            'metadata': self.metadata
        }

class URLValidator:
    """Validator pentru URL-uri"""
    
    # Domenii cunoscute pentru platforme
    KNOWN_DOMAINS = {
        'youtube.com', 'youtu.be', 'm.youtube.com',
        'instagram.com', 'www.instagram.com',
        'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com',
        'twitter.com', 'x.com', 'mobile.twitter.com',
        'facebook.com', 'www.facebook.com', 'm.facebook.com',
        'reddit.com', 'www.reddit.com', 'old.reddit.com',
        'twitch.tv', 'www.twitch.tv',
        'vimeo.com', 'player.vimeo.com',
        'dailymotion.com', 'www.dailymotion.com',
        'soundcloud.com', 'www.soundcloud.com'
    }
    
    # Scheme permise
    ALLOWED_SCHEMES = {'http', 'https'}
    
    # Extensii periculoase
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.msi', '.dll'
    }
    
    @classmethod
    def validate_url(cls, url: str, level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează un URL"""
        report = ValidationReport(is_valid=True)
        
        if not url or not isinstance(url, str):
            report.add_issue(ValidationIssue(
                type=ValidationType.URL,
                level=ValidationResult.INVALID,
                message="URL is empty or not a string",
                value=url,
                code="URL_EMPTY"
            ))
            return report
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            
            # Verifică schema
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                report.add_issue(ValidationIssue(
                    type=ValidationType.URL,
                    level=ValidationResult.INVALID,
                    message=f"Invalid URL scheme: {parsed.scheme}",
                    field="scheme",
                    value=parsed.scheme,
                    suggestion="Use http or https",
                    code="URL_INVALID_SCHEME"
                ))
            
            # Verifică domeniul
            if not parsed.netloc:
                report.add_issue(ValidationIssue(
                    type=ValidationType.URL,
                    level=ValidationResult.INVALID,
                    message="URL missing domain",
                    field="netloc",
                    code="URL_NO_DOMAIN"
                ))
            else:
                # Verifică dacă domeniul este cunoscut
                domain = parsed.netloc.lower()
                if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                    if not any(known in domain for known in cls.KNOWN_DOMAINS):
                        report.add_issue(ValidationIssue(
                            type=ValidationType.URL,
                            level=ValidationResult.WARNING,
                            message=f"Unknown domain: {domain}",
                            field="domain",
                            value=domain,
                            suggestion="Verify this is a supported platform",
                            code="URL_UNKNOWN_DOMAIN"
                        ))
            
            # Verifică extensii periculoase
            if level == ValidationLevel.PARANOID:
                path = parsed.path.lower()
                for ext in cls.DANGEROUS_EXTENSIONS:
                    if path.endswith(ext):
                        report.add_issue(ValidationIssue(
                            type=ValidationType.SECURITY,
                            level=ValidationResult.WARNING,
                            message=f"Potentially dangerous file extension: {ext}",
                            field="path",
                            value=path,
                            code="URL_DANGEROUS_EXTENSION"
                        ))
            
            # Verifică lungimea URL-ului
            if len(url) > 2048:
                report.add_issue(ValidationIssue(
                    type=ValidationType.URL,
                    level=ValidationResult.WARNING,
                    message=f"URL is very long ({len(url)} characters)",
                    field="length",
                    value=len(url),
                    suggestion="Long URLs may cause issues",
                    code="URL_TOO_LONG"
                ))
            
            # Verifică caractere suspicioase
            if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                suspicious_chars = ['<', '>', '"', "'", '`']
                for char in suspicious_chars:
                    if char in url:
                        report.add_issue(ValidationIssue(
                            type=ValidationType.SECURITY,
                            level=ValidationResult.WARNING,
                            message=f"Suspicious character in URL: {char}",
                            field="characters",
                            value=char,
                            code="URL_SUSPICIOUS_CHAR"
                        ))
            
        except Exception as e:
            report.add_issue(ValidationIssue(
                type=ValidationType.URL,
                level=ValidationResult.INVALID,
                message=f"Failed to parse URL: {e}",
                value=url,
                code="URL_PARSE_ERROR"
            ))
        
        return report
    
    @classmethod
    def extract_video_id(cls, url: str, platform: str) -> Optional[str]:
        """Extrage ID-ul video din URL pentru o platformă specifică"""
        try:
            parsed = urlparse(url)
            
            if platform.lower() == 'youtube':
                if 'youtu.be' in parsed.netloc:
                    return parsed.path[1:]  # Elimină /
                elif 'youtube.com' in parsed.netloc:
                    query = parse_qs(parsed.query)
                    return query.get('v', [None])[0]
            
            elif platform.lower() == 'instagram':
                # Instagram: /p/POST_ID/ sau /reel/REEL_ID/
                match = re.search(r'/(p|reel)/([A-Za-z0-9_-]+)/', parsed.path)
                if match:
                    return match.group(2)
            
            elif platform.lower() == 'tiktok':
                # TikTok: /video/VIDEO_ID
                match = re.search(r'/video/(\d+)', parsed.path)
                if match:
                    return match.group(1)
            
            elif platform.lower() == 'twitter':
                # Twitter: /status/TWEET_ID
                match = re.search(r'/status/(\d+)', parsed.path)
                if match:
                    return match.group(1)
            
        except Exception as e:
            logger.warning(f"Failed to extract video ID from {url}: {e}")
        
        return None

class FileValidator:
    """Validator pentru fișiere"""
    
    # Tipuri MIME permise
    ALLOWED_MIME_TYPES = {
        'video': {
            'video/mp4', 'video/avi', 'video/mkv', 'video/mov',
            'video/wmv', 'video/flv', 'video/webm', 'video/m4v'
        },
        'audio': {
            'audio/mp3', 'audio/wav', 'audio/flac', 'audio/aac',
            'audio/ogg', 'audio/m4a', 'audio/wma'
        },
        'image': {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'image/bmp', 'image/svg+xml'
        }
    }
    
    # Limite de dimensiune (în bytes)
    SIZE_LIMITS = {
        'video': 5 * 1024 * 1024 * 1024,  # 5GB
        'audio': 500 * 1024 * 1024,       # 500MB
        'image': 50 * 1024 * 1024,        # 50MB
        'default': 1024 * 1024 * 1024     # 1GB
    }
    
    @classmethod
    def validate_file_path(cls, file_path: str, level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează o cale de fișier"""
        report = ValidationReport(is_valid=True)
        
        if not file_path or not isinstance(file_path, str):
            report.add_issue(ValidationIssue(
                type=ValidationType.FILE_PATH,
                level=ValidationResult.INVALID,
                message="File path is empty or not a string",
                value=file_path,
                code="PATH_EMPTY"
            ))
            return report
        
        try:
            path = Path(file_path)
            
            # Verifică caractere invalide
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
            if os.name == 'nt':  # Windows
                for char in invalid_chars:
                    if char in file_path:
                        report.add_issue(ValidationIssue(
                            type=ValidationType.FILE_PATH,
                            level=ValidationResult.INVALID,
                            message=f"Invalid character in path: {char}",
                            field="characters",
                            value=char,
                            code="PATH_INVALID_CHAR"
                        ))
            
            # Verifică lungimea căii
            if len(file_path) > 260 and os.name == 'nt':  # Windows path limit
                report.add_issue(ValidationIssue(
                    type=ValidationType.FILE_PATH,
                    level=ValidationResult.WARNING,
                    message=f"Path is very long ({len(file_path)} characters)",
                    field="length",
                    value=len(file_path),
                    suggestion="Consider shortening the path",
                    code="PATH_TOO_LONG"
                ))
            
            # Verifică dacă directorul părinte există
            parent_dir = path.parent
            if not parent_dir.exists():
                if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                    report.add_issue(ValidationIssue(
                        type=ValidationType.FILE_PATH,
                        level=ValidationResult.WARNING,
                        message=f"Parent directory does not exist: {parent_dir}",
                        field="parent_directory",
                        value=str(parent_dir),
                        suggestion="Directory will be created automatically",
                        code="PATH_PARENT_NOT_EXISTS"
                    ))
            
            # Verifică permisiunile de scriere
            if parent_dir.exists() and not os.access(parent_dir, os.W_OK):
                report.add_issue(ValidationIssue(
                    type=ValidationType.FILE_PATH,
                    level=ValidationResult.INVALID,
                    message=f"No write permission for directory: {parent_dir}",
                    field="permissions",
                    value=str(parent_dir),
                    code="PATH_NO_WRITE_PERMISSION"
                ))
            
            # Verifică dacă fișierul există deja
            if path.exists():
                if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                    report.add_issue(ValidationIssue(
                        type=ValidationType.FILE_PATH,
                        level=ValidationResult.WARNING,
                        message=f"File already exists: {file_path}",
                        field="existence",
                        value=file_path,
                        suggestion="File will be overwritten",
                        code="PATH_FILE_EXISTS"
                    ))
            
        except Exception as e:
            report.add_issue(ValidationIssue(
                type=ValidationType.FILE_PATH,
                level=ValidationResult.INVALID,
                message=f"Failed to validate path: {e}",
                value=file_path,
                code="PATH_VALIDATION_ERROR"
            ))
        
        return report
    
    @classmethod
    def validate_file_size(cls, size: int, content_type: str = 'default', 
                          level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează dimensiunea unui fișier"""
        report = ValidationReport(is_valid=True)
        
        if size < 0:
            report.add_issue(ValidationIssue(
                type=ValidationType.FILE_SIZE,
                level=ValidationResult.INVALID,
                message="File size cannot be negative",
                value=size,
                code="SIZE_NEGATIVE"
            ))
            return report
        
        # Determină tipul de conținut
        if content_type.startswith('video/'):
            category = 'video'
        elif content_type.startswith('audio/'):
            category = 'audio'
        elif content_type.startswith('image/'):
            category = 'image'
        else:
            category = 'default'
        
        limit = cls.SIZE_LIMITS.get(category, cls.SIZE_LIMITS['default'])
        
        if size > limit:
            report.add_issue(ValidationIssue(
                type=ValidationType.FILE_SIZE,
                level=ValidationResult.WARNING,
                message=f"File size ({cls._format_size(size)}) exceeds recommended limit ({cls._format_size(limit)})",
                field="size",
                value=size,
                suggestion="Large files may take longer to download",
                code="SIZE_EXCEEDS_LIMIT"
            ))
        
        # Verifică fișiere foarte mici (posibil corupte)
        if size < 1024 and level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:  # < 1KB
            report.add_issue(ValidationIssue(
                type=ValidationType.FILE_SIZE,
                level=ValidationResult.WARNING,
                message=f"File is very small ({cls._format_size(size)})",
                field="size",
                value=size,
                suggestion="Verify file is not corrupted",
                code="SIZE_VERY_SMALL"
            ))
        
        return report
    
    @classmethod
    def validate_mime_type(cls, mime_type: str, expected_category: Optional[str] = None,
                          level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează tipul MIME"""
        report = ValidationReport(is_valid=True)
        
        if not mime_type:
            report.add_issue(ValidationIssue(
                type=ValidationType.CONTENT_TYPE,
                level=ValidationResult.WARNING,
                message="MIME type is empty",
                value=mime_type,
                code="MIME_EMPTY"
            ))
            return report
        
        # Verifică dacă tipul MIME este cunoscut
        all_allowed = set()
        for category_types in cls.ALLOWED_MIME_TYPES.values():
            all_allowed.update(category_types)
        
        if mime_type not in all_allowed:
            if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONTENT_TYPE,
                    level=ValidationResult.WARNING,
                    message=f"Unknown MIME type: {mime_type}",
                    field="mime_type",
                    value=mime_type,
                    suggestion="Verify file type is supported",
                    code="MIME_UNKNOWN"
                ))
        
        # Verifică categoria așteptată
        if expected_category:
            expected_types = cls.ALLOWED_MIME_TYPES.get(expected_category, set())
            if mime_type not in expected_types:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONTENT_TYPE,
                    level=ValidationResult.WARNING,
                    message=f"MIME type {mime_type} doesn't match expected category {expected_category}",
                    field="category",
                    value=mime_type,
                    code="MIME_CATEGORY_MISMATCH"
                ))
        
        return report
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Formatează dimensiunea în format human-readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

class ConfigValidator:
    """Validator pentru configurații"""
    
    @classmethod
    def validate_platform_config(cls, config: Dict[str, Any], 
                                level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează configurația unei platforme"""
        report = ValidationReport(is_valid=True)
        
        # Câmpuri obligatorii
        required_fields = ['name', 'domains', 'capabilities']
        for field in required_fields:
            if field not in config:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.INVALID,
                    message=f"Missing required field: {field}",
                    field=field,
                    code="CONFIG_MISSING_FIELD"
                ))
        
        # Validează numele
        if 'name' in config:
            name = config['name']
            if not isinstance(name, str) or not name.strip():
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.INVALID,
                    message="Platform name must be a non-empty string",
                    field="name",
                    value=name,
                    code="CONFIG_INVALID_NAME"
                ))
        
        # Validează domeniile
        if 'domains' in config:
            domains = config['domains']
            if not isinstance(domains, list) or not domains:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.INVALID,
                    message="Domains must be a non-empty list",
                    field="domains",
                    value=domains,
                    code="CONFIG_INVALID_DOMAINS"
                ))
            else:
                for domain in domains:
                    if not isinstance(domain, str) or not domain.strip():
                        report.add_issue(ValidationIssue(
                            type=ValidationType.CONFIG,
                            level=ValidationResult.INVALID,
                            message=f"Invalid domain: {domain}",
                            field="domains",
                            value=domain,
                            code="CONFIG_INVALID_DOMAIN"
                        ))
        
        # Validează capabilitățile
        if 'capabilities' in config:
            capabilities = config['capabilities']
            if not isinstance(capabilities, list):
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.INVALID,
                    message="Capabilities must be a list",
                    field="capabilities",
                    value=capabilities,
                    code="CONFIG_INVALID_CAPABILITIES"
                ))
            else:
                valid_capabilities = {cap.value for cap in PlatformCapability}
                for cap in capabilities:
                    if cap not in valid_capabilities:
                        report.add_issue(ValidationIssue(
                            type=ValidationType.CONFIG,
                            level=ValidationResult.WARNING,
                            message=f"Unknown capability: {cap}",
                            field="capabilities",
                            value=cap,
                            suggestion=f"Valid capabilities: {', '.join(valid_capabilities)}",
                            code="CONFIG_UNKNOWN_CAPABILITY"
                        ))
        
        # Validează configurația de rate limiting
        if 'rate_limit' in config:
            rate_limit = config['rate_limit']
            if isinstance(rate_limit, dict):
                if 'requests_per_minute' in rate_limit:
                    rpm = rate_limit['requests_per_minute']
                    if not isinstance(rpm, int) or rpm <= 0:
                        report.add_issue(ValidationIssue(
                            type=ValidationType.CONFIG,
                            level=ValidationResult.INVALID,
                            message="requests_per_minute must be a positive integer",
                            field="rate_limit.requests_per_minute",
                            value=rpm,
                            code="CONFIG_INVALID_RATE_LIMIT"
                        ))
        
        return report
    
    @classmethod
    def validate_download_config(cls, config: Dict[str, Any],
                               level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează configurația de descărcare"""
        report = ValidationReport(is_valid=True)
        
        # Validează quality
        if 'quality' in config:
            quality = config['quality']
            valid_qualities = {q.value for q in QualityLevel}
            if quality not in valid_qualities:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.WARNING,
                    message=f"Unknown quality level: {quality}",
                    field="quality",
                    value=quality,
                    suggestion=f"Valid qualities: {', '.join(valid_qualities)}",
                    code="CONFIG_UNKNOWN_QUALITY"
                ))
        
        # Validează content_type
        if 'content_type' in config:
            content_type = config['content_type']
            valid_types = {ct.value for ct in ContentType}
            if content_type not in valid_types:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.WARNING,
                    message=f"Unknown content type: {content_type}",
                    field="content_type",
                    value=content_type,
                    suggestion=f"Valid types: {', '.join(valid_types)}",
                    code="CONFIG_UNKNOWN_CONTENT_TYPE"
                ))
        
        # Validează timeout
        if 'timeout' in config:
            timeout = config['timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.INVALID,
                    message="Timeout must be a positive number",
                    field="timeout",
                    value=timeout,
                    code="CONFIG_INVALID_TIMEOUT"
                ))
        
        # Validează max_retries
        if 'max_retries' in config:
            retries = config['max_retries']
            if not isinstance(retries, int) or retries < 0:
                report.add_issue(ValidationIssue(
                    type=ValidationType.CONFIG,
                    level=ValidationResult.INVALID,
                    message="max_retries must be a non-negative integer",
                    field="max_retries",
                    value=retries,
                    code="CONFIG_INVALID_RETRIES"
                ))
        
        return report

class SecurityValidator:
    """Validator pentru securitate"""
    
    # Extensii periculoase
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.msi', '.dll', '.ps1'
    }
    
    # Caractere suspicioase
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>',  # Script tags
        r'javascript:',     # JavaScript URLs
        r'data:.*base64',   # Base64 data URLs
        r'\.\.[\\/]',      # Directory traversal
        r'[<>"\']',         # HTML/SQL injection chars
    ]
    
    @classmethod
    def validate_security(cls, data: Any, context: str = "general",
                         level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationReport:
        """Validează aspectele de securitate"""
        report = ValidationReport(is_valid=True)
        
        if isinstance(data, str):
            # Verifică extensii periculoase
            for ext in cls.DANGEROUS_EXTENSIONS:
                if data.lower().endswith(ext):
                    report.add_issue(ValidationIssue(
                        type=ValidationType.SECURITY,
                        level=ValidationResult.WARNING,
                        message=f"Potentially dangerous file extension: {ext}",
                        field="extension",
                        value=ext,
                        code="SECURITY_DANGEROUS_EXTENSION"
                    ))
            
            # Verifică pattern-uri suspicioase
            if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                for pattern in cls.SUSPICIOUS_PATTERNS:
                    if re.search(pattern, data, re.IGNORECASE):
                        report.add_issue(ValidationIssue(
                            type=ValidationType.SECURITY,
                            level=ValidationResult.WARNING,
                            message=f"Suspicious pattern detected: {pattern}",
                            field="content",
                            value=pattern,
                            code="SECURITY_SUSPICIOUS_PATTERN"
                        ))
        
        elif isinstance(data, dict):
            # Verifică chei suspicioase
            suspicious_keys = ['password', 'token', 'key', 'secret', 'auth']
            for key in data.keys():
                if any(sus in key.lower() for sus in suspicious_keys):
                    if level == ValidationLevel.PARANOID:
                        report.add_issue(ValidationIssue(
                            type=ValidationType.SECURITY,
                            level=ValidationResult.WARNING,
                            message=f"Potentially sensitive key: {key}",
                            field="keys",
                            value=key,
                            suggestion="Ensure sensitive data is properly protected",
                            code="SECURITY_SENSITIVE_KEY"
                        ))
        
        return report

class UniversalValidator:
    """
    Validator universal care combină toate tipurile de validare.
    Oferă o interfață simplă pentru validarea comprehensivă.
    """
    
    def __init__(self, default_level: ValidationLevel = ValidationLevel.STANDARD):
        self.default_level = default_level
        self.url_validator = URLValidator()
        self.file_validator = FileValidator()
        self.config_validator = ConfigValidator()
        self.security_validator = SecurityValidator()
        
        # Statistici
        self.stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'warnings_generated': 0,
            'errors_generated': 0,
            'validation_types': defaultdict(int)
        }
        
        logger.info("🔍 Universal Validator initialized")
    
    async def validate_url(self, url: str, level: Optional[ValidationLevel] = None) -> ValidationReport:
        """Validează un URL"""
        level = level or self.default_level
        start_time = datetime.now()
        
        try:
            report = self.url_validator.validate_url(url, level)
            
            # Adaugă validare de securitate
            if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                security_report = self.security_validator.validate_security(url, "url", level)
                report.issues.extend(security_report.issues)
                report.warnings.extend(security_report.warnings)
                report.errors.extend(security_report.errors)
                if security_report.has_errors():
                    report.is_valid = False
            
            self._update_stats(report, ValidationType.URL)
            report.validation_time = (datetime.now() - start_time).total_seconds()
            
            return report
            
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            report = ValidationReport(is_valid=False)
            report.add_issue(ValidationIssue(
                type=ValidationType.URL,
                level=ValidationResult.ERROR,
                message=f"Validation error: {e}",
                code="VALIDATION_ERROR"
            ))
            self._update_stats(report, ValidationType.URL)
            return report
    
    async def validate_file_path(self, file_path: str, level: Optional[ValidationLevel] = None) -> ValidationReport:
        """Validează o cale de fișier"""
        level = level or self.default_level
        start_time = datetime.now()
        
        try:
            report = self.file_validator.validate_file_path(file_path, level)
            
            # Adaugă validare de securitate
            security_report = self.security_validator.validate_security(file_path, "file_path", level)
            report.issues.extend(security_report.issues)
            report.warnings.extend(security_report.warnings)
            report.errors.extend(security_report.errors)
            if security_report.has_errors():
                report.is_valid = False
            
            self._update_stats(report, ValidationType.FILE_PATH)
            report.validation_time = (datetime.now() - start_time).total_seconds()
            
            return report
            
        except Exception as e:
            logger.error(f"File path validation failed: {e}")
            report = ValidationReport(is_valid=False)
            report.add_issue(ValidationIssue(
                type=ValidationType.FILE_PATH,
                level=ValidationResult.ERROR,
                message=f"Validation error: {e}",
                code="VALIDATION_ERROR"
            ))
            self._update_stats(report, ValidationType.FILE_PATH)
            return report
    
    async def validate_download_request(self, url: str, output_path: str, 
                                      config: Dict[str, Any],
                                      level: Optional[ValidationLevel] = None) -> ValidationReport:
        """Validează o cerere de descărcare completă"""
        level = level or self.default_level
        start_time = datetime.now()
        
        combined_report = ValidationReport(is_valid=True)
        
        try:
            # Validează URL-ul
            url_report = await self.validate_url(url, level)
            combined_report.issues.extend(url_report.issues)
            combined_report.warnings.extend(url_report.warnings)
            combined_report.errors.extend(url_report.errors)
            if url_report.has_errors():
                combined_report.is_valid = False
            
            # Validează calea de fișier
            path_report = await self.validate_file_path(output_path, level)
            combined_report.issues.extend(path_report.issues)
            combined_report.warnings.extend(path_report.warnings)
            combined_report.errors.extend(path_report.errors)
            if path_report.has_errors():
                combined_report.is_valid = False
            
            # Validează configurația
            config_report = self.config_validator.validate_download_config(config, level)
            combined_report.issues.extend(config_report.issues)
            combined_report.warnings.extend(config_report.warnings)
            combined_report.errors.extend(config_report.errors)
            if config_report.has_errors():
                combined_report.is_valid = False
            
            self._update_stats(combined_report, ValidationType.DOWNLOAD)
            combined_report.validation_time = (datetime.now() - start_time).total_seconds()
            
            return combined_report
            
        except Exception as e:
            logger.error(f"Download request validation failed: {e}")
            combined_report.is_valid = False
            combined_report.add_issue(ValidationIssue(
                type=ValidationType.DOWNLOAD,
                level=ValidationResult.ERROR,
                message=f"Validation error: {e}",
                code="VALIDATION_ERROR"
            ))
            self._update_stats(combined_report, ValidationType.DOWNLOAD)
            return combined_report
    
    async def validate_platform_config(self, config: Dict[str, Any],
                                      level: Optional[ValidationLevel] = None) -> ValidationReport:
        """Validează configurația unei platforme"""
        level = level or self.default_level
        start_time = datetime.now()
        
        try:
            report = self.config_validator.validate_platform_config(config, level)
            
            # Adaugă validare de securitate pentru configurație
            security_report = self.security_validator.validate_security(config, "platform_config", level)
            report.issues.extend(security_report.issues)
            report.warnings.extend(security_report.warnings)
            report.errors.extend(security_report.errors)
            if security_report.has_errors():
                report.is_valid = False
            
            self._update_stats(report, ValidationType.PLATFORM)
            report.validation_time = (datetime.now() - start_time).total_seconds()
            
            return report
            
        except Exception as e:
            logger.error(f"Platform config validation failed: {e}")
            report = ValidationReport(is_valid=False)
            report.add_issue(ValidationIssue(
                type=ValidationType.PLATFORM,
                level=ValidationResult.ERROR,
                message=f"Validation error: {e}",
                code="VALIDATION_ERROR"
            ))
            self._update_stats(report, ValidationType.PLATFORM)
            return report
    
    def _update_stats(self, report: ValidationReport, validation_type: ValidationType):
        """Actualizează statisticile"""
        self.stats['total_validations'] += 1
        self.stats['validation_types'][validation_type.value] += 1
        
        if report.is_valid:
            self.stats['successful_validations'] += 1
        else:
            self.stats['failed_validations'] += 1
        
        self.stats['warnings_generated'] += len(report.warnings)
        self.stats['errors_generated'] += len(report.errors)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obține statisticile validatorului"""
        stats = self.stats.copy()
        stats['validation_types'] = dict(stats['validation_types'])
        
        total = stats['total_validations']
        if total > 0:
            stats['success_rate'] = stats['successful_validations'] / total * 100
            stats['average_warnings_per_validation'] = stats['warnings_generated'] / total
            stats['average_errors_per_validation'] = stats['errors_generated'] / total
        else:
            stats['success_rate'] = 0.0
            stats['average_warnings_per_validation'] = 0.0
            stats['average_errors_per_validation'] = 0.0
        
        return stats
    
    def set_default_level(self, level: ValidationLevel):
        """Setează nivelul de validare implicit"""
        self.default_level = level
        logger.info(f"🔧 Default validation level set to: {level.value}")
    
    def __str__(self) -> str:
        total = self.stats['total_validations']
        success_rate = self.stats['successful_validations'] / total * 100 if total > 0 else 0
        return f"UniversalValidator(validations={total}, success_rate={success_rate:.1f}%)"
    
    def __repr__(self) -> str:
        return (f"UniversalValidator(level={self.default_level.value}, "
                f"validations={self.stats['total_validations']})")


# Singleton instance pentru utilizare globală
validator = UniversalValidator()