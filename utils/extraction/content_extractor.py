# utils/extraction/content_extractor.py - Extractor Universal de Conținut
# Versiunea: 4.0.0 - Arhitectura Refactorizată

import asyncio
import aiohttp
import re
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urlparse, parse_qs, unquote
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import base64

try:
    from platforms.base.abstract_platform import (
        ContentType, QualityLevel, MediaFormat, VideoMetadata,
        PlatformError, UnsupportedURLError, DownloadError
    )
except ImportError:
    # Fallback pentru development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from platforms.base.abstract_platform import (
        ContentType, QualityLevel, MediaFormat, VideoMetadata,
        PlatformError, UnsupportedURLError, DownloadError
    )

logger = logging.getLogger(__name__)

class ExtractionMethod(Enum):
    """Metodele de extragere disponibile"""
    HTML_PARSING = "html_parsing"
    API_CALL = "api_call"
    REGEX_EXTRACTION = "regex_extraction"
    JAVASCRIPT_EXECUTION = "javascript_execution"
    METADATA_PARSING = "metadata_parsing"
    DIRECT_LINK = "direct_link"

class ExtractionStrategy(Enum):
    """Strategiile de extragere"""
    FAST = "fast"  # Doar metode rapide
    COMPREHENSIVE = "comprehensive"  # Toate metodele disponibile
    FALLBACK = "fallback"  # Încearcă metodele una câte una
    PARALLEL = "parallel"  # Rulează metodele în paralel

@dataclass
class ExtractionResult:
    """Rezultatul unei extrageri de conținut"""
    success: bool
    method_used: ExtractionMethod
    extraction_time: float
    metadata: Optional[VideoMetadata] = None
    media_urls: List[str] = field(default_factory=list)
    thumbnail_urls: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0  # 0-1, cât de sigur este rezultatul
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'method_used': self.method_used.value,
            'extraction_time': self.extraction_time,
            'metadata': self.metadata.__dict__ if self.metadata else None,
            'media_urls': self.media_urls,
            'thumbnail_urls': self.thumbnail_urls,
            'error_message': self.error_message,
            'confidence_score': self.confidence_score
        }

@dataclass
class ExtractionConfig:
    """Configurația pentru extragerea de conținut"""
    strategy: ExtractionStrategy = ExtractionStrategy.COMPREHENSIVE
    timeout: int = 30
    max_retries: int = 3
    user_agent: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    follow_redirects: bool = True
    verify_ssl: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    preferred_quality: QualityLevel = QualityLevel.HD
    extract_thumbnails: bool = True
    extract_subtitles: bool = False
    extract_comments: bool = False

