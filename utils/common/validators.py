#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilități comune pentru validarea URL-urilor și conținutului
"""

import re
import os
import urllib.parse
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

class URLValidator:
    """Validatoare pentru URL-uri și platforme"""
    
    # Pattern-uri pentru platforme
    PLATFORM_PATTERNS = {
        'youtube': [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([\w-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/live/([\w-]+)'
        ],
        'tiktok': [
            r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/(\d+)',
            r'(?:https?://)?vm\.tiktok\.com/([\w-]+)',
            r'(?:https?://)?(?:www\.)?tiktok\.com/t/([\w-]+)'
        ],
        'instagram': [
            r'(?:https?://)?(?:www\.)?instagram\.com/p/([\w-]+)',
            r'(?:https?://)?(?:www\.)?instagram\.com/reel/([\w-]+)',
            r'(?:https?://)?(?:www\.)?instagram\.com/tv/([\w-]+)'
        ],
        'facebook': [
            r'(?:https?://)?(?:www\.)?facebook\.com/watch/\?v=(\d+)',
            r'(?:https?://)?(?:www\.)?facebook\.com/[\w.-]+/videos/(\d+)',
            r'(?:https?://)?(?:www\.)?fb\.watch/([\w-]+)'
        ],
        'twitter': [
            r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/(\d+)',
            r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/i/status/(\d+)'
        ],
        'reddit': [
            r'(?:https?://)?(?:www\.)?reddit\.com/r/\w+/comments/([\w-]+)',
            r'(?:https?://)?(?:www\.)?redd\.it/([\w-]+)'
        ],
        'vimeo': [
            r'(?:https?://)?(?:www\.)?vimeo\.com/(\d+)',
            r'(?:https?://)?player\.vimeo\.com/video/(\d+)'
        ],
        'dailymotion': [
            r'(?:https?://)?(?:www\.)?dailymotion\.com/video/([\w-]+)',
            r'(?:https?://)?dai\.ly/([\w-]+)'
        ],
        'pinterest': [
            r'(?:https?://)?(?:www\.)?pinterest\.com/pin/(\d+)',
            r'(?:https?://)?pin\.it/([\w-]+)'
        ],
        'threads': [
            r'(?:https?://)?(?:www\.)?threads\.net/@[\w.-]+/post/([\w-]+)'
        ]
    }
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Verifică dacă URL-ul este valid"""
        if not url or not isinstance(url, str):
            return False
        
        try:
            result = urlparse(url.strip())
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        """Detectează platforma din URL"""
        if not URLValidator.is_valid_url(url):
            return None
        
        url_lower = url.lower()
        
        for platform, patterns in URLValidator.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return platform
        
        return None
    
    @staticmethod
    def extract_video_id(url: str, platform: str) -> Optional[str]:
        """Extrage ID-ul video din URL pentru o platformă specifică"""
        if platform not in URLValidator.PLATFORM_PATTERNS:
            return None
        
        for pattern in URLValidator.PLATFORM_PATTERNS[platform]:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalizează URL-ul pentru procesare consistentă"""
        if not url:
            return url
        
        # Adaugă schema dacă lipsește
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Parse și rebuild pentru normalizare
        parsed = urlparse(url)
        
        # Normalizează domeniul
        netloc = parsed.netloc.lower()
        
        # Elimină www. pentru consistență
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Reconstruiește URL-ul
        normalized = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        return normalized
    
    @staticmethod
    def get_supported_platforms() -> List[str]:
        """Returnează lista platformelor suportate"""
        return list(URLValidator.PLATFORM_PATTERNS.keys())

class ContentValidator:
    """Validatoare pentru conținut și fișiere"""
    
    # Extensii video permise
    ALLOWED_VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'
    }
    
    # Extensii audio permise
    ALLOWED_AUDIO_EXTENSIONS = {
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'
    }
    
    # Dimensiuni maxime (în bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB pentru Telegram
    MAX_FILENAME_LENGTH = 255
    
    @staticmethod
    def is_valid_video_extension(filename: str) -> bool:
        """Verifică dacă extensia fișierului este validă pentru video"""
        if not filename:
            return False
        
        ext = os.path.splitext(filename.lower())[1]
        return ext in ContentValidator.ALLOWED_VIDEO_EXTENSIONS
    
    @staticmethod
    def is_valid_audio_extension(filename: str) -> bool:
        """Verifică dacă extensia fișierului este validă pentru audio"""
        if not filename:
            return False
        
        ext = os.path.splitext(filename.lower())[1]
        return ext in ContentValidator.ALLOWED_AUDIO_EXTENSIONS
    
    @staticmethod
    def is_valid_media_extension(filename: str) -> bool:
        """Verifică dacă extensia fișierului este validă pentru media"""
        return (ContentValidator.is_valid_video_extension(filename) or 
                ContentValidator.is_valid_audio_extension(filename))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Curăță numele fișierului de caractere periculoase"""
        if not filename:
            return 'untitled'
        
        # Elimină caractere periculoase
        dangerous_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(dangerous_chars, '_', filename)
        
        # Elimină spațiile multiple
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Limitează lungimea
        if len(sanitized) > ContentValidator.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(sanitized)
            max_name_length = ContentValidator.MAX_FILENAME_LENGTH - len(ext)
            sanitized = name[:max_name_length] + ext
        
        return sanitized or 'untitled'
    
    @staticmethod
    def validate_file_size(file_path: str) -> Dict[str, Any]:
        """Validează dimensiunea fișierului"""
        try:
            if not os.path.exists(file_path):
                return {'valid': False, 'error': 'Fișierul nu există'}
            
            file_size = os.path.getsize(file_path)
            
            if file_size > ContentValidator.MAX_FILE_SIZE:
                return {
                    'valid': False,
                    'error': f'Fișierul este prea mare ({file_size / 1024 / 1024:.1f}MB > {ContentValidator.MAX_FILE_SIZE / 1024 / 1024}MB)',
                    'size': file_size
                }
            
            return {'valid': True, 'size': file_size}
            
        except Exception as e:
            return {'valid': False, 'error': f'Eroare la verificarea dimensiunii: {e}'}
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Returnează informații despre fișier"""
        try:
            if not os.path.exists(file_path):
                return {'exists': False}
            
            stat = os.stat(file_path)
            filename = os.path.basename(file_path)
            
            return {
                'exists': True,
                'filename': filename,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'extension': os.path.splitext(filename)[1].lower(),
                'is_video': ContentValidator.is_valid_video_extension(filename),
                'is_audio': ContentValidator.is_valid_audio_extension(filename),
                'created': stat.st_ctime,
                'modified': stat.st_mtime
            }
            
        except Exception as e:
            return {'exists': False, 'error': str(e)}

class SecurityValidator:
    """Validatoare pentru securitate"""
    
    # Pattern-uri periculoase
    DANGEROUS_PATTERNS = [
        r'\.\.[\/\\]',  # Path traversal
        r'[<>"\']',      # HTML/Script injection
        r'javascript:',   # JavaScript URLs
        r'data:',        # Data URLs
        r'file:',        # File URLs
    ]
    
    @staticmethod
    def is_safe_path(path: str) -> bool:
        """Verifică dacă calea este sigură (fără path traversal)"""
        if not path:
            return False
        
        # Verifică pattern-uri periculoase
        for pattern in SecurityValidator.DANGEROUS_PATTERNS[:1]:  # Doar path traversal
            if re.search(pattern, path):
                return False
        
        # Verifică că calea nu iese din directorul curent
        try:
            abs_path = os.path.abspath(path)
            current_dir = os.path.abspath('.')
            return abs_path.startswith(current_dir)
        except Exception:
            return False
    
    @staticmethod
    def is_safe_url(url: str) -> bool:
        """Verifică dacă URL-ul este sigur"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Verifică scheme-uri periculoase
        dangerous_schemes = ['javascript:', 'data:', 'file:', 'ftp:']
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return False
        
        # Verifică pattern-uri periculoase
        for pattern in SecurityValidator.DANGEROUS_PATTERNS[1:]:  # Fără path traversal
            if re.search(pattern, url):
                return False
        
        return True
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Curăță input-ul de caractere periculoase"""
        if not input_str:
            return ''
        
        # Elimină caractere periculoase
        sanitized = input_str
        for pattern in SecurityValidator.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized)
        
        return sanitized.strip()