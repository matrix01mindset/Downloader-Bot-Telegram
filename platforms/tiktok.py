# platforms/tiktok.py - TikTok Platform cu Anti-Detection Avansată
# Versiunea: 3.0.0 - Arhitectura Nouă
# Versiunea: 2.0.0 - Arhitectura Modulară

import re
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
from datetime import datetime
from urllib.parse import unquote, urlparse, parse_qs

try:
    from platforms.base import BasePlatform, VideoInfo, PlatformCapability
    from utils.cache import cache, generate_cache_key, cached
    from utils.monitoring import monitoring, trace_operation
    from utils.retry_manager import RetryStrategy
except ImportError:
    # Fallback pentru development/testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

class TikTokPlatform(BasePlatform):
    """
    TikTok video downloader cu suport pentru:
    - Video-uri individuale (cu și fără watermark)
    - Profile complete
    - Hashtag collections
    - Trending videos
    
    Caracteristici:
    - Multiple extraction methods (web, API)
    - Anti-bot protection bypass
    - User-agent și header rotation
    - Suport pentru video fără watermark
    - Batch download pentru profile
    """
    
    def __init__(self):
        super().__init__()
        self.platform_name = "tiktok"
        self.base_url = "https://www.tiktok.com"
        
        # Capabilities specific TikTok
        self.capabilities = {
            PlatformCapability.DOWNLOAD_VIDEO,
            PlatformCapability.DOWNLOAD_AUDIO,
            PlatformCapability.GET_METADATA,
            PlatformCapability.GET_THUMBNAIL,
            PlatformCapability.BATCH_DOWNLOAD,
            PlatformCapability.CUSTOM_QUALITY,
            PlatformCapability.PLAYLIST_SUPPORT
        }
        
        # User agents pentru anti-detection
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/109.0 Firefox/119.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.current_ua_index = 0
        
        # Headers pentru requests
        self.base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # API endpoints și patterns
        self.api_endpoints = {
            'web_app': 'https://www.tiktok.com/api/item/detail/',
            'share_app': 'https://www.tiktok.com/api/item/detail/',
            'user_info': 'https://www.tiktok.com/api/user/detail/',
            'user_posts': 'https://www.tiktok.com/api/post/item_list/'
        }
        
        # URL patterns pentru matching
        self.url_patterns = [
            r'https?://(?:www\.|vm\.|m\.)?tiktok\.com/@([^/]+)/video/(\d+)',        # Standard video
            r'https?://(?:www\.|m\.)?tiktok\.com/t/([A-Za-z0-9]+)/?',              # Shortened URL
            r'https?://vm\.tiktok\.com/([A-Za-z0-9]+)/?',                          # VM shortened
            r'https?://(?:www\.|m\.)?tiktok\.com/@([^/]+)/?$',                     # User profile
            r'https?://(?:www\.|m\.)?tiktok\.com/tag/([^/]+)',                     # Hashtag
        ]
        
        logger.info("🎵 TikTok Platform initialized")
        
    def supports_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este suportat"""
        return any(re.match(pattern, url) for pattern in self.url_patterns)
        
    def _get_next_user_agent(self) -> str:
        """Obține următorul user agent pentru rotation"""
        ua = self.user_agents[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return ua
        
    def _parse_url(self, url: str) -> Dict[str, Any]:
        """Parse URL-ul și determină tipul conținutului"""
        
        # Standard video URL
        video_match = re.match(r'https?://(?:www\.|vm\.|m\.)?tiktok\.com/@([^/]+)/video/(\d+)', url)
        if video_match:
            return {
                'type': 'video',
                'username': video_match.group(1),
                'video_id': video_match.group(2),
                'id': video_match.group(2)
            }
            
        # Shortened URLs (t/xxx sau vm.tiktok.com/xxx)
        short_match = re.match(r'https?://(?:(?:www\.|m\.)?tiktok\.com/t/|vm\.tiktok\.com/)([A-Za-z0-9]+)', url)
        if short_match:
            return {
                'type': 'short',
                'short_code': short_match.group(1),
                'id': short_match.group(1),
                'needs_resolve': True
            }
            
        # User profile
        user_match = re.match(r'https?://(?:www\.|m\.)?tiktok\.com/@([^/]+)/?$', url)
        if user_match:
            return {
                'type': 'user',
                'username': user_match.group(1),
                'id': user_match.group(1)
            }
            
        # Hashtag
        hashtag_match = re.match(r'https?://(?:www\.|m\.)?tiktok\.com/tag/([^/]+)', url)
        if hashtag_match:
            return {
                'type': 'hashtag',
                'hashtag': hashtag_match.group(1),
                'id': hashtag_match.group(1)
            }
            
        return {'type': 'unknown', 'id': 'unknown'}
        
    async def _resolve_short_url(self, short_url: str) -> str:
        """Rezolvă URL-urile scurte TikTok"""
        
        cache_key = generate_cache_key("tiktok_short_url", short_url)
        cached_url = cache.get(cache_key)
        
        if cached_url:
            logger.debug(f"📦 Using cached resolved URL for: {short_url}")
            return cached_url
            
        try:
            headers = self.base_headers.copy()
            headers['User-Agent'] = self._get_next_user_agent()
            
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(short_url, headers=headers, allow_redirects=False) as response:
                    
                    # Urmărește redirect-urile manual pentru control
                    redirect_url = short_url
                    max_redirects = 5
                    redirects = 0
                    
                    while response.status in (301, 302, 303, 307, 308) and redirects < max_redirects:
                        redirect_url = response.headers.get('Location', '')
                        if redirect_url:
                            async with session.get(redirect_url, headers=headers, allow_redirects=False) as redirect_response:
                                response = redirect_response
                                redirects += 1
                        else:
                            break
                            
                    # Cache rezultatul pentru 1 oră
                    cache.put(cache_key, redirect_url, ttl=3600, priority="high")
                    
                    return redirect_url
                    
        except Exception as e:
            logger.error(f"❌ Error resolving TikTok short URL {short_url}: {e}")
            if monitoring:
                monitoring.record_error("tiktok", "url_resolution", str(e))
            return short_url  # Returnează URL-ul original dacă nu poate rezolva
            
    async def _make_request(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Face un request cu headers și protection bypass"""
        
        headers = self.base_headers.copy()
        headers['User-Agent'] = self._get_next_user_agent()
        
        # Adaugă headers specifice TikTok pentru API calls
        if '/api/' in url:
            headers.update({
                'Referer': 'https://www.tiktok.com/',
                'X-Requested-With': 'XMLHttpRequest',
            })
            
        # Override headers dacă sunt specificate
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
            
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                return response
                
    async def _extract_from_webpage(self, url: str) -> Dict[str, Any]:
        """Extrage date din pagina web TikTok"""
        
        cache_key = generate_cache_key("tiktok_webpage_data", url)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"📦 Using cached webpage data for: {url}")
            return cached_data
            
        try:
            response = await self._make_request(url)
            html = await response.text()
            
            # Caută __NEXT_DATA__ script tag
            next_data_pattern = r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>'
            match = re.search(next_data_pattern, html)
            
            if match:
                try:
                    next_data = json.loads(match.group(1))
                    
                    # Cache pentru 10 minute
                    cache.put(cache_key, next_data, ttl=600, priority="high")
                    
                    return next_data
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Could not parse __NEXT_DATA__: {e}")
                    
            # Fallback: caută alte script tags cu date
            script_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
            script_match = re.search(script_pattern, html)
            
            if script_match:
                try:
                    initial_state = json.loads(script_match.group(1))
                    cache.put(cache_key, initial_state, ttl=600, priority="high")
                    return initial_state
                except json.JSONDecodeError:
                    pass
                    
            logger.warning("⚠️ Could not find structured data in TikTok page")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error extracting webpage data from {url}: {e}")
            if monitoring:
                monitoring.record_error("tiktok", "webpage_extraction", str(e))
            return {}
            
    def _extract_video_info(self, data: Dict[str, Any], video_id: str) -> Optional[Dict[str, Any]]:
        """Extrage informații video din datele structurate"""
        
        try:
            # Încearcă să găsească video data în structura __NEXT_DATA__
            if 'props' in data and 'pageProps' in data['props']:
                page_props = data['props']['pageProps']
                
                # Caută în itemInfo
                if 'itemInfo' in page_props and 'itemStruct' in page_props['itemInfo']:
                    return page_props['itemInfo']['itemStruct']
                    
                # Caută în altres structuri
                if 'videoData' in page_props:
                    return page_props['videoData']
                    
            # Încearcă să găsească în alte locații
            if 'ItemModule' in data:
                for key, item in data['ItemModule'].items():
                    if str(item.get('id')) == str(video_id):
                        return item
                        
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting video info: {e}")
            return None
            
    def _parse_tiktok_video(self, video_data: Dict[str, Any]) -> VideoInfo:
        """Parse datele video TikTok într-un VideoInfo"""
        
        try:
            # Basic info
            video_id = str(video_data.get('id', 'unknown'))
            desc = video_data.get('desc', '')
            
            # Author info
            author = video_data.get('author', {})
            username = author.get('uniqueId', 'unknown')
            nickname = author.get('nickname', username)
            
            # Video URLs și metadata
            video_obj = video_data.get('video', {})
            
            # Format URLs (încearcă să găsească cea mai bună calitate)
            formats = []
            
            # Download URL (fără watermark, dacă e disponibil)
            download_addr = video_obj.get('downloadAddr', '')
            if download_addr:
                formats.append({
                    'url': download_addr,
                    'format_id': 'download',
                    'ext': 'mp4',
                    'quality': 'no_watermark',
                    'filesize': None,
                    'width': video_obj.get('width'),
                    'height': video_obj.get('height'),
                    'fps': None,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'preference': 100  # Preferință înaltă pentru fără watermark
                })
                
            # Play URL (cu watermark)
            play_addr = video_obj.get('playAddr', '')
            if play_addr:
                formats.append({
                    'url': play_addr,
                    'format_id': 'play',
                    'ext': 'mp4',
                    'quality': 'with_watermark',
                    'filesize': None,
                    'width': video_obj.get('width'),
                    'height': video_obj.get('height'),
                    'fps': None,
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'preference': 50  # Preferință mai scăzută
                })
                
            # Alternative URLs
            if 'bitrateInfo' in video_obj:
                for bitrate_info in video_obj['bitrateInfo']:
                    play_url = bitrate_info.get('PlayAddr', {}).get('UrlList', [])
                    if play_url:
                        formats.append({
                            'url': play_url[0],
                            'format_id': f"bitrate_{bitrate_info.get('Bitrate', 'unknown')}",
                            'ext': 'mp4',
                            'quality': f"{bitrate_info.get('Bitrate', 0)}kbps",
                            'filesize': None,
                            'width': video_obj.get('width'),
                            'height': video_obj.get('height'),
                            'fps': None,
                            'vcodec': 'h264',
                            'acodec': 'aac',
                            'preference': bitrate_info.get('Bitrate', 0) // 1000
                        })
                        
            # Thumbnail
            thumbnail_url = None
            if 'cover' in video_obj:
                cover_urls = video_obj['cover'].get('UrlList', [])
                thumbnail_url = cover_urls[0] if cover_urls else None
                
            # Statistics
            stats = video_data.get('stats', {})
            play_count = stats.get('playCount', 0)
            digg_count = stats.get('diggCount', 0)  # Likes
            share_count = stats.get('shareCount', 0)
            comment_count = stats.get('commentCount', 0)
            
            # Music info
            music = video_data.get('music', {})
            music_title = music.get('title', '')
            music_author = music.get('authorName', '')
            
            # Duration
            duration = video_obj.get('duration', 0) / 1000.0 if video_obj.get('duration') else None
            
            # Upload date
            create_time = video_data.get('createTime', 0)
            upload_date = datetime.fromtimestamp(create_time).isoformat() if create_time else None
            
            # Hashtags
            hashtags = []
            if 'challenges' in video_data:
                for challenge in video_data['challenges']:
                    hashtags.append(challenge.get('title', '').replace('#', ''))
                    
            # Construiește VideoInfo
            video_info = VideoInfo(
                id=video_id,
                title=desc[:100] + "..." if len(desc) > 100 else desc or f"TikTok by @{username}",
                description=desc,
                duration=duration,
                uploader=nickname,
                uploader_id=username,
                uploader_url=f"https://tiktok.com/@{username}",
                upload_date=upload_date,
                view_count=play_count,
                like_count=digg_count,
                comment_count=comment_count,
                thumbnail=thumbnail_url,
                webpage_url=f"https://tiktok.com/@{username}/video/{video_id}",
                formats=sorted(formats, key=lambda x: x.get('preference', 0), reverse=True),
                platform="tiktok",
                platform_id=video_id,
                extra_info={
                    'author': author,
                    'music': music,
                    'music_title': music_title,
                    'music_author': music_author,
                    'hashtags': hashtags,
                    'share_count': share_count,
                    'challenges': video_data.get('challenges', []),
                    'is_ad': video_data.get('isAd', False),
                    'video_quality': video_obj.get('quality', 'unknown')
                }
            )
            
            return video_info
            
        except Exception as e:
            logger.error(f"❌ Error parsing TikTok video: {e}")
            raise
            
    @trace_operation("tiktok_get_info")
    async def get_video_info(self, url: str) -> VideoInfo:
        """Obține informații despre video de pe TikTok"""
        
        parsed = self._parse_url(url)
        content_type = parsed['type']
        
        if content_type == 'unknown':
            raise ValueError(f"Unsupported TikTok URL format: {url}")
            
        # Rezolvă URL-urile scurte
        if content_type == 'short':
            resolved_url = await self._resolve_short_url(url)
            parsed = self._parse_url(resolved_url)
            content_type = parsed['type']
            url = resolved_url
            
        if content_type == 'video':
            return await self._get_video_info(url, parsed)
        elif content_type == 'user':
            raise ValueError("User profile URLs require specific video selection")
        elif content_type == 'hashtag':
            raise ValueError("Hashtag URLs require specific video selection")
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
            
    async def _get_video_info(self, url: str, parsed: Dict[str, Any]) -> VideoInfo:
        """Obține informații pentru un video specific"""
        
        try:
            webpage_data = await self._extract_from_webpage(url)
            
            if not webpage_data:
                raise Exception("Could not extract data from TikTok page")
                
            video_data = self._extract_video_info(webpage_data, parsed['video_id'])
            
            if not video_data:
                raise Exception("Could not find video data in page")
                
            video_info = self._parse_tiktok_video(video_data)
            
            # Record success
            if monitoring:
                monitoring.record_download_attempt("tiktok", True, 0)
                
            return video_info
            
        except Exception as e:
            logger.error(f"❌ Error getting TikTok video info: {e}")
            if monitoring:
                monitoring.record_error("tiktok", "video_info_extraction", str(e))
            raise
            
    @trace_operation("tiktok_download")
    async def download_video(self, 
                           video_info: VideoInfo, 
                           output_path: str,
                           quality: Optional[str] = None,
                           format_preference: Optional[str] = None) -> str:
        """Descarcă video de pe TikTok"""
        
        if not video_info.formats:
            raise ValueError("No downloadable formats found")
            
        # Selectează cel mai bun format
        selected_format = self._select_best_format(
            video_info.formats, 
            quality, 
            format_preference
        )
        
        if not selected_format:
            raise ValueError("No suitable format found")
            
        # Descarcă fișierul
        return await self._download_file(
            selected_format['url'],
            output_path,
            video_info.id,
            selected_format.get('ext', 'mp4')
        )
        
    async def _download_file(self, url: str, output_path: str, filename: str, ext: str) -> str:
        """Descarcă fișierul de la URL"""
        
        import os
        import aiofiles
        
        full_filename = f"{filename}.{ext}"
        file_path = os.path.join(output_path, full_filename)
        
        try:
            response = await self._make_request(url)
            
            # Creează directorul dacă nu există
            os.makedirs(output_path, exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
                    
            logger.info(f"✅ Downloaded TikTok video: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Error downloading file: {e}")
            if monitoring:
                monitoring.record_error("tiktok", "file_download", str(e))
            raise
            
    async def get_playlist_info(self, url: str) -> List[VideoInfo]:
        """Obține info pentru mai multe videoclipuri (user profile, hashtag)"""
        
        parsed = self._parse_url(url)
        content_type = parsed['type']
        
        if content_type == 'video':
            # Pentru video singular
            info = await self.get_video_info(url)
            return [info]
        elif content_type == 'user':
            return await self._get_user_videos(parsed['username'])
        elif content_type == 'hashtag':
            return await self._get_hashtag_videos(parsed['hashtag'])
        else:
            return []
            
    async def _get_user_videos(self, username: str, limit: int = 20) -> List[VideoInfo]:
        """Obține videoclipurile unui user"""
        
        logger.warning(f"⚠️ User video extraction for @{username} not fully implemented")
        logger.warning("💡 Please provide specific video URLs instead")
        
        # Implementare simplificată - necesită API complex pentru user feeds
        return []
        
    async def _get_hashtag_videos(self, hashtag: str, limit: int = 20) -> List[VideoInfo]:
        """Obține videoclipurile pentru un hashtag"""
        
        logger.warning(f"⚠️ Hashtag video extraction for #{hashtag} not fully implemented")
        logger.warning("💡 Please provide specific video URLs instead")
        
        # Implementare simplificată - necesită API complex pentru hashtag feeds
        return []
        
    def _select_best_format(self, 
                          formats: List[Dict[str, Any]], 
                          quality: Optional[str] = None,
                          format_preference: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Selectează cel mai bun format pentru descărcare"""
        
        if not formats:
            return None
            
        # Pentru TikTok, preferăm format-urile fără watermark
        if format_preference == "no_watermark":
            no_watermark_formats = [f for f in formats if f.get('quality') == 'no_watermark']
            if no_watermark_formats:
                return no_watermark_formats[0]
                
        # Sortează după preferință și apoi după calitate
        sorted_formats = sorted(
            formats,
            key=lambda f: (f.get('preference', 0), f.get('height', 0)),
            reverse=True
        )
        
        # Dacă nu e specificată calitatea, ia cea mai bună
        if not quality or quality == 'best':
            return sorted_formats[0]
            
        # Pentru calități specifice
        if quality == 'worst':
            return sorted_formats[-1]
        elif quality == 'no_watermark':
            no_watermark_formats = [f for f in sorted_formats if f.get('quality') == 'no_watermark']
            return no_watermark_formats[0] if no_watermark_formats else sorted_formats[0]
            
        # Default
        return sorted_formats[0]

# Export pentru registry
__all__ = ['TikTokPlatform']
