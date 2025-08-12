# platforms/base.py - Clasa de Bază pentru Platforme
# Versiunea: 3.0.0 - Arhitectura Nouă

import abc
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
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

class PlatformCapability(Enum):
    """Capabilitățile suportate de o platformă"""
    DOWNLOAD_VIDEO = "download_video"
    DOWNLOAD_AUDIO = "download_audio"
    GET_METADATA = "get_metadata"
    GET_THUMBNAIL = "get_thumbnail"
    CUSTOM_QUALITY = "custom_quality"
    PLAYLIST_SUPPORT = "playlist_support"
    LIVE_STREAM = "live_stream"
    SUBTITLES = "subtitles"
    STORIES = "stories"
    SHORTS = "shorts"

@dataclass
class VideoInfo:
    """Informații despre un video"""
    # Informații de bază
    id: str
    title: str
    description: str = ""
    duration: int = 0  # în secunde
    
    # Informații uploader
    uploader: str = ""
    uploader_id: str = ""
    uploader_url: Optional[str] = None
    
    # Statistici
    upload_date: str = ""
    view_count: int = 0
    like_count: int = 0
    dislike_count: int = 0
    comment_count: int = 0
    
    # Media
    thumbnail: str = ""
    webpage_url: str = ""
    
    # Formate disponibile
    formats: List[Dict[str, Any]] = None
    
    # Metadata platformă
    platform: str = ""
    platform_id: str = ""
    
    # Informații extra specifice platformei
    extra_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.formats is None:
            self.formats = []
        if self.extra_info is None:
            self.extra_info = {}