class ContentExtractor:
    """
    Extractor universal de conținut care poate extrage metadata și link-uri
    de media din diverse surse folosind multiple metode.
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        
        # Cache pentru rezultate
        self._cache: Dict[str, ExtractionResult] = {}
        self._cache_ttl = 3600  # 1 oră
        
        # Statistici
        self.stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'cache_hits': 0,
            'method_usage': {method.value: 0 for method in ExtractionMethod}
        }
        
        # Regex patterns comune
        self.common_patterns = {
            'video_id': {
                'youtube': r'(?:v=|embed/|watch\?v=)([a-zA-Z0-9_-]{11})',
                'instagram': r'(?:p/|reel/)([a-zA-Z0-9_-]+)',
                'tiktok': r'(?:video/)([0-9]+)',
                'facebook': r'(?:videos/)([0-9]+)',
                'twitter': r'(?:status/)([0-9]+)'
            },
            'media_urls': {
                'direct_video': r'https?://[^\s"]+\.(?:mp4|webm|avi|mov|flv|mkv)',
                'direct_audio': r'https?://[^\s"]+\.(?:mp3|wav|aac|ogg|m4a)',
                'direct_image': r'https?://[^\s"]+\.(?:jpg|jpeg|png|gif|webp)'
            },
            'metadata': {
                'title': r'<title[^>]*>([^<]+)</title>',
                'description': r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\'>]+)["\']',
                'og_title': r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\'>]+)["\']',
                'og_description': r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\'>]+)["\']',
                'og_image': r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\'>]+)["\']',
                'og_video': r'<meta[^>]*property=["\']og:video["\'][^>]*content=["\']([^"\'>]+)["\']'
            }
        }
        
        # User agents pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        
        logger.info("🔍 Content Extractor initialized")
    
    async def extract_content(self, url: str, platform_hint: Optional[str] = None) -> ExtractionResult:
        """
        Extrage conținut din URL folosind strategia configurată.
        
        Args:
            url: URL-ul de la care să extragă conținutul
            platform_hint: Hint despre platforma (youtube, instagram, etc.)
        
        Returns:
            ExtractionResult cu datele extrase
        """
        start_time = time.time()
        
        # Verifică cache-ul
        cache_key = self._get_cache_key(url)
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result.extraction_time < self._cache_ttl:
                self.stats['cache_hits'] += 1
                logger.debug(f"📋 Cache hit for {url}")
                return cached_result
        
        self.stats['total_extractions'] += 1
        
        try:
            # Determină strategia de extragere
            if self.config.strategy == ExtractionStrategy.FAST:
                result = await self._extract_fast(url, platform_hint)
            elif self.config.strategy == ExtractionStrategy.COMPREHENSIVE:
                result = await self._extract_comprehensive(url, platform_hint)
            elif self.config.strategy == ExtractionStrategy.FALLBACK:
                result = await self._extract_fallback(url, platform_hint)
            elif self.config.strategy == ExtractionStrategy.PARALLEL:
                result = await self._extract_parallel(url, platform_hint)
            else:
                result = await self._extract_comprehensive(url, platform_hint)
            
            # Actualizează timpul de extragere
            result.extraction_time = time.time() - start_time
            
            # Salvează în cache
            self._cache[cache_key] = result
            
            # Actualizează statisticile
            if result.success:
                self.stats['successful_extractions'] += 1
            else:
                self.stats['failed_extractions'] += 1
            
            self.stats['method_usage'][result.method_used.value] += 1
            
            logger.info(f"✅ Content extracted from {url} using {result.method_used.value} in {result.extraction_time:.2f}s")
            return result
            
        except Exception as e:
            self.stats['failed_extractions'] += 1
            logger.error(f"❌ Content extraction failed for {url}: {e}")
            
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.HTML_PARSING,
                extraction_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _extract_fast(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extragere rapidă folosind doar metode simple"""
        # Încearcă direct link detection
        if self._is_direct_media_link(url):
            return await self._extract_direct_link(url)
        
        # Încearcă regex extraction
        return await self._extract_with_regex(url, platform_hint)
    
    async def _extract_comprehensive(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extragere comprehensivă folosind toate metodele"""
        methods = [
            self._extract_direct_link,
            self._extract_with_regex,
            self._extract_with_html_parsing,
            self._extract_with_api_call,
            self._extract_with_metadata_parsing
        ]
        
        for method in methods:
            try:
                if method == self._extract_direct_link and not self._is_direct_media_link(url):
                    continue
                
                result = await method(url, platform_hint)
                if result.success and result.confidence_score > 0.7:
                    return result
            except Exception as e:
                logger.debug(f"Method {method.__name__} failed: {e}")
                continue
        
        return ExtractionResult(
            success=False,
            method_used=ExtractionMethod.HTML_PARSING,
            extraction_time=0,
            error_message="All extraction methods failed"
        )
    
    async def _extract_fallback(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extragere cu fallback - încearcă metodele una câte una"""
        methods = [
            (self._extract_direct_link, "direct link"),
            (self._extract_with_regex, "regex"),
            (self._extract_with_html_parsing, "HTML parsing"),
            (self._extract_with_api_call, "API call"),
            (self._extract_with_metadata_parsing, "metadata parsing")
        ]
        
        last_error = None
        
        for method, method_name in methods:
            try:
                if method == self._extract_direct_link and not self._is_direct_media_link(url):
                    continue
                
                logger.debug(f"🔄 Trying {method_name} for {url}")
                result = await method(url, platform_hint)
                
                if result.success:
                    logger.info(f"✅ Success with {method_name}")
                    return result
                else:
                    last_error = result.error_message
                    
            except Exception as e:
                last_error = str(e)
                logger.debug(f"❌ {method_name} failed: {e}")
                continue
        
        return ExtractionResult(
            success=False,
            method_used=ExtractionMethod.HTML_PARSING,
            extraction_time=0,
            error_message=last_error or "All fallback methods failed"
        )
    
    async def _extract_parallel(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extragere în paralel - rulează toate metodele simultan"""
        tasks = []
        
        # Adaugă task-urile pentru fiecare metodă
        if self._is_direct_media_link(url):
            tasks.append(asyncio.create_task(self._extract_direct_link(url, platform_hint)))
        
        tasks.extend([
            asyncio.create_task(self._extract_with_regex(url, platform_hint)),
            asyncio.create_task(self._extract_with_html_parsing(url, platform_hint)),
            asyncio.create_task(self._extract_with_api_call(url, platform_hint)),
            asyncio.create_task(self._extract_with_metadata_parsing(url, platform_hint))
        ])
        
        # Așteaptă primul rezultat de succes
        done, pending = await asyncio.wait(
            tasks, 
            return_when=asyncio.FIRST_COMPLETED,
            timeout=self.config.timeout
        )
        
        # Anulează task-urile rămase
        for task in pending:
            task.cancel()
        
        # Găsește cel mai bun rezultat
        best_result = None
        best_score = 0
        
        for task in done:
            try:
                result = await task
                if result.success and result.confidence_score > best_score:
                    best_result = result
                    best_score = result.confidence_score
            except Exception as e:
                logger.debug(f"Parallel task failed: {e}")
        
        if best_result:
            return best_result
        
        return ExtractionResult(
            success=False,
            method_used=ExtractionMethod.HTML_PARSING,
            extraction_time=0,
            error_message="All parallel extraction methods failed"
        )
    
    async def _extract_direct_link(self, url: str, platform_hint: Optional[str] = None) -> ExtractionResult:
        """Extrage conținut din link-uri directe către media"""
        try:
            # Verifică dacă este link direct către media
            if not self._is_direct_media_link(url):
                return ExtractionResult(
                    success=False,
                    method_used=ExtractionMethod.DIRECT_LINK,
                    extraction_time=0,
                    error_message="Not a direct media link"
                )
            
            # Determină tipul de media
            content_type = self._detect_content_type_from_url(url)
            
            # Creează metadata de bază
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1]
            
            metadata = VideoMetadata(
                title=filename,
                description="Direct media link",
                duration=0,
                view_count=0,
                like_count=0,
                upload_date=datetime.now(),
                uploader="Unknown",
                uploader_id="unknown",
                thumbnail_url="",
                tags=[],
                content_type=content_type
            )
            
            return ExtractionResult(
                success=True,
                method_used=ExtractionMethod.DIRECT_LINK,
                extraction_time=0,
                metadata=metadata,
                media_urls=[url],
                confidence_score=1.0
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.DIRECT_LINK,
                extraction_time=0,
                error_message=str(e)
            )
    
    async def _extract_with_regex(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extrage conținut folosind regex patterns"""
        try:
            # Obține conținutul HTML
            html_content = await self._fetch_html(url)
            
            # Extrage metadata folosind regex
            metadata = self._extract_metadata_with_regex(html_content)
            
            # Extrage URL-uri media
            media_urls = self._extract_media_urls_with_regex(html_content)
            
            # Extrage thumbnail-uri
            thumbnail_urls = self._extract_thumbnail_urls_with_regex(html_content)
            
            # Calculează confidence score
            confidence = self._calculate_confidence_score(metadata, media_urls, thumbnail_urls)
            
            return ExtractionResult(
                success=len(media_urls) > 0 or metadata.title != "Unknown",
                method_used=ExtractionMethod.REGEX_EXTRACTION,
                extraction_time=0,
                metadata=metadata,
                media_urls=media_urls,
                thumbnail_urls=thumbnail_urls,
                confidence_score=confidence
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.REGEX_EXTRACTION,
                extraction_time=0,
                error_message=str(e)
            )
    
    async def _extract_with_html_parsing(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extrage conținut prin parsing HTML"""
        try:
            # Obține conținutul HTML
            html_content = await self._fetch_html(url)
            
            # Parse HTML pentru metadata
            metadata = self._parse_html_metadata(html_content)
            
            # Caută script tags cu date JSON
            json_data = self._extract_json_from_html(html_content)
            
            # Extrage URL-uri media din JSON
            media_urls = self._extract_media_urls_from_json(json_data)
            
            # Extrage thumbnail-uri
            thumbnail_urls = self._extract_thumbnails_from_json(json_data)
            
            # Îmbunătățește metadata cu datele din JSON
            if json_data:
                metadata = self._enhance_metadata_with_json(metadata, json_data)
            
            confidence = self._calculate_confidence_score(metadata, media_urls, thumbnail_urls)
            
            return ExtractionResult(
                success=len(media_urls) > 0 or metadata.title != "Unknown",
                method_used=ExtractionMethod.HTML_PARSING,
                extraction_time=0,
                metadata=metadata,
                media_urls=media_urls,
                thumbnail_urls=thumbnail_urls,
                raw_data=json_data,
                confidence_score=confidence
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.HTML_PARSING,
                extraction_time=0,
                error_message=str(e)
            )
    
    async def _extract_with_api_call(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extrage conținut prin API calls (dacă sunt disponibile)"""
        try:
            # Această metodă ar putea fi implementată pentru platforme specifice
            # care oferă API-uri publice
            
            # Pentru moment, returnează un rezultat de eșec
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.API_CALL,
                extraction_time=0,
                error_message="API extraction not implemented for this platform"
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.API_CALL,
                extraction_time=0,
                error_message=str(e)
            )
    
    async def _extract_with_metadata_parsing(self, url: str, platform_hint: Optional[str]) -> ExtractionResult:
        """Extrage conținut prin parsing metadata (Open Graph, Twitter Cards, etc.)"""
        try:
            html_content = await self._fetch_html(url)
            
            # Extrage Open Graph metadata
            og_metadata = self._extract_open_graph_metadata(html_content)
            
            # Extrage Twitter Card metadata
            twitter_metadata = self._extract_twitter_card_metadata(html_content)
            
            # Combină metadata
            metadata = self._combine_metadata(og_metadata, twitter_metadata)
            
            # Extrage URL-uri media din metadata
            media_urls = []
            thumbnail_urls = []
            
            if og_metadata.get('video'):
                media_urls.append(og_metadata['video'])
            
            if og_metadata.get('image'):
                thumbnail_urls.append(og_metadata['image'])
            
            if twitter_metadata.get('player'):
                media_urls.append(twitter_metadata['player'])
            
            confidence = 0.6 if media_urls else 0.3  # Metadata parsing are confidence mai mică
            
            return ExtractionResult(
                success=len(media_urls) > 0 or metadata.title != "Unknown",
                method_used=ExtractionMethod.METADATA_PARSING,
                extraction_time=0,
                metadata=metadata,
                media_urls=media_urls,
                thumbnail_urls=thumbnail_urls,
                confidence_score=confidence
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                method_used=ExtractionMethod.METADATA_PARSING,
                extraction_time=0,
                error_message=str(e)
            )
    
    async def _fetch_html(self, url: str) -> str:
        """Obține conținutul HTML al unei pagini"""
        headers = self.config.headers.copy()
        
        # Adaugă User-Agent dacă nu este setat
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self.config.user_agent or self.user_agents[0]
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            cookies=self.config.cookies
        ) as session:
            async with session.get(
                url,
                ssl=self.config.verify_ssl,
                allow_redirects=self.config.follow_redirects,
                proxy=self.config.proxy
            ) as response:
                if response.status != 200:
                    raise DownloadError(f"HTTP {response.status}: {response.reason}")
                
                content = await response.text()
                return content
    
    def _is_direct_media_link(self, url: str) -> bool:
        """Verifică dacă URL-ul este un link direct către media"""
        media_extensions = {
            '.mp4', '.webm', '.avi', '.mov', '.flv', '.mkv',  # Video
            '.mp3', '.wav', '.aac', '.ogg', '.m4a',  # Audio
            '.jpg', '.jpeg', '.png', '.gif', '.webp'  # Image
        }
        
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        return any(path.endswith(ext) for ext in media_extensions)
    
    def _detect_content_type_from_url(self, url: str) -> ContentType:
        """Detectează tipul de conținut din URL"""
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        video_extensions = {'.mp4', '.webm', '.avi', '.mov', '.flv', '.mkv'}
        audio_extensions = {'.mp3', '.wav', '.aac', '.ogg', '.m4a'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        
        if any(path.endswith(ext) for ext in video_extensions):
            return ContentType.VIDEO
        elif any(path.endswith(ext) for ext in audio_extensions):
            return ContentType.AUDIO
        elif any(path.endswith(ext) for ext in image_extensions):
            return ContentType.IMAGE
        else:
            return ContentType.VIDEO  # Default
    
    def _extract_metadata_with_regex(self, html_content: str) -> VideoMetadata:
        """Extrage metadata folosind regex patterns"""
        title = self._extract_with_pattern(html_content, self.common_patterns['metadata']['title']) or \
                self._extract_with_pattern(html_content, self.common_patterns['metadata']['og_title']) or \
                "Unknown"
        
        description = self._extract_with_pattern(html_content, self.common_patterns['metadata']['description']) or \
                     self._extract_with_pattern(html_content, self.common_patterns['metadata']['og_description']) or \
                     ""
        
        thumbnail_url = self._extract_with_pattern(html_content, self.common_patterns['metadata']['og_image']) or ""
        
        return VideoMetadata(
            title=title,
            description=description,
            duration=0,
            view_count=0,
            like_count=0,
            upload_date=datetime.now(),
            uploader="Unknown",
            uploader_id="unknown",
            thumbnail_url=thumbnail_url,
            tags=[],
            content_type=ContentType.VIDEO
        )
    
    def _extract_media_urls_with_regex(self, html_content: str) -> List[str]:
        """Extrage URL-uri media folosind regex"""
        media_urls = []
        
        # Caută URL-uri directe către video
        video_matches = re.findall(self.common_patterns['media_urls']['direct_video'], html_content, re.IGNORECASE)
        media_urls.extend(video_matches)
        
        # Caută URL-uri directe către audio
        audio_matches = re.findall(self.common_patterns['media_urls']['direct_audio'], html_content, re.IGNORECASE)
        media_urls.extend(audio_matches)
        
        return list(set(media_urls))  # Remove duplicates
    
    def _extract_thumbnail_urls_with_regex(self, html_content: str) -> List[str]:
        """Extrage URL-uri thumbnail folosind regex"""
        thumbnail_urls = []
        
        # Caută URL-uri directe către imagini
        image_matches = re.findall(self.common_patterns['media_urls']['direct_image'], html_content, re.IGNORECASE)
        thumbnail_urls.extend(image_matches)
        
        # Caută og:image
        og_image = self._extract_with_pattern(html_content, self.common_patterns['metadata']['og_image'])
        if og_image:
            thumbnail_urls.append(og_image)
        
        return list(set(thumbnail_urls))  # Remove duplicates
    
    def _extract_with_pattern(self, text: str, pattern: str) -> Optional[str]:
        """Extrage text folosind un pattern regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else None
    
    def _parse_html_metadata(self, html_content: str) -> VideoMetadata:
        """Parse metadata din HTML folosind multiple metode"""
        # Implementare simplificată - în realitate ar folosi BeautifulSoup sau similar
        return self._extract_metadata_with_regex(html_content)
    
    def _extract_json_from_html(self, html_content: str) -> Dict[str, Any]:
        """Extrage date JSON din script tags"""
        json_data = {}
        
        # Caută script tags cu JSON
        script_patterns = [
            r'<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'<script[^>]*>\s*window\.__APOLLO_STATE__\s*=\s*({.+?});',
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>\s*({.+?})\s*</script>',
            r'<script[^>]*>\s*var\s+\w+\s*=\s*({.+?});'
        ]
        
        for pattern in script_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    data = json.loads(match)
                    json_data.update(data)
                except json.JSONDecodeError:
                    continue
        
        return json_data
    
    def _extract_media_urls_from_json(self, json_data: Dict[str, Any]) -> List[str]:
        """Extrage URL-uri media din datele JSON"""
        media_urls = []
        
        # Caută în structura JSON pentru URL-uri media
        def search_for_media_urls(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ['url', 'src', 'video_url', 'media_url', 'download_url']:
                        if isinstance(value, str) and self._is_media_url(value):
                            media_urls.append(value)
                    else:
                        search_for_media_urls(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_for_media_urls(item, f"{path}[{i}]")
        
        search_for_media_urls(json_data)
        return list(set(media_urls))
    
    def _extract_thumbnails_from_json(self, json_data: Dict[str, Any]) -> List[str]:
        """Extrage URL-uri thumbnail din datele JSON"""
        thumbnail_urls = []
        
        def search_for_thumbnails(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in ['thumbnail', 'thumb', 'poster', 'image', 'cover']:
                        if isinstance(value, str) and self._is_image_url(value):
                            thumbnail_urls.append(value)
                    else:
                        search_for_thumbnails(value)
            elif isinstance(obj, list):
                for item in obj:
                    search_for_thumbnails(item)
        
        search_for_thumbnails(json_data)
        return list(set(thumbnail_urls))
    
    def _enhance_metadata_with_json(self, metadata: VideoMetadata, json_data: Dict[str, Any]) -> VideoMetadata:
        """Îmbunătățește metadata cu datele din JSON"""
        # Caută informații suplimentare în JSON
        def find_value(obj, keys):
            if isinstance(obj, dict):
                for key in keys:
                    if key in obj:
                        return obj[key]
                for value in obj.values():
                    result = find_value(value, keys)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_value(item, keys)
                    if result:
                        return result
            return None
        
        # Actualizează metadata dacă găsește informații mai bune
        title = find_value(json_data, ['title', 'name', 'headline'])
        if title and isinstance(title, str):
            metadata.title = title
        
        description = find_value(json_data, ['description', 'summary', 'content'])
        if description and isinstance(description, str):
            metadata.description = description
        
        duration = find_value(json_data, ['duration', 'length', 'runtime'])
        if duration and isinstance(duration, (int, float)):
            metadata.duration = int(duration)
        
        view_count = find_value(json_data, ['view_count', 'views', 'play_count'])
        if view_count and isinstance(view_count, (int, float)):
            metadata.view_count = int(view_count)
        
        like_count = find_value(json_data, ['like_count', 'likes', 'favorites'])
        if like_count and isinstance(like_count, (int, float)):
            metadata.like_count = int(like_count)
        
        uploader = find_value(json_data, ['uploader', 'author', 'creator', 'channel'])
        if uploader and isinstance(uploader, str):
            metadata.uploader = uploader
        
        return metadata
    
    def _extract_open_graph_metadata(self, html_content: str) -> Dict[str, str]:
        """Extrage Open Graph metadata"""
        og_data = {}
        
        og_patterns = {
            'title': r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\'>]+)["\']',
            'description': r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\'>]+)["\']',
            'image': r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\'>]+)["\']',
            'video': r'<meta[^>]*property=["\']og:video["\'][^>]*content=["\']([^"\'>]+)["\']',
            'url': r'<meta[^>]*property=["\']og:url["\'][^>]*content=["\']([^"\'>]+)["\']',
            'type': r'<meta[^>]*property=["\']og:type["\'][^>]*content=["\']([^"\'>]+)["\']'
        }
        
        for key, pattern in og_patterns.items():
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                og_data[key] = match.group(1)
        
        return og_data
    
    def _extract_twitter_card_metadata(self, html_content: str) -> Dict[str, str]:
        """Extrage Twitter Card metadata"""
        twitter_data = {}
        
        twitter_patterns = {
            'title': r'<meta[^>]*name=["\']twitter:title["\'][^>]*content=["\']([^"\'>]+)["\']',
            'description': r'<meta[^>]*name=["\']twitter:description["\'][^>]*content=["\']([^"\'>]+)["\']',
            'image': r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\'>]+)["\']',
            'player': r'<meta[^>]*name=["\']twitter:player["\'][^>]*content=["\']([^"\'>]+)["\']',
            'card': r'<meta[^>]*name=["\']twitter:card["\'][^>]*content=["\']([^"\'>]+)["\']'
        }
        
        for key, pattern in twitter_patterns.items():
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                twitter_data[key] = match.group(1)
        
        return twitter_data
    
    def _combine_metadata(self, og_data: Dict[str, str], twitter_data: Dict[str, str]) -> VideoMetadata:
        """Combină metadata din Open Graph și Twitter Cards"""
        title = og_data.get('title') or twitter_data.get('title') or "Unknown"
        description = og_data.get('description') or twitter_data.get('description') or ""
        thumbnail_url = og_data.get('image') or twitter_data.get('image') or ""
        
        return VideoMetadata(
            title=title,
            description=description,
            duration=0,
            view_count=0,
            like_count=0,
            upload_date=datetime.now(),
            uploader="Unknown",
            uploader_id="unknown",
            thumbnail_url=thumbnail_url,
            tags=[],
            content_type=ContentType.VIDEO
        )
    
    def _is_media_url(self, url: str) -> bool:
        """Verifică dacă URL-ul pare să fie pentru media"""
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            return False
        
        media_indicators = [
            '.mp4', '.webm', '.avi', '.mov', '.flv', '.mkv',
            '.mp3', '.wav', '.aac', '.ogg', '.m4a',
            'video', 'media', 'stream', 'download'
        ]
        
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in media_indicators)
    
    def _is_image_url(self, url: str) -> bool:
        """Verifică dacă URL-ul pare să fie pentru imagine"""
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            return False
        
        image_indicators = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in image_indicators)
    
    def _calculate_confidence_score(self, metadata: VideoMetadata, media_urls: List[str], thumbnail_urls: List[str]) -> float:
        """Calculează un scor de încredere pentru rezultat"""
        score = 0.0
        
        # Punctaj pentru metadata
        if metadata.title and metadata.title != "Unknown":
            score += 0.3
        
        if metadata.description:
            score += 0.1
        
        if metadata.uploader and metadata.uploader != "Unknown":
            score += 0.1
        
        # Punctaj pentru media URLs
        if media_urls:
            score += 0.4
            # Bonus pentru multiple URLs
            if len(media_urls) > 1:
                score += 0.1
        
        # Punctaj pentru thumbnails
        if thumbnail_urls:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_cache_key(self, url: str) -> str:
        """Generează o cheie de cache pentru URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statisticile extractorului"""
        return self.stats.copy()
    
    def clear_cache(self):
        """Curăță cache-ul"""
        self._cache.clear()
        logger.info("🧹 Content extractor cache cleared")
    
    def __str__(self) -> str:
        return f"ContentExtractor(strategy={self.config.strategy.value}, cache_size={len(self._cache)})"
    
    def __repr__(self) -> str:
        return (f"ContentExtractor(strategy={self.config.strategy.value}, "
                f"timeout={self.config.timeout}, cache_size={len(self._cache)})")


# Singleton instance pentru utilizare globală
content_extractor = ContentExtractor()