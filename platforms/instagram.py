# platforms/instagram.py - Instagram Platform Implementation
# Versiunea: 2.0.0 - Arhitectura Modulară

import re
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
from datetime import datetime

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

class InstagramPlatform(BasePlatform):
    """
    Instagram video downloader cu suport pentru:
    - Posts (video și carousel)
    - Reels 
    - Stories
    - IGTV
    - Profile posts browsing
    
    Caracteristici:
    - Evită API restrictions prin web scraping
    - User-agent rotation pentru anti-detection
    - Rate limiting intelligent
    - Cache pentru metadata și URLs
    """
    
    def __init__(self):
        super().__init__()
        self.platform_name = "instagram"
        self.base_url = "https://www.instagram.com"
        
        # Capabilities specific Instagram
        self.capabilities = {
            PlatformCapability.DOWNLOAD_VIDEO,
            PlatformCapability.DOWNLOAD_AUDIO,  # Din video
            PlatformCapability.GET_METADATA,
            PlatformCapability.GET_THUMBNAIL,
            PlatformCapability.BATCH_DOWNLOAD,
            PlatformCapability.CUSTOM_QUALITY
        }
        
        # User agents pentru rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.current_ua_index = 0
        
        # Headers pentru requests
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors", 
            "Sec-Fetch-Site": "same-origin"
        }
        
        # Patterns pentru URL matching
        self.url_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/([A-Za-z0-9_-]+)',           # Posts
            r'https?://(?:www\.)?instagram\.com/reel/([A-Za-z0-9_-]+)',       # Reels
            r'https?://(?:www\.)?instagram\.com/tv/([A-Za-z0-9_-]+)',         # IGTV
            r'https?://(?:www\.)?instagram\.com/stories/([^/]+)/([0-9]+)',    # Stories
            r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)',            # Profile
        ]
        
        logger.info("📷 Instagram Platform initialized")
        
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
        
        # Post/Media
        post_match = re.match(r'https?://(?:www\.)?instagram\.com/p/([A-Za-z0-9_-]+)', url)
        if post_match:
            return {
                'type': 'post',
                'shortcode': post_match.group(1),
                'id': post_match.group(1)
            }
            
        # Reel
        reel_match = re.match(r'https?://(?:www\.)?instagram\.com/reel/([A-Za-z0-9_-]+)', url)
        if reel_match:
            return {
                'type': 'reel',
                'shortcode': reel_match.group(1),
                'id': reel_match.group(1)
            }
            
        # IGTV
        igtv_match = re.match(r'https?://(?:www\.)?instagram\.com/tv/([A-Za-z0-9_-]+)', url)
        if igtv_match:
            return {
                'type': 'igtv',
                'shortcode': igtv_match.group(1),
                'id': igtv_match.group(1)
            }
            
        # Story
        story_match = re.match(r'https?://(?:www\.)?instagram\.com/stories/([^/]+)/([0-9]+)', url)
        if story_match:
            return {
                'type': 'story',
                'username': story_match.group(1),
                'story_id': story_match.group(2),
                'id': f"{story_match.group(1)}_{story_match.group(2)}"
            }
            
        # Profile
        profile_match = re.match(r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)', url)
        if profile_match:
            return {
                'type': 'profile',
                'username': profile_match.group(1),
                'id': profile_match.group(1)
            }
            
        return {'type': 'unknown', 'id': 'unknown'}
        
    async def _make_request(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Face un request cu headers și rotation de user-agent"""
        
        headers = self.headers.copy()
        headers['User-Agent'] = self._get_next_user_agent()
        
        # Override headers dacă sunt specificate
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
            
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                return response
                
    async def _get_shared_data(self, url: str) -> Dict[str, Any]:
        """Extrage shared data din pagina Instagram"""
        
        cache_key = generate_cache_key("instagram_shared_data", url)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"📦 Using cached shared data for: {url}")
            return cached_data
            
        try:
            response = await self._make_request(url)
            html = await response.text()
            
            # Extract shared data din script tag
            shared_data_pattern = r'window\._sharedData\s*=\s*({.*?});'
            match = re.search(shared_data_pattern, html)
            
            if match:
                shared_data = json.loads(match.group(1))
                
                # Cache pentru 10 minute
                cache.put(cache_key, shared_data, ttl=600, priority="high")
                
                return shared_data
            else:
                logger.warning("⚠️ Could not find shared data in Instagram page")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error getting shared data from {url}: {e}")
            if monitoring:
                monitoring.record_error("instagram", "shared_data_extraction", str(e))
            return {}
            
    async def _extract_media_info(self, shared_data: Dict[str, Any], shortcode: str) -> Optional[Dict[str, Any]]:
        """Extrage informații despre media din shared data"""
        
        try:
            # Caută în entry_data
            entry_data = shared_data.get('entry_data', {})
            
            # PostPage pentru posts normale
            if 'PostPage' in entry_data:
                posts = entry_data['PostPage'][0]['graphql']['shortcode_media']
                return posts
                
            # Alte tipuri de pagini
            for page_type in entry_data:
                if page_type.endswith('Page') and entry_data[page_type]:
                    page_data = entry_data[page_type][0]
                    
                    if 'graphql' in page_data:
                        # Caută shortcode_media
                        if 'shortcode_media' in page_data['graphql']:
                            return page_data['graphql']['shortcode_media']
                            
                        # Caută în user->edge_owner_to_timeline_media
                        if 'user' in page_data['graphql']:
                            user_data = page_data['graphql']['user']
                            timeline = user_data.get('edge_owner_to_timeline_media', {})
                            
                            for edge in timeline.get('edges', []):
                                node = edge['node']
                                if node.get('shortcode') == shortcode:
                                    return node
                                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting media info: {e}")
            return None
            
    def _parse_instagram_media(self, media_data: Dict[str, Any]) -> VideoInfo:
        """Parse datele media Instagram într-un VideoInfo"""
        
        try:
            # Basic info
            shortcode = media_data.get('shortcode', 'unknown')
            typename = media_data.get('__typename', 'unknown')
            
            # Owner info  
            owner = media_data.get('owner', {})
            username = owner.get('username', 'unknown')
            full_name = owner.get('full_name', username)
            
            # Media URLs
            video_url = None
            thumbnail_url = None
            duration = None
            
            # Pentru video content
            if typename in ['GraphVideo', 'GraphSidecar'] or media_data.get('is_video'):
                video_url = media_data.get('video_url')
                duration = media_data.get('video_duration', 0)
                
            # Thumbnail
            display_resources = media_data.get('display_resources', [])
            if display_resources:
                # Ia cea mai mare rezoluție
                thumbnail_url = display_resources[-1]['src']
            else:
                thumbnail_url = media_data.get('display_url')
                
            # Caption
            caption_edges = media_data.get('edge_media_to_caption', {}).get('edges', [])
            caption = ""
            if caption_edges:
                caption = caption_edges[0]['node']['text']
                
            # Stats
            likes = media_data.get('edge_media_preview_like', {}).get('count', 0)
            comments = media_data.get('edge_media_to_comment', {}).get('count', 0)
            views = media_data.get('video_view_count', 0)
            
            # Timestamps
            taken_at = media_data.get('taken_at_timestamp', 0)
            upload_date = datetime.fromtimestamp(taken_at).isoformat() if taken_at else None
            
            # Construiește VideoInfo
            video_info = VideoInfo(
                id=shortcode,
                title=caption[:100] + "..." if len(caption) > 100 else caption,
                description=caption,
                duration=duration,
                uploader=username,
                uploader_id=username,
                uploader_url=f"https://instagram.com/{username}",
                upload_date=upload_date,
                view_count=views,
                like_count=likes,
                comment_count=comments,
                thumbnail=thumbnail_url,
                webpage_url=f"https://instagram.com/p/{shortcode}",
                formats=[],  # Va fi populat cu video_url
                platform="instagram",
                platform_id=shortcode,
                extra_info={
                    'typename': typename,
                    'owner': owner,
                    'is_video': media_data.get('is_video', False),
                    'accessibility_caption': media_data.get('accessibility_caption', ''),
                    'location': media_data.get('location'),
                    'hashtags': self._extract_hashtags(caption)
                }
            )
            
            # Adaugă format pentru video dacă există
            if video_url:
                video_info.formats.append({
                    'url': video_url,
                    'format_id': 'mp4',
                    'ext': 'mp4',
                    'quality': 'unknown',
                    'filesize': None,
                    'width': media_data.get('dimensions', {}).get('width'),
                    'height': media_data.get('dimensions', {}).get('height'),
                    'fps': None,
                    'vcodec': 'h264',
                    'acodec': 'aac'
                })
                
            return video_info
            
        except Exception as e:
            logger.error(f"❌ Error parsing Instagram media: {e}")
            raise
            
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extrage hashtag-urile din text"""
        if not text:
            return []
            
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
        return hashtags
        
    @trace_operation("instagram_get_info")
    async def get_video_info(self, url: str) -> VideoInfo:
        """Obține informații despre video de pe Instagram"""
        
        parsed = self._parse_url(url)
        content_type = parsed['type']
        
        if content_type == 'unknown':
            raise ValueError(f"Unsupported Instagram URL format: {url}")
            
        if content_type in ['post', 'reel', 'igtv']:
            return await self._get_media_info(url, parsed)
        elif content_type == 'story':
            return await self._get_story_info(url, parsed) 
        elif content_type == 'profile':
            raise ValueError("Profile URLs require specific post selection")
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
            
    async def _get_media_info(self, url: str, parsed: Dict[str, Any]) -> VideoInfo:
        """Obține info pentru post/reel/igtv"""
        
        try:
            shared_data = await self._get_shared_data(url)
            
            if not shared_data:
                raise Exception("Could not extract shared data from Instagram")
                
            media_data = await self._extract_media_info(shared_data, parsed['shortcode'])
            
            if not media_data:
                raise Exception("Could not find media data in page")
                
            video_info = self._parse_instagram_media(media_data)
            
            # Record success
            if monitoring:
                monitoring.record_download_attempt("instagram", True, 0)
                
            return video_info
            
        except Exception as e:
            logger.error(f"❌ Error getting Instagram media info: {e}")
            if monitoring:
                monitoring.record_error("instagram", "media_info_extraction", str(e))
            raise
            
    async def _get_story_info(self, url: str, parsed: Dict[str, Any]) -> VideoInfo:
        """Obține info pentru story (implementare de bază)"""
        
        # Stories necesită autentificare în cele mai multe cazuri
        # Implementare simplificată
        
        username = parsed['username']
        story_id = parsed['story_id']
        
        video_info = VideoInfo(
            id=f"{username}_{story_id}",
            title=f"Instagram Story by {username}",
            description=f"Story from @{username}",
            duration=None,
            uploader=username,
            uploader_id=username,
            uploader_url=f"https://instagram.com/{username}",
            upload_date=None,
            view_count=None,
            like_count=None,
            comment_count=None,
            thumbnail=None,
            webpage_url=url,
            formats=[],
            platform="instagram",
            platform_id=story_id,
            extra_info={
                'content_type': 'story',
                'requires_auth': True
            }
        )
        
        logger.warning("⚠️ Instagram stories typically require authentication")
        return video_info
        
    @trace_operation("instagram_download")
    async def download_video(self, 
                           video_info: VideoInfo, 
                           output_path: str,
                           quality: Optional[str] = None,
                           format_preference: Optional[str] = None) -> str:
        """Descarcă video de pe Instagram"""
        
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
                    
            logger.info(f"✅ Downloaded Instagram video: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Error downloading file: {e}")
            if monitoring:
                monitoring.record_error("instagram", "file_download", str(e))
            raise
            
    async def get_playlist_info(self, url: str) -> List[VideoInfo]:
        """Obține info pentru mai multe videoclipuri (profile)"""
        
        parsed = self._parse_url(url)
        
        if parsed['type'] != 'profile':
            # Pentru post singular
            info = await self.get_video_info(url)
            return [info]
            
        # Pentru profile, necesită implementare complexă
        username = parsed['username']
        
        logger.warning(f"⚠️ Profile playlist extraction for @{username} not fully implemented")
        logger.warning("💡 Please provide specific post URLs instead")
        
        return []
        
    def _select_best_format(self, 
                          formats: List[Dict[str, Any]], 
                          quality: Optional[str] = None,
                          format_preference: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Selectează cel mai bun format pentru descărcare"""
        
        if not formats:
            return None
            
        # Pentru Instagram, de obicei avem un singur format
        if len(formats) == 1:
            return formats[0]
            
        # Sortează după calitate (height)
        sorted_formats = sorted(
            formats,
            key=lambda f: f.get('height', 0),
            reverse=True  # Începe cu cea mai înaltă rezoluție
        )
        
        # Dacă nu e specificată calitatea, ia cea mai bună
        if not quality or quality == 'best':
            return sorted_formats[0]
            
        # Pentru calități specifice
        if quality == 'worst':
            return sorted_formats[-1]
            
        # Pentru alte cerințe de calitate
        return sorted_formats[0]  # Default la cea mai bună

# Export pentru registry
__all__ = ['InstagramPlatform']