@dataclass
class DownloadResult:
    """Rezultatul unei descărcări"""
    success: bool
    file_path: Optional[str] = None
    file_size: int = 0
    duration: float = 0.0
    error_message: Optional[str] = None
    format_info: Dict[str, Any] = None
    metadata: Optional[Dict[str, Any]] = None
    platform: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.format_info is None:
            self.format_info = {}
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = time.time()
            
        # Calculează dimensiunea fișierului dacă nu este setată
        if self.file_path and os.path.exists(self.file_path) and self.file_size == 0:
            try:
                self.file_size = os.path.getsize(self.file_path)
            except Exception:
                pass
                
    @property
    def file_size_mb(self) -> float:
        """Returnează dimensiunea fișierului în MB"""
        return round(self.file_size / (1024 * 1024), 2) if self.file_size > 0 else 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertește rezultatul în dicționar pentru logging/debugging"""
        return {
            'success': self.success,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'duration': self.duration,
            'error_message': self.error_message,
            'format_info': self.format_info,
            'metadata': self.metadata,
            'platform': self.platform,
            'timestamp': self.timestamp
        }
        
    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"DownloadResult({status}, platform={self.platform}, file_size={self.file_size_mb}MB)"

class PlatformError(Exception):
    """Excepție de bază pentru platforme"""
    pass

class UnsupportedURLError(PlatformError):
    """URL nu este suportat de platformă"""
    pass

class ExtractionError(PlatformError):
    """Eroare la extragerea informațiilor"""
    pass

class DownloadError(PlatformError):
    """Eroare la descărcare"""
    pass

class BasePlatform(abc.ABC):
    """
    Clasa de bază abstractă pentru toate platformele.
    Definește interfața comună care trebuie implementată de toate platformele.
    """
    
    def __init__(self):
        self.platform_name: str = ""
        self.capabilities: set = set()
        self.rate_limit_delay: float = 1.0  # secunde între cereri
        self.max_retries: int = 3
        self.timeout: int = 30
        self._stats = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'last_request': None,
            'errors': []
        }
        
        # Backward compatibility cu versiunea anterioară
        if config:
            self.config = config.get_platform_config(self.platform_name) if self.platform_name else {}
            self.enabled = config.is_platform_enabled(self.platform_name) if self.platform_name else True
        else:
            self.config = self._get_fallback_config()
            self.enabled = True
            
        self.priority = self.config.get('priority', 999)
        self.max_file_size_mb = self.config.get('max_file_size_mb', 45)
        self.max_duration_seconds = self.config.get('max_duration_seconds', 1800)
        self.rate_limit_per_minute = self.config.get('rate_limit_per_minute', 10)
        self.retry_attempts = self.config.get('retry_attempts', 2)
        self.supported_domains: List[str] = []
        
        # Legacy stats for backward compatibility
        self.download_count = 0
        self.success_count = 0
        self.last_used = None
        
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
        
    @abc.abstractmethod
    def supports_url(self, url: str) -> bool:
        """
        Verifică dacă platforma suportă URL-ul dat.
        
        Args:
            url: URL-ul de verificat
            
        Returns:
            True dacă platforma suportă URL-ul
        """
        pass
        
    @abc.abstractmethod
    async def get_video_info(self, url: str) -> VideoInfo:
        """
        Extrage informațiile despre video de la URL-ul dat.
        
        Args:
            url: URL-ul video-ului
            
        Returns:
            VideoInfo cu datele video-ului
            
        Raises:
            ExtractionError: Dacă extragerea eșuează
        """
        pass
        
    @abc.abstractmethod
    async def download_video(self, video_info: VideoInfo, output_path: str, 
                           quality: Optional[str] = None) -> str:
        """
        Descarcă video-ul la calea specificată.
        
        Args:
            video_info: Informații despre video
            output_path: Calea de destinație
            quality: Calitatea dorită (opțional)
            
        Returns:
            Calea către fișierul descărcat
            
        Raises:
            DownloadError: Dacă descărcarea eșuează
        """
        pass
        
    # Backward compatibility methods
    async def is_supported_url(self, url: str) -> bool:
        """Backward compatibility wrapper"""
        return self.supports_url(url)
        
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Backward compatibility wrapper"""
        try:
            video_info = await self.get_video_info(url)
            return {
                'title': video_info.title,
                'description': video_info.description,
                'duration': video_info.duration,
                'uploader': video_info.uploader,
                'view_count': video_info.view_count,
                'upload_date': video_info.upload_date,
                'thumbnail': video_info.thumbnail,
                'webpage_url': video_info.webpage_url,
                'platform': video_info.platform
            }
        except Exception as e:
            raise ExtractionError(f"Failed to extract metadata: {str(e)}")
        
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
            error_message=f"All {self.retry_attempts + 1} attempts failed. Last error: {last_error}",
            platform=self.platform_name if hasattr(self, 'platform_name') else getattr(self, 'name', 'unknown')
        )
        
    def __str__(self) -> str:
        return f"{self.name.title()}Platform(enabled={self.enabled}, priority={self.priority})"
        
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})>"
        
    # New 3.0.0 Interface Methods
    def has_capability(self, capability: PlatformCapability) -> bool:
        """Verifică dacă platforma are o capacitate specifică"""
        return capability in self.capabilities
        
    async def download_audio(self, video_info: VideoInfo, output_path: str) -> str:
        """
        Descarcă doar audio-ul din video (dacă este suportat).
        
        Args:
            video_info: Informații despre video
            output_path: Calea de destinație
            
        Returns:
            Calea către fișierul audio descărcat
            
        Raises:
            NotImplementedError: Dacă platforma nu suportă descărcarea audio
        """
        if not self.has_capability(PlatformCapability.DOWNLOAD_AUDIO):
            raise NotImplementedError(f"Platform {self.platform_name} doesn't support audio download")
        raise NotImplementedError("Audio download not implemented")
        
    async def get_thumbnail(self, video_info: VideoInfo) -> Optional[str]:
        """
        Descarcă thumbnail-ul video-ului (dacă este suportat).
        
        Args:
            video_info: Informații despre video
            
        Returns:
            URL-ul thumbnail-ului sau None
        """
        if not self.has_capability(PlatformCapability.GET_THUMBNAIL):
            return None
        return video_info.thumbnail
        
    async def get_playlist_videos(self, url: str) -> List[VideoInfo]:
        """
        Extrage video-urile dintr-o playlist (dacă este suportată).
        
        Args:
            url: URL-ul playlist-ului
            
        Returns:
            Lista cu informații despre video-urile din playlist
            
        Raises:
            NotImplementedError: Dacă platforma nu suportă playlists
        """
        if not self.has_capability(PlatformCapability.PLAYLIST_SUPPORT):
            raise NotImplementedError(f"Platform {self.platform_name} doesn't support playlists")
        raise NotImplementedError("Playlist support not implemented")
        
    def get_supported_qualities(self) -> List[str]:
        """
        Returnează lista calităților suportate de platformă.
        
        Returns:
            Lista cu calitățile suportate
        """
        return ["best", "worst", "720p", "480p", "360p"]
        
    def get_platform_info(self) -> Dict[str, Any]:
        """
        Returnează informații despre platformă.
        
        Returns:
            Dicționar cu informații despre platformă
        """
        return {
            'name': self.platform_name,
            'capabilities': [cap.value for cap in self.capabilities],
            'supported_qualities': self.get_supported_qualities(),
            'rate_limit_delay': self.rate_limit_delay,
            'max_retries': self.max_retries,
            'timeout': self.timeout
        }
        
    def record_request(self, success: bool, error: Optional[str] = None):
        """Înregistrează o cerere în statistici"""
        self._stats['requests'] += 1
        self._stats['last_request'] = datetime.now()
        
        if success:
            self._stats['successes'] += 1
        else:
            self._stats['failures'] += 1
            if error:
                self._stats['errors'].append({
                    'timestamp': datetime.now(),
                    'error': error[:200]  # Limitează lungimea erorii
                })
                
        # Păstrează doar ultimele 10 erori
        if len(self._stats['errors']) > 10:
            self._stats['errors'] = self._stats['errors'][-10:]
            
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statisticile platformei"""
        success_rate = 0.0
        if self._stats['requests'] > 0:
            success_rate = self._stats['successes'] / self._stats['requests'] * 100
            
        return {
            'platform': self.platform_name,
            'requests': self._stats['requests'],
            'successes': self._stats['successes'],
            'failures': self._stats['failures'],
            'success_rate': round(success_rate, 2),
            'last_request': self._stats['last_request'].isoformat() if self._stats['last_request'] else None,
            'recent_errors': len(self._stats['errors']),
            'capabilities': [cap.value for cap in self.capabilities],
            'status': 'active' if self.is_healthy() else 'inactive'
        }
        
    def is_healthy(self) -> bool:
        """
        Verifică dacă platforma este în stare bună.
        
        Returns:
            True dacă platforma este sănătoasă
        """
        # Consideră platforma sănătoasă dacă:
        # 1. Nu are prea multe erori recente
        # 2. Are un success rate decent
        if self._stats['requests'] == 0:
            return True  # Nu a fost încă testată
            
        success_rate = self._stats['successes'] / self._stats['requests']
        recent_errors = len(self._stats['errors'])
        
        return success_rate >= 0.5 and recent_errors < 5
        
    async def cleanup(self):
        """Curăță resursele platformei"""
        logger.info(f"🧹 Cleaning up {self.platform_name} platform resources...")
        # Implementarea de bază nu face nimic
        # Platformele specifice pot suprascrie această metodă

# Generic Platform Implementation
class GenericPlatform(BasePlatform):
    """
    Platformă generică care poate fi utilizată pentru platforme simple
    care folosesc yt-dlp fără configurări speciale.
    """
    
    def __init__(self, platform_name: str, supported_domains: List[str]):
        super().__init__()
        self.platform_name = platform_name
        self.supported_domains = supported_domains
        self.capabilities = {
            PlatformCapability.DOWNLOAD_VIDEO,
            PlatformCapability.GET_METADATA,
            PlatformCapability.GET_THUMBNAIL
        }
        
    def supports_url(self, url: str) -> bool:
        """Verifică dacă URL-ul conține unul din domeniile suportate"""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.supported_domains)
        
    async def get_video_info(self, url: str) -> VideoInfo:
        """Implementare de bază folosind yt-dlp"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                if not info:
                    raise ExtractionError(f"Could not extract info from {url}")
                    
                return VideoInfo(
                    id=info.get('id', 'unknown'),
                    title=info.get('title', 'Unknown Title'),
                    description=info.get('description', '')[:500],
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', ''),
                    uploader_id=info.get('uploader_id', ''),
                    upload_date=info.get('upload_date', ''),
                    view_count=info.get('view_count', 0),
                    like_count=info.get('like_count', 0),
                    thumbnail=info.get('thumbnail', ''),
                    webpage_url=url,
                    platform=self.platform_name,
                    platform_id=info.get('id', 'unknown'),
                    formats=[{
                        'format_id': fmt.get('format_id', ''),
                        'ext': fmt.get('ext', 'mp4'),
                        'quality': fmt.get('format_note', 'unknown'),
                        'url': fmt.get('url', ''),
                        'filesize': fmt.get('filesize'),
                        'width': fmt.get('width'),
                        'height': fmt.get('height')
                    } for fmt in info.get('formats', [])]
                )
                
        except Exception as e:
            self.record_request(False, str(e))
            raise ExtractionError(f"Failed to extract video info: {str(e)}")
            
    async def download_video(self, video_info: VideoInfo, output_path: str, 
                           quality: Optional[str] = None) -> str:
        """Implementare de bază pentru descărcare"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'outtmpl': output_path,
                'format': 'best[filesize<50M]/best' if not quality else f'best[height<={quality[:-1]}]/best'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [video_info.webpage_url])
                
            self.record_request(True)
            return output_path
            
        except Exception as e:
            self.record_request(False, str(e))
            raise DownloadError(f"Failed to download video: {str(e)}")
