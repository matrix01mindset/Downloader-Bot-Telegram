# platforms/facebook.py - Facebook Platform Implementation
# Versiunea: 2.0.0 - Arhitectura Modulară

import asyncio
import logging
import tempfile
import random
import re
import os
from typing import Dict, Any, List
import yt_dlp

from .base import BasePlatform, DownloadResult

logger = logging.getLogger(__name__)

class FacebookPlatform(BasePlatform):
    """
    Facebook platform cu gestionare avansată URL și anti-detection mechanisms
    
    Caracteristici:
    - URL normalization pentru share/v/ links
    - Multiple API version fallback (v19.0, v18.0, v17.0)
    - Anti-detection cu User-Agent rotation
    - Fallback pe multiple strategii
    - Optimizat pentru Free Tier hosting
    """
    
    def __init__(self):
        super().__init__()
        self.platform_name = 'facebook'
        
        # Domenii suportate
        self.supported_domains = [
            'facebook.com', 'www.facebook.com', 'm.facebook.com',
            'fb.watch', 'fb.me'
        ]
        
        # API versions pentru fallback
        self.api_versions = ['v19.0', 'v18.0', 'v17.0']
        self.current_api_index = 0
        
        # User agents reali pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ]
        
        logger.info(f"🔵 Facebook platform initialized with {len(self.api_versions)} API versions")
    
    def supports_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este suportat de Facebook platform"""
        if not url:
            return False
            
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.supported_domains)
    
    async def get_video_info(self, url: str) -> 'VideoInfo':
        """Obține informații despre video de pe Facebook"""
        from .base import VideoInfo
        
        try:
            # Normalizează URL-ul
            normalized_url = self._normalize_facebook_url(url)
            
            # Configurează yt-dlp pentru Facebook
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'user_agent': random.choice(self.user_agents),
                'http_headers': {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(normalized_url, download=False)
                
                if not info:
                    raise Exception("Could not extract video information")
                
                # Extrage informațiile necesare
                title = info.get('title', 'Facebook Video')
                duration = info.get('duration', 0)
                thumbnail = info.get('thumbnail', '')
                
                # Găsește cel mai bun format
                formats = info.get('formats', [])
                best_format = None
                
                for fmt in formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                        if not best_format or (fmt.get('height', 0) > best_format.get('height', 0)):
                            best_format = fmt
                
                if not best_format:
                    raise Exception("No suitable video format found")
                
                return VideoInfo(
                    title=title,
                    duration=duration,
                    thumbnail=thumbnail,
                    url=normalized_url,
                    platform='facebook',
                    quality=f"{best_format.get('height', 'unknown')}p",
                    file_size=best_format.get('filesize', 0) or 0
                )
                
        except Exception as e:
            logger.error(f"Error getting Facebook video info: {e}")
            raise Exception(f"Failed to get video info: {str(e)}")
        
    async def is_supported_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este de Facebook"""
        if not url or not isinstance(url, str):
            return False
            
        return any(domain in url.lower() for domain in self.supported_domains)
        
    def _normalize_url(self, url: str) -> str:
        """Normalizează URL-urile Facebook în formate compatibile"""
        import re
        
        # Convertește share/v/ în watch?v=
        if 'facebook.com/share/v/' in url:
            match = re.search(r'facebook\.com/share/v/([^/?]+)', url)
            if match:
                video_id = match.group(1)
                normalized = f"https://www.facebook.com/watch?v={video_id}"
                logger.info(f"URL normalized: {url} -> {normalized}")
                return normalized
                
        # Convertește reel/ în watch?v=
        if 'facebook.com/reel/' in url:
            match = re.search(r'facebook\.com/reel/([^/?]+)', url)
            if match:
                reel_id = match.group(1)
                normalized = f"https://www.facebook.com/watch?v={reel_id}"
                logger.info(f"Reel URL normalized: {url} -> {normalized}")
                return normalized
                
        return url
        
    def _get_next_api_version(self) -> str:
        """Obține următoarea versiune API pentru rotation"""
        api_version = self.api_versions[self.current_api_index]
        self.current_api_index = (self.current_api_index + 1) % len(self.api_versions)
        return api_version
        
    def _get_extraction_options(self, api_version: str) -> Dict[str, Any]:
        """Generează opțiuni de extracție pentru o versiune API specifică"""
        user_agent = random.choice(self.user_agents)
        
        return {
            'format': 'best[filesize<45M][height<=720]/best[height<=720]/best[filesize<45M]/best',
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
            'extractor_args': {
                'facebook': {
                    'api_version': api_version,
                    'legacy_ssl': True,
                    'tab': 'videos',
                    'ignore_parse_errors': True
                }
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            'retries': 3,
            'ignoreerrors': True,
            'sleep_interval': 2,
            'max_sleep_interval': 5,
            'geo_bypass': True,
            'geo_bypass_country': 'US'
        }
        
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Extrage metadata Facebook fără descărcare"""
        logger.info(f"🔍 Extracting Facebook metadata for: {url[:50]}...")
        
        # Normalizează URL-ul
        normalized_url = self._normalize_url(url)
        
        for api_version in self.api_versions:
            try:
                opts = self._get_extraction_options(api_version)
                opts['skip_download'] = True
                opts['quiet'] = True
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, normalized_url, download=False)
                    
                if info:
                    metadata = {
                        'title': info.get('title', 'Facebook Video'),
                        'description': info.get('description', ''),
                        'uploader': info.get('uploader', 'Facebook User'),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'thumbnail': info.get('thumbnail', ''),
                        'webpage_url': normalized_url,
                        'platform': self.name,
                        'api_version_used': api_version
                    }
                    logger.info(f"✅ Metadata extracted with API {api_version}: {metadata.get('title', 'Unknown')[:50]}")
                    return metadata
                    
            except Exception as e:
                logger.warning(f"⚠️ Metadata extraction failed with API {api_version}: {e}")
                continue
                
        raise Exception("Failed to extract metadata with all API versions")
        
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        """Descarcă video Facebook cu fallback pe multiple API versions"""
        logger.info(f"📥 Starting Facebook download: {url[:50]}...")
        
        # Normalizează URL-ul
        normalized_url = self._normalize_url(url)
        
        # Încearcă cu fiecare versiune API
        for attempt, api_version in enumerate(self.api_versions, 1):
            try:
                logger.info(f"🔄 Attempt {attempt}/{len(self.api_versions)} with API {api_version}")
                
                opts = self._get_extraction_options(api_version)
                opts['outtmpl'] = output_path
                opts['quiet'] = False
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # Extrage metadata mai întâi
                    info = await asyncio.to_thread(ydl.extract_info, normalized_url, download=False)
                    
                    if not info:
                        continue
                        
                    # Verifică constrângerile
                    validation = await self.validate_constraints(info)
                    if not validation['valid']:
                        return DownloadResult(
                            success=False,
                            error=validation['error'],
                            platform=self.name
                        )
                    
                    # Descarcă videoclipul
                    await asyncio.to_thread(ydl.download, [normalized_url])
                    
                    # Verifică dacă fișierul a fost descărcat
                    if os.path.exists(output_path):
                        metadata = {
                            'title': info.get('title', 'Facebook Video'),
                            'description': info.get('description', ''),
                            'uploader': info.get('uploader', 'Facebook User'),
                            'duration': info.get('duration', 0),
                            'api_version_used': api_version
                        }
                        
                        logger.info(f"✅ Facebook download successful with API {api_version}")
                        return DownloadResult(
                            success=True,
                            file_path=output_path,
                            metadata=metadata,
                            platform=self.name
                        )
                        
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"⚠️ Download failed with API {api_version}: {e}")
                
                # Dacă este ultima încercare, returnează eroarea
                if attempt == len(self.api_versions):
                    if 'private' in error_msg or 'restricted' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="🔒 This Facebook video is private or restricted",
                            platform=self.name
                        )
                    elif 'not found' in error_msg or '404' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="❌ Facebook video not found or has been deleted",
                            platform=self.name
                        )
                    else:
                        return DownloadResult(
                            success=False,
                            error=f"❌ Facebook download failed: {str(e)[:100]}",
                            platform=self.name
                        )
                        
                continue
                
        return DownloadResult(
            success=False,
            error="❌ Facebook download failed with all API versions",
            platform=self.name
        )

# Singleton instance pentru Facebook platform
facebook_platform = FacebookPlatform()