# platforms/dailymotion.py - Dailymotion Platform Implementation
# Versiunea: 2.0.0 - Arhitectura Modulară

import asyncio
import logging
import tempfile
import random
import re
import os
from typing import Dict, Any, List
import yt_dlp

from .base import BasePlatform, DownloadResult, VideoInfo, ExtractionError

logger = logging.getLogger(__name__)

class DailymotionPlatform(BasePlatform):
    """
    Dailymotion platform cu gestionare avansată și anti-detection
    
    Caracteristici:
    - Suport pentru dailymotion.com și dai.ly
    - URL normalization pentru diverse formate
    - Anti-detection cu User-Agent rotation
    - Fallback pe multiple strategii
    - Optimizat pentru Free Tier hosting
    """
    
    def __init__(self):
        super().__init__()
        self.platform_name = 'dailymotion'
        
        # Domenii suportate
        self.supported_domains = [
            'dailymotion.com', 'www.dailymotion.com',
            'dai.ly', 'geo.dailymotion.com'
        ]
        
        # User agents reali pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ]
        
        # Strategii de extracție
        self.extraction_strategies = ['dailymotion', 'generic']
        
        logger.info(f"📺 Dailymotion platform initialized with {len(self.extraction_strategies)} strategies")
        
    async def is_supported_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este de Dailymotion"""
        if not url or not isinstance(url, str):
            return False
            
        return any(domain in url.lower() for domain in self.supported_domains)
        
    def _normalize_url(self, url: str) -> str:
        """Normalizează URL-urile Dailymotion în formate compatibile"""
        import re
        
        # Asigură-te că URL-ul are protocolul
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Expandează URL-urile scurte dai.ly
        if 'dai.ly' in url:
            # dai.ly URL-urile se redirectează automat către dailymotion.com
            logger.info(f"Short Dailymotion URL detected: {url}")
            return url
            
        # Convertește geo.dailymotion.com în www.dailymotion.com
        if 'geo.dailymotion.com' in url:
            normalized = url.replace('geo.dailymotion.com', 'www.dailymotion.com')
            logger.info(f"Geo URL normalized: {url} -> {normalized}")
            return normalized
            
        return url
        
    def _get_extraction_options(self, strategy: str = 'dailymotion') -> Dict[str, Any]:
        """Generează opțiuni de extracție pentru o strategie specifică"""
        user_agent = random.choice(self.user_agents)
        
        base_opts = {
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
                'Referer': 'https://www.dailymotion.com/'
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
        
        if strategy == 'dailymotion':
            base_opts['extractor_args'] = {
                'dailymotion': {
                    'family_filter': False,
                    'api_version': 'v1'
                }
            }
        elif strategy == 'generic':
            base_opts['extractor_args'] = {
                'generic': {
                    'force_generic_extractor': True
                }
            }
            
        return base_opts
        
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Extrage metadata Dailymotion fără descărcare"""
        logger.info(f"🔍 Extracting Dailymotion metadata for: {url[:50]}...")
        
        # Normalizează URL-ul
        normalized_url = self._normalize_url(url)
        
        for strategy in self.extraction_strategies:
            try:
                opts = self._get_extraction_options(strategy)
                opts['skip_download'] = True
                opts['quiet'] = True
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, normalized_url, download=False)
                    
                if info:
                    metadata = {
                        'title': info.get('title', 'Dailymotion Video'),
                        'description': info.get('description', ''),
                        'uploader': info.get('uploader', 'Dailymotion User'),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'thumbnail': info.get('thumbnail', ''),
                        'webpage_url': normalized_url,
                        'platform': self.name,
                        'strategy_used': strategy,
                        'tags': info.get('tags', [])
                    }
                    logger.info(f"✅ Metadata extracted with strategy {strategy}: {metadata.get('title', 'Unknown')[:50]}")
                    return metadata
                    
            except Exception as e:
                logger.warning(f"⚠️ Metadata extraction failed with strategy {strategy}: {e}")
                continue
                
        raise Exception("Failed to extract metadata with all strategies")
        
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        """Descarcă video Dailymotion cu fallback pe multiple strategii"""
        logger.info(f"📥 Starting Dailymotion download: {url[:50]}...")
        
        # Normalizează URL-ul
        normalized_url = self._normalize_url(url)
        
        # Încearcă cu fiecare strategie
        for attempt, strategy in enumerate(self.extraction_strategies, 1):
            try:
                logger.info(f"🔄 Attempt {attempt}/{len(self.extraction_strategies)} with strategy {strategy}")
                
                opts = self._get_extraction_options(strategy)
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
                            'title': info.get('title', 'Dailymotion Video'),
                            'description': info.get('description', ''),
                            'uploader': info.get('uploader', 'Dailymotion User'),
                            'duration': info.get('duration', 0),
                            'strategy_used': strategy,
                            'tags': info.get('tags', [])
                        }
                        
                        logger.info(f"✅ Dailymotion download successful with strategy {strategy}")
                        return DownloadResult(
                            success=True,
                            file_path=output_path,
                            metadata=metadata,
                            platform=self.name
                        )
                        
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"⚠️ Download failed with strategy {strategy}: {e}")
                
                # Dacă este ultima încercare, returnează eroarea
                if attempt == len(self.extraction_strategies):
                    if 'private' in error_msg or 'restricted' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="🔒 This Dailymotion video is private or restricted",
                            platform=self.name
                        )
                    elif 'not found' in error_msg or '404' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="❌ Dailymotion video not found or has been deleted",
                            platform=self.name
                        )
                    elif 'geo' in error_msg or 'region' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="🌍 This Dailymotion video is not available in your region",
                            platform=self.name
                        )
                    elif 'age' in error_msg or 'mature' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="🔞 This Dailymotion video has age restrictions",
                            platform=self.name
                        )
                    else:
                        return DownloadResult(
                            success=False,
                            error=f"❌ Dailymotion download failed: {str(e)[:100]}",
                            platform=self.name
                        )
                        
                continue
                
        return DownloadResult(
            success=False,
            error="❌ Dailymotion download failed with all strategies",
            platform=self.name
        )
    
    def supports_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este suportat de Dailymotion"""
        return any(domain in url.lower() for domain in self.supported_domains)
    
    async def get_video_info(self, url: str) -> VideoInfo:
        """Extrage informațiile video de pe Dailymotion"""
        try:
            # Folosim yt-dlp pentru a extrage informațiile
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return VideoInfo(
                    id=info.get('id', ''),
                    title=info.get('title', 'Dailymotion Video'),
                    description=info.get('description', ''),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', ''),
                    thumbnail=info.get('thumbnail', ''),
                    view_count=info.get('view_count', 0),
                    like_count=info.get('like_count', 0),
                    upload_date=info.get('upload_date', ''),
                    webpage_url=url,
                    platform='dailymotion'
                )
                
        except Exception as e:
            logger.error(f"❌ Error extracting Dailymotion video info: {e}")
            raise ExtractionError(f"Failed to extract video info: {str(e)}")

# Singleton instance pentru Dailymotion platform
dailymotion_platform = DailymotionPlatform()