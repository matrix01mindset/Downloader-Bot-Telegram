# platforms/twitter.py - Twitter/X Platform Implementation
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

class TwitterPlatform(BasePlatform):
    """
    Twitter/X platform cu gestionare avansată și anti-detection
    
    Caracteristici:
    - Suport pentru twitter.com și x.com
    - URL normalization pentru diverse formate
    - Anti-detection cu User-Agent rotation
    - Fallback pe multiple strategii
    - Optimizat pentru Free Tier hosting
    """
    
    def __init__(self):
        super().__init__()
        self.platform_name = 'twitter'
        
        # Domenii suportate
        self.supported_domains = [
            'twitter.com', 'www.twitter.com', 'mobile.twitter.com',
            'x.com', 'www.x.com', 'mobile.x.com'
        ]
        
        # User agents reali pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        ]
        
        # Strategii de extracție
        self.extraction_strategies = ['twitter', 'generic']
        
        logger.info(f"🐦 Twitter/X platform initialized with {len(self.extraction_strategies)} strategies")
        
    async def is_supported_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este de Twitter/X"""
        if not url or not isinstance(url, str):
            return False
            
        return any(domain in url.lower() for domain in self.supported_domains)
        
    def _normalize_url(self, url: str) -> str:
        """Normalizează URL-urile Twitter/X în formate compatibile"""
        import re
        
        # Convertește x.com în twitter.com pentru compatibilitate
        if 'x.com' in url:
            normalized = url.replace('x.com', 'twitter.com')
            logger.info(f"URL normalized: {url} -> {normalized}")
            return normalized
            
        # Asigură-te că URL-ul are protocolul
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        return url
        
    def _get_extraction_options(self, strategy: str = 'twitter') -> Dict[str, Any]:
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
        
        if strategy == 'twitter':
            base_opts['extractor_args'] = {
                'twitter': {
                    'legacy_api': True,
                    'api_version': '1.1',
                    'guest_token': True
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
        """Extrage metadata Twitter/X fără descărcare"""
        logger.info(f"🔍 Extracting Twitter/X metadata for: {url[:50]}...")
        
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
                        'title': info.get('title', 'Twitter Video'),
                        'description': info.get('description', ''),
                        'uploader': info.get('uploader', 'Twitter User'),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'repost_count': info.get('repost_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'thumbnail': info.get('thumbnail', ''),
                        'webpage_url': normalized_url,
                        'platform': self.name,
                        'strategy_used': strategy
                    }
                    logger.info(f"✅ Metadata extracted with strategy {strategy}: {metadata.get('title', 'Unknown')[:50]}")
                    return metadata
                    
            except Exception as e:
                logger.warning(f"⚠️ Metadata extraction failed with strategy {strategy}: {e}")
                continue
                
        raise Exception("Failed to extract metadata with all strategies")
        
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        """Descarcă video Twitter/X cu fallback pe multiple strategii"""
        logger.info(f"📥 Starting Twitter/X download: {url[:50]}...")
        
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
                            'title': info.get('title', 'Twitter Video'),
                            'description': info.get('description', ''),
                            'uploader': info.get('uploader', 'Twitter User'),
                            'duration': info.get('duration', 0),
                            'strategy_used': strategy
                        }
                        
                        logger.info(f"✅ Twitter/X download successful with strategy {strategy}")
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
                    if 'private' in error_msg or 'protected' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="🔒 This Twitter/X account or tweet is private/protected",
                            platform=self.name
                        )
                    elif 'not found' in error_msg or '404' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="❌ Twitter/X tweet not found or has been deleted",
                            platform=self.name
                        )
                    elif 'suspended' in error_msg:
                        return DownloadResult(
                            success=False,
                            error="🚫 This Twitter/X account has been suspended",
                            platform=self.name
                        )
                    else:
                        return DownloadResult(
                            success=False,
                            error=f"❌ Twitter/X download failed: {str(e)[:100]}",
                            platform=self.name
                        )
                        
                continue
                
        return DownloadResult(
            success=False,
            error="❌ Twitter/X download failed with all strategies",
            platform=self.name
        )
    
    def supports_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este suportat de Twitter/X"""
        return any(domain in url.lower() for domain in self.supported_domains)
    
    async def get_video_info(self, url: str) -> VideoInfo:
        """Extrage informațiile video de pe Twitter/X"""
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
                    title=info.get('title', 'Twitter Video'),
                    description=info.get('description', ''),
                    duration=info.get('duration', 0),
                    uploader=info.get('uploader', ''),
                    thumbnail=info.get('thumbnail', ''),
                    view_count=info.get('view_count', 0),
                    like_count=info.get('like_count', 0),
                    upload_date=info.get('upload_date', ''),
                    webpage_url=url,
                    platform='twitter'
                )
                
        except Exception as e:
            logger.error(f"❌ Error extracting Twitter video info: {e}")
            raise ExtractionError(f"Failed to extract video info: {str(e)}")

# Singleton instance pentru Twitter platform
twitter_platform = TwitterPlatform()