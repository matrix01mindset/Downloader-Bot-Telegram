# platforms/base.py - Abstract Base Platform pentru toate platformele video
# Versiunea: 2.0.0 - Arhitectura Modulară

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
import asyncio
import logging
import time
import re
import unicodedata
import os

# Import local pentru configurație
try:
    from utils.config import config
except ImportError:
    # Fallback în caz că utils.config nu este disponibil
    config = None

logger = logging.getLogger(__name__)

class DownloadResult:
    """
    Rezultatul unei încercări de download cu toate informațiile necesare
    """
    def __init__(self, success: bool, file_path: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None, error: Optional[str] = None,
                 platform: Optional[str] = None):
        self.success = success
        self.file_path = file_path 
        self.metadata = metadata or {}
        self.error = error
        self.platform = platform
        self.timestamp = time.time()
        
        # Adaugă informații suplimentare pentru debugging
        self.file_size_mb = None
        if file_path and os.path.exists(file_path):
            try:
                file_size_bytes = os.path.getsize(file_path)
                self.file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
            except Exception:
                pass
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertește rezultatul în dicționar pentru logging/debugging"""
        return {
            'success': self.success,
            'file_path': self.file_path,
            'metadata': self.metadata,
            'error': self.error,
            'platform': self.platform,
            'timestamp': self.timestamp,
            'file_size_mb': self.file_size_mb
        }
        
    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"DownloadResult({status}, platform={self.platform}, file_size={self.file_size_mb}MB)"

class BasePlatform(ABC):
    """
    Abstract base class pentru toate platformele video
    
    Definește interfața comună și funcționalitatea de bază pentru:
    - YouTube, Instagram, TikTok, Facebook, Twitter
    - Platforme noi: Threads, Pinterest, Reddit, Vimeo, etc.
    """
    
    def __init__(self, platform_name: str):
        self.name = platform_name.lower()
        
        # Încarcă configurația pentru această platformă
        if config:
            self.config = config.get_platform_config(platform_name)
            self.enabled = config.is_platform_enabled(platform_name)
        else:
            # Fallback configuration dacă config nu este disponibil
            self.config = self._get_fallback_config()
            self.enabled = True
            
        self.priority = self.config.get('priority', 999)
        
        # Limitări configurabile pentru această platformă
        self.max_file_size_mb = self.config.get('max_file_size_mb', 45)  # Limită Telegram: 50MB
        self.max_duration_seconds = self.config.get('max_duration_seconds', 1800)
        self.rate_limit_per_minute = self.config.get('rate_limit_per_minute', 10)
        self.retry_attempts = self.config.get('retry_attempts', 2)
        
        # Domenii suportate - vor fi definite în fiecare platformă
        self.supported_domains: List[str] = []
        
        # Statistici pentru monitoring
        self.download_count = 0
        self.success_count = 0
        self.last_used = None
        
        logger.info(f"🔧 Initialized {self.name} platform - Enabled: {self.enabled}")
        
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Configurație fallback când config nu este disponibil"""
        return {
            'enabled': True,
            'priority': 999,
            'max_file_size_mb': 45,  # Limită Telegram: 50MB
            'max_duration_seconds': 1800,
            'rate_limit_per_minute': 10,
            'retry_attempts': 2
        }
        
    @abstractmethod
    async def is_supported_url(self, url: str) -> bool:
        """
        Verifică dacă URL-ul este suportat de această platformă
        
        Args:
            url: URL-ul de verificat
            
        Returns:
            True dacă URL-ul este suportat
        """
        pass
        
    @abstractmethod  
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extrage metadata fără descărcare (pentru validări și preview)
        
        Args:
            url: URL-ul videoclipului
            
        Returns:
            Dict cu metadata: title, description, duration, etc.
        """
        pass
        
    @abstractmethod
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        """
        Descarcă videoclipul și returnează rezultatul
        
        Args:
            url: URL-ul videoclipului
            output_path: Calea unde să salveze fișierul
            
        Returns:
            DownloadResult cu informații despre succesul descărcării
        """
        pass
        
    async def validate_constraints(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validează constrângerile platformei (dimensiune, durată, etc.)
        
        Args:
            metadata: Metadata videoclipului
            
        Returns:
            Dict cu 'valid' (bool) și eventual 'error' (str)
        """
        
        # Verifică durata
        duration = metadata.get('duration', 0)
        if isinstance(duration, (int, float)) and duration > self.max_duration_seconds:
            duration_minutes = self.max_duration_seconds // 60
            return {
                'valid': False, 
                'error': f'🕐 Video prea lung: {int(duration//60)}:{int(duration%60):02d} > {duration_minutes} min'
            }
            
        # Verifică dimensiunea estimată (dacă disponibilă)  
        estimated_size = metadata.get('estimated_size_mb', 0)
        if estimated_size and estimated_size > self.max_file_size_mb:
            return {
                'valid': False,
                'error': f'📦 Video prea mare: {estimated_size}MB > {self.max_file_size_mb}MB'
            }
            
        # Verifică că videoclipul nu este privat sau restricționat
        if metadata.get('is_private', False):
            return {
                'valid': False,
                'error': f'🔒 Videoclipul este privat și nu poate fi descărcat'
            }
            
        return {'valid': True}
        
    def _clean_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Curăță și standardizează metadata pentru Telegram
        
        Args:
            raw_metadata: Metadata brută de la extractor
            
        Returns:
            Metadata curățată și standardizată
        """
        cleaned = {
            'title': self._clean_title(raw_metadata.get('title', 'Video')),
            'description': self._clean_description(raw_metadata.get('description', '')),
            'uploader': self._clean_uploader(raw_metadata.get('uploader', '')),
            'duration': self._normalize_duration(raw_metadata.get('duration', 0)),
            'view_count': raw_metadata.get('view_count', 0),
            'upload_date': raw_metadata.get('upload_date'),
            'thumbnail': raw_metadata.get('thumbnail'),
            'webpage_url': raw_metadata.get('webpage_url', ''),
            'platform': self.name,
            'file_size': raw_metadata.get('filesize', 0)
        }
        
        # Elimină valorile None și goale
        return {k: v for k, v in cleaned.items() if v is not None and v != ''}
        
    def _clean_title(self, title: str, max_length: int = 200) -> str:
        """
        Curăță titlul pentru Telegram caption
        
        Args:
            title: Titlul original
            max_length: Lungimea maximă
            
        Returns:
            Titlul curățat
        """
        if not title or not isinstance(title, str):
            return f"Video {self.name.title()}"
            
        # Normalizează Unicode și elimină caractere de control
        title = unicodedata.normalize('NFKD', title)
        title = ''.join(char for char in title if unicodedata.category(char)[0] != 'C')
        
        # Elimină emoji și caractere speciale problematice, păstrând punctuația de bază
        title = re.sub(r'[^\w\s\-_.,!?()\[\]{}"\':;]+', '', title, flags=re.UNICODE)
        
        # Curăță spațiile multiple
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Truncate dacă este prea lung
        if len(title) > max_length:
            title = title[:max_length-3].strip() + "..."
            
        return title if title else f"Video {self.name.title()}"
        
    def _clean_description(self, description: str, max_length: int = 300) -> str:
        """
        Curăță descrierea pentru Telegram caption
        
        Args:
            description: Descrierea originală
            max_length: Lungimea maximă
            
        Returns:
            Descrierea curățată
        """
        if not description or not isinstance(description, str):
            return ""
            
        # Normalizează newlines și spații
        description = re.sub(r'[\r\n]+', ' ', description)
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Truncate smart (la ultima propoziție sau spațiu)
        if len(description) > max_length:
            truncate_pos = max_length - 3
            
            # Încearcă să găsești ultima propoziție completă
            last_sentence = description[:truncate_pos].rfind('.')
            if last_sentence > max_length // 2:
                description = description[:last_sentence + 1]
            else:
                # Altfel, găsește ultimul spațiu
                last_space = description[:truncate_pos].rfind(' ')
                if last_space > max_length // 2:
                    description = description[:last_space] + "..."
                else:
                    description = description[:truncate_pos] + "..."
                    
        return description
        
    def _clean_uploader(self, uploader: str) -> str:
        """Curăță numele uploader-ului"""
        if not uploader or not isinstance(uploader, str):
            return ""
            
        # Elimină caractere speciale și limitează lungimea
        uploader = re.sub(r'[^\w\s\-_.]+', '', uploader, flags=re.UNICODE)
        return uploader.strip()[:50]  # Max 50 caractere
        
    def _normalize_duration(self, duration: Any) -> int:
        """Normalizează durata în secunde"""
        if not duration:
            return 0
            
        try:
            return int(float(duration))
        except (ValueError, TypeError):
            return 0
            
    async def get_platform_health(self) -> Dict[str, Any]:
        """
        Returnează starea de sănătate a platformei pentru monitoring
        
        Returns:
            Dict cu informații despre starea platformei
        """
        success_rate = 0
        if self.download_count > 0:
            success_rate = round((self.success_count / self.download_count) * 100, 2)
            
        return {
            'name': self.name,
            'enabled': self.enabled,
            'priority': self.priority,
            'constraints': {
                'max_file_size_mb': self.max_file_size_mb,
                'max_duration_seconds': self.max_duration_seconds,
                'rate_limit_per_minute': self.rate_limit_per_minute
            },
            'supported_domains': self.supported_domains,
            'statistics': {
                'download_count': self.download_count,
                'success_count': self.success_count,
                'success_rate': success_rate,
                'last_used': self.last_used
            },
            'status': 'healthy' if self.enabled else 'disabled'
        }
        
    def _record_download_attempt(self, success: bool):
        """Înregistrează o încercare de download pentru statistici"""
        self.download_count += 1
        if success:
            self.success_count += 1
        self.last_used = time.time()
        
    async def process_download_with_retry(self, url: str, output_path: str) -> DownloadResult:
        """
        Procesează descărcarea cu retry logic
        
        Args:
            url: URL-ul videoclipului
            output_path: Calea de output
            
        Returns:
            DownloadResult final
        """
        last_error = None
        
        for attempt in range(self.retry_attempts + 1):
            try:
                logger.info(f"🔄 {self.name.title()} download attempt {attempt + 1}/{self.retry_attempts + 1} for {url[:50]}...")
                
                result = await self.download_video(url, output_path)
                
                # Înregistrează rezultatul pentru statistici
                self._record_download_attempt(result.success)
                
                if result.success:
                    logger.info(f"✅ {self.name.title()} download successful on attempt {attempt + 1}")
                    return result
                else:
                    last_error = result.error
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ {self.name.title()} download attempt {attempt + 1} failed: {e}")
                
            # Wait before retry (exponential backoff)
            if attempt < self.retry_attempts:
                wait_time = 2 ** attempt  # 1s, 2s, 4s, etc.
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
                
        # Toate încercările au eșuat
        self._record_download_attempt(False)
        return DownloadResult(
            success=False,
            error=f"All {self.retry_attempts + 1} attempts failed. Last error: {last_error}",
            platform=self.name
        )
        
    def __str__(self) -> str:
        return f"{self.name.title()}Platform(enabled={self.enabled}, priority={self.priority})"
        
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})>"
