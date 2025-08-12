# platforms/youtube_new.py - YouTube Platform cu PO Token Support
# Versiunea: 3.0.0 - Arhitectura Nouă

import asyncio
import logging
import random
import time
import json
from typing import Dict, List, Optional, Any, Tuple
import yt_dlp

from platforms.base import BasePlatform, VideoInfo, PlatformCapability
from utils.cache import cache, generate_cache_key
from utils.monitoring import monitoring, trace_operation

logger = logging.getLogger(__name__)

class YouTubePlatform(BasePlatform):
    """
    YouTube platform cu gestionare avansată PO Token și anti-detection
    Suportă multiple client types și fallback mechanisms
    """
    
    def __init__(self):
        super().__init__()
        self.platform_name = "youtube"
        
        # Capabilities
        self.capabilities = {
            PlatformCapability.DOWNLOAD_VIDEO,
            PlatformCapability.DOWNLOAD_AUDIO,
            PlatformCapability.GET_METADATA,
            PlatformCapability.GET_THUMBNAIL,
            PlatformCapability.CUSTOM_QUALITY,
            PlatformCapability.PLAYLIST_SUPPORT
        }
        
        # Client configurations optimizate pentru 2024-2025
        self.client_configs = {
            'mweb': {
                'player_client': 'mweb',
                'description': 'Mobile web client - recomandat pentru evitarea PO Token',
                'requires_po_token': False,
                'supports_hls': True,
                'priority': 1
            },
            'tv_embedded': {
                'player_client': 'tv_embedded',
                'description': 'TV embedded client - nu necesită PO Token',
                'requires_po_token': False,
                'supports_hls': True,
                'priority': 2
            },
            'web_safari': {
                'player_client': 'web_safari',
                'description': 'Safari web client - oferă HLS fără PO Token',
                'requires_po_token': False,
                'supports_hls': True,
                'priority': 3
            },
            'android_vr': {
                'player_client': 'android_vr',
                'description': 'Android VR client - nu necesită PO Token',
                'requires_po_token': False,
                'supports_hls': False,
                'priority': 4
            },
            'mediaconnect': {
                'player_client': 'mediaconnect',
                'description': 'Media Connect client - pentru cazuri speciale',
                'requires_po_token': False,
                'supports_hls': False,
                'priority': 5
            }
        }
        
        # User Agents reali pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        self.current_ua_index = 0
        
        logger.info("📺 YouTube Platform initialized with advanced PO Token handling")
        
    def supports_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este YouTube"""
        youtube_domains = [
            'youtube.com', 'youtu.be', 'm.youtube.com', 
            'www.youtube.com', 'youtube-nocookie.com'
        ]
        return any(domain in url.lower() for domain in youtube_domains)
        
    def _get_next_user_agent(self) -> str:
        """Obține următorul user agent din rotație"""
        ua = self.user_agents[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return ua
        
    def _get_random_headers(self) -> Dict[str, str]:
        """Generează headers HTTP reali pentru anti-detection"""
        user_agent = self._get_next_user_agent()
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-US,en;q=0.8,es;q=0.6']),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        # Adaugă headers specifice pentru Chrome
        if 'Chrome' in user_agent and 'Edg' not in user_agent:
            headers.update({
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"' if 'Windows' in user_agent else ('"macOS"' if 'Mac' in user_agent else '"Linux"'),
            })
            
        return headers
        
    def _get_client_options(self, client_type: str = 'mweb') -> Dict[str, Any]:
        """Obține opțiunile pentru un tip de client specific"""
        client_config = self.client_configs.get(client_type, self.client_configs['mweb'])
        
        extractor_args = {
            'youtube': {
                'player_client': [client_config['player_client']],
                'player_skip': ['webpage', 'configs'] if not client_config.get('requires_po_token') else [],
                'skip': [] if client_config.get('supports_hls') else ['hls'],
                'innertube_host': 'www.youtube.com',
                'innertube_key': None,
                'comment_sort': 'top',
                'max_comments': [0],
            }
        }
        
        # Configurări specifice pentru client mweb
        if client_type == 'mweb':
            extractor_args['youtube'].update({
                'player_client': ['mweb'],
                'player_skip': ['webpage'],
                'innertube_host': 'm.youtube.com',
            })
            
        return {
            'format': 'best[filesize<50M][height<=720]/best[height<=720]/best[filesize<50M]/best',
            'http_headers': self._get_random_headers(),
            'extractor_args': extractor_args,
            'nocheckcertificate': False,
            'prefer_insecure': False,
            'cachedir': False,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'geo_bypass': True,
            'geo_bypass_country': random.choice(['US', 'GB', 'CA', 'AU']),
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'socket_timeout': 30,
            'retries': 1,
            'extractor_retries': 1,
            'fragment_retries': 2,
            'retry_sleep_functions': {
                'http': lambda n: min(2 + n, 10),
                'fragment': lambda n: min(2 + n, 10)
            },
            'extract_comments': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'embed_subs': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'writedescription': False,
            'writeannotations': False,
            'no_color': True,
            'no_check_certificate': False,
            'prefer_free_formats': True,
            'youtube_include_dash_manifest': False,
        }
        
    def _is_po_token_required_error(self, error_msg: str) -> bool:
        """Verifică dacă eroarea necesită PO Token"""
        po_token_indicators = [
            'Sign in to confirm you\'re not a bot',
            'confirm you\'re not a bot',
            'Playback on other websites has been disabled',
            'Video unavailable',
            'Private video',
            'This video is not available',
            'age-gate',
            'Sign in to confirm your age',
        ]
        
        error_lower = error_msg.lower()
        return any(indicator.lower() in error_lower for indicator in po_token_indicators)
        
    def _is_bot_detection_error(self, error_msg: str) -> bool:
        """Verifică dacă este o eroare de detecție bot"""
        bot_detection_indicators = [
            'HTTP Error 403',
            'HTTP Error 429',
            'Sign in to confirm',
            'bot',
            'automated',
            'unusual activity',
            'rate limit',
            'throttled'
        ]
        
        error_lower = error_msg.lower()
        return any(indicator.lower() in error_lower for indicator in bot_detection_indicators)
        
    @trace_operation("youtube.get_video_info")
    async def get_video_info(self, url: str) -> VideoInfo:
        """Obține informații despre video YouTube cu fallback pe multiple clienți"""
        
        # Check cache
        cache_key = generate_cache_key("youtube_info", url)
        cached_info = await cache.get(cache_key)
        if cached_info:
            return cached_info
            
        # Sortează clienții după prioritate
        sorted_clients = sorted(
            self.client_configs.items(),
            key=lambda x: x[1]['priority']
        )
        
        last_error = None
        
        for client_name, client_config in sorted_clients:
            try:
                logger.info(f"🔄 Trying YouTube extraction with {client_name} client")
                
                # Obține opțiunile pentru client
                ydl_opts = self._get_client_options(client_name)
                ydl_opts['skip_download'] = True
                
                # Extrage informațiile
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                    
                    if not info:
                        continue
                        
                # Parsează informațiile în VideoInfo
                video_info = self._parse_youtube_info(info, url)
                
                # Cache results pentru 30 minute
                await cache.set(cache_key, video_info, ttl=1800)
                
                logger.info(f"✅ YouTube extraction successful with {client_name}")
                
                if monitoring:
                    monitoring.record_metric("youtube.extraction_success", 1)
                    monitoring.record_metric(f"youtube.client_{client_name}_success", 1)
                    
                return video_info
                
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                logger.warning(f"❌ YouTube extraction failed with {client_name}: {error_msg[:100]}...")
                
                # Verifică tipul de eroare
                if self._is_po_token_required_error(error_msg):
                    logger.info(f"🔒 PO Token required for {client_name}, trying next client")
                    continue
                elif self._is_bot_detection_error(error_msg):
                    logger.info(f"🤖 Bot detection for {client_name}, trying next client")
                    # Adaugă delay pentru anti-detection
                    await asyncio.sleep(random.uniform(1, 3))
                    continue
                else:
                    # Pentru alte erori, încearcă următorul client
                    logger.info(f"⚠️ General error for {client_name}, trying next client")
                    continue
                    
        # Dacă toate metodele au eșuat
        if monitoring:
            monitoring.record_error("youtube", "extraction_failed", last_error or "All clients failed")
            
        raise Exception(f"YouTube extraction failed with all clients. Last error: {last_error}")
        
    def _parse_youtube_info(self, info: Dict[str, Any], url: str) -> VideoInfo:
        """Parsează informațiile YouTube în VideoInfo"""
        try:
            video_id = info.get('id', 'unknown')
            title = info.get('title', 'YouTube Video')
            description = info.get('description', '')
            uploader = info.get('uploader', info.get('channel', ''))
            uploader_id = info.get('uploader_id', info.get('channel_id', ''))
            duration = info.get('duration', 0)
            view_count = info.get('view_count', 0)
            like_count = info.get('like_count', 0)
            upload_date = info.get('upload_date', '')
            thumbnail = info.get('thumbnail', '')
            
            # Parsează formatele disponibile
            formats = []
            if 'formats' in info and info['formats']:
                for fmt in info['formats']:
                    format_info = {
                        'format_id': fmt.get('format_id', ''),
                        'ext': fmt.get('ext', 'mp4'),
                        'quality': fmt.get('format_note', 'unknown'),
                        'url': fmt.get('url', ''),
                        'filesize': fmt.get('filesize'),
                        'width': fmt.get('width'),
                        'height': fmt.get('height'),
                        'fps': fmt.get('fps'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec'),
                        'preference': self._calculate_format_preference(fmt)
                    }
                    formats.append(format_info)
                    
            # Sortează formatele după preferință
            formats.sort(key=lambda x: x.get('preference', 0), reverse=True)
            
            # Construiește VideoInfo
            video_info = VideoInfo(
                id=video_id,
                title=title,
                description=description[:500] + "..." if len(description) > 500 else description,
                duration=duration,
                uploader=uploader,
                uploader_id=uploader_id,
                uploader_url=f"https://youtube.com/channel/{uploader_id}" if uploader_id else None,
                upload_date=upload_date,
                view_count=view_count,
                like_count=like_count,
                thumbnail=thumbnail,
                webpage_url=url,
                formats=formats,
                platform="youtube",
                platform_id=video_id,
                extra_info={
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', []),
                    'age_limit': info.get('age_limit', 0),
                    'availability': info.get('availability', 'public'),
                    'live_status': info.get('live_status', 'not_live'),
                    'channel_follower_count': info.get('channel_follower_count'),
                    'comment_count': info.get('comment_count'),
                }
            )
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error parsing YouTube info: {e}")
            raise
            
    def _calculate_format_preference(self, fmt: Dict[str, Any]) -> int:
        """Calculează preferința pentru un format"""
        preference = 0
        
        # Preferință pentru calitate video
        height = fmt.get('height', 0)
        if height:
            if height <= 480:
                preference += 10
            elif height <= 720:
                preference += 20  # Preferința pentru 720p
            elif height <= 1080:
                preference += 15
            else:
                preference += 5
                
        # Preferință pentru codec
        vcodec = fmt.get('vcodec', '').lower()
        if 'h264' in vcodec:
            preference += 10
        elif 'vp9' in vcodec:
            preference += 8
        elif 'av01' in vcodec:
            preference += 5
            
        # Preferință pentru audio
        acodec = fmt.get('acodec', '').lower()
        if 'aac' in acodec:
            preference += 5
        elif 'mp3' in acodec:
            preference += 3
            
        # Preferință pentru container
        ext = fmt.get('ext', '').lower()
        if ext == 'mp4':
            preference += 15
        elif ext == 'webm':
            preference += 10
        elif ext == 'mkv':
            preference += 8
            
        return preference
        
    @trace_operation("youtube.download_video")
    async def download_video(self, video_info: VideoInfo, output_path: str, 
                           quality: Optional[str] = None) -> str:
        """Descarcă video YouTube cu retry pe multiple clienți"""
        
        if not video_info.formats:
            raise ValueError("No downloadable formats found")
            
        # Selectează formatele potrivite
        selected_formats = self._select_best_formats(video_info.formats, quality)
        
        # Sortează clienții după prioritate
        sorted_clients = sorted(
            self.client_configs.items(),
            key=lambda x: x[1]['priority']
        )
        
        last_error = None
        
        for client_name, client_config in sorted_clients:
            try:
                logger.info(f"🔄 Trying YouTube download with {client_name} client")
                
                # Obține opțiunile pentru client
                ydl_opts = self._get_client_options(client_name)
                ydl_opts['outtmpl'] = output_path
                
                # Configurează formatul pentru descărcare
                if selected_formats:
                    format_string = '+'.join([f['format_id'] for f in selected_formats[:2]])  # Video + Audio
                    ydl_opts['format'] = format_string
                    
                # Descarcă video-ul
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    await asyncio.to_thread(ydl.download, [video_info.webpage_url])
                    
                # Verifică dacă fișierul există
                import glob
                import os
                
                output_dir = os.path.dirname(output_path)
                possible_files = glob.glob(os.path.join(output_dir, "*"))
                
                if possible_files:
                    downloaded_file = max(possible_files, key=os.path.getctime)
                    logger.info(f"✅ YouTube download successful with {client_name}: {downloaded_file}")
                    
                    if monitoring:
                        monitoring.record_metric("youtube.download_success", 1)
                        monitoring.record_metric(f"youtube.client_{client_name}_download_success", 1)
                        
                    return downloaded_file
                else:
                    raise FileNotFoundError("Downloaded file not found")
                    
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                logger.warning(f"❌ YouTube download failed with {client_name}: {error_msg[:100]}...")
                
                if self._is_po_token_required_error(error_msg):
                    logger.info(f"🔒 PO Token required for {client_name}, trying next client")
                    continue
                elif self._is_bot_detection_error(error_msg):
                    logger.info(f"🤖 Bot detection for {client_name}, trying next client")
                    await asyncio.sleep(random.uniform(2, 5))
                    continue
                else:
                    continue
                    
        # Toate metodele au eșuat
        if monitoring:
            monitoring.record_error("youtube", "download_failed", last_error or "All clients failed")
            
        raise Exception(f"YouTube download failed with all clients. Last error: {last_error}")
        
    def _select_best_formats(self, formats: List[Dict[str, Any]], 
                           quality: Optional[str] = None) -> List[Dict[str, Any]]:
        """Selectează cele mai bune formate pentru descărcare"""
        
        if not formats:
            return []
            
        # Filtrează formatele după calitate dacă este specificată
        if quality:
            if quality == "720p":
                filtered_formats = [f for f in formats if f.get('height', 0) <= 720]
            elif quality == "480p":
                filtered_formats = [f for f in formats if f.get('height', 0) <= 480]
            elif quality == "360p":
                filtered_formats = [f for f in formats if f.get('height', 0) <= 360]
            else:
                filtered_formats = formats
        else:
            # Pentru Free Tier, limitează la 720p
            filtered_formats = [f for f in formats if f.get('height', 0) <= 720]
            
        if not filtered_formats:
            filtered_formats = formats[:5]  # Fallback la primele 5
            
        # Sortează și returnează primele 3 formate
        sorted_formats = sorted(filtered_formats, key=lambda x: x.get('preference', 0), reverse=True)
        return sorted_formats[:3]
        
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statisticile platformei YouTube"""
        return {
            'platform': 'youtube',
            'available_clients': len(self.client_configs),
            'client_configs': {name: config['description'] for name, config in self.client_configs.items()},
            'capabilities': [cap.value for cap in self.capabilities],
            'user_agents_count': len(self.user_agents),
            'status': 'active'
        }
        
    async def cleanup(self):
        """Curăță resursele YouTube"""
        logger.info("🧹 Cleaning up YouTube platform resources...")
        # Nu sunt resurse specifice de curățat pentru YouTube
        logger.info("✅ YouTube platform cleanup complete")
        
    def is_healthy(self) -> bool:
        """Verifică starea platformei"""
        return len(self.client_configs) > 0 and len(self.user_agents) > 0
