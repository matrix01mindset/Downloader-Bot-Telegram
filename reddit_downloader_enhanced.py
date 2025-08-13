#!/usr/bin/env python3
"""
Enhanced Reddit Video Downloader
Implements improvements based on testing and analysis
"""

import requests
import os
import tempfile
import time
import json
import random
import logging
from urllib.parse import urlparse, parse_qs
import re
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedditDownloaderEnhanced:
    """Enhanced Reddit video downloader with improved strategies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.failed_proxies = set()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0'
        ]
        
        # Quality preferences (highest to lowest)
        self.quality_preferences = ['DASH_1080', 'DASH_720', 'DASH_480', 'DASH_360', 'DASH_240']
        
    def get_random_headers(self) -> Dict[str, str]:
        """Generate random headers for anti-detection"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    def normalize_reddit_url(self, url: str) -> str:
        """Normalize Reddit URL for consistent processing"""
        # Remove tracking parameters
        url = re.sub(r'[?&]utm_[^&]*', '', url)
        url = re.sub(r'[?&]ref_[^&]*', '', url)
        
        # Convert to www.reddit.com format
        url = url.replace('old.reddit.com', 'www.reddit.com')
        url = url.replace('m.reddit.com', 'www.reddit.com')
        url = url.replace('np.reddit.com', 'www.reddit.com')
        
        # Handle short URLs
        if 'redd.it/' in url:
            post_id = url.split('redd.it/')[-1].split('?')[0].split('#')[0]
            url = f'https://www.reddit.com/comments/{post_id}/'
        
        # Ensure trailing slash for consistency
        if '/comments/' in url and not url.endswith('/'):
            url += '/'
            
        return url
    
    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract Reddit post ID from URL"""
        patterns = [
            r'/comments/([a-zA-Z0-9]+)/',
            r'redd\.it/([a-zA-Z0-9]+)',
            r'/([a-zA-Z0-9]+)/?$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_extraction_strategies(self, url: str) -> List[Dict]:
        """Get list of extraction strategies to try"""
        strategies = [
            {
                'name': 'Reddit JSON Direct',
                'url_transform': lambda u: u.rstrip('/') + '.json',
                'headers': {
                    **self.get_random_headers(),
                    'Accept': 'application/json, text/plain, */*'
                }
            },
            {
                'name': 'Old Reddit JSON',
                'url_transform': lambda u: u.replace('www.reddit.com', 'old.reddit.com').rstrip('/') + '.json',
                'headers': {
                    **self.get_random_headers(),
                    'Accept': 'application/json, text/plain, */*'
                }
            },
            {
                'name': 'Mobile Reddit JSON',
                'url_transform': lambda u: u.replace('www.reddit.com', 'm.reddit.com').rstrip('/') + '.json',
                'headers': {
                    **self.get_random_headers(),
                    'Accept': 'application/json, text/plain, */*'
                }
            },
            {
                'name': 'Reddit API v1',
                'url_transform': lambda u: f"https://www.reddit.com/api/info.json?url={u}",
                'headers': {
                    **self.get_random_headers(),
                    'Accept': 'application/json'
                }
            }
        ]
        
        return strategies
    
    def extract_video_urls_from_json(self, data: Dict) -> List[Dict[str, str]]:
        """Extract video URLs with quality information from Reddit JSON"""
        video_urls = []
        
        try:
            # Handle different JSON structures
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            # Navigate to post data
            posts = []
            if 'data' in data and 'children' in data['data']:
                posts = data['data']['children']
            elif 'data' in data and 'things' in data['data']:
                posts = data['data']['things']
            
            for post in posts:
                post_data = post.get('data', {})
                
                # Check secure_media for reddit_video
                if 'secure_media' in post_data and post_data['secure_media']:
                    reddit_video = post_data['secure_media'].get('reddit_video', {})
                    if reddit_video:
                        self._extract_from_reddit_video(reddit_video, video_urls)
                
                # Check media for reddit_video
                if 'media' in post_data and post_data['media']:
                    reddit_video = post_data['media'].get('reddit_video', {})
                    if reddit_video:
                        self._extract_from_reddit_video(reddit_video, video_urls)
                
                # Check preview for reddit_video_preview
                if 'preview' in post_data and 'reddit_video_preview' in post_data['preview']:
                    reddit_video = post_data['preview']['reddit_video_preview']
                    self._extract_from_reddit_video(reddit_video, video_urls)
                
                # Check direct URL
                url = post_data.get('url', '')
                if url and ('v.redd.it' in url or '.mp4' in url):
                    quality = self._guess_quality_from_url(url)
                    video_urls.append({
                        'url': url,
                        'quality': quality,
                        'type': 'direct'
                    })
        
        except Exception as e:
            logger.warning(f"Error extracting video URLs from JSON: {e}")
        
        # Sort by quality preference
        return self._sort_by_quality(video_urls)
    
    def _extract_from_reddit_video(self, reddit_video: Dict, video_urls: List[Dict]):
        """Extract video URLs from reddit_video object"""
        # Get fallback URL
        if 'fallback_url' in reddit_video:
            quality = self._guess_quality_from_url(reddit_video['fallback_url'])
            video_urls.append({
                'url': reddit_video['fallback_url'],
                'quality': quality,
                'type': 'fallback',
                'duration': reddit_video.get('duration'),
                'width': reddit_video.get('width'),
                'height': reddit_video.get('height')
            })
        
        # Get HLS playlist URL
        if 'hls_url' in reddit_video:
            video_urls.append({
                'url': reddit_video['hls_url'],
                'quality': 'HLS',
                'type': 'hls',
                'duration': reddit_video.get('duration')
            })
        
        # Get DASH manifest URL
        if 'dash_url' in reddit_video:
            video_urls.append({
                'url': reddit_video['dash_url'],
                'quality': 'DASH',
                'type': 'dash',
                'duration': reddit_video.get('duration')
            })
    
    def _guess_quality_from_url(self, url: str) -> str:
        """Guess video quality from URL"""
        for quality in self.quality_preferences:
            if quality in url:
                return quality
        
        # Check for resolution indicators
        if '1080' in url:
            return 'DASH_1080'
        elif '720' in url:
            return 'DASH_720'
        elif '480' in url:
            return 'DASH_480'
        elif '360' in url:
            return 'DASH_360'
        elif '240' in url:
            return 'DASH_240'
        
        return 'unknown'
    
    def _sort_by_quality(self, video_urls: List[Dict]) -> List[Dict]:
        """Sort video URLs by quality preference"""
        def quality_score(video_info):
            quality = video_info['quality']
            if quality in self.quality_preferences:
                return self.quality_preferences.index(quality)
            return len(self.quality_preferences)  # Unknown quality goes last
        
        return sorted(video_urls, key=quality_score)
    
    def download_video(self, video_url: str, temp_dir: str, max_size_mb: int = 50) -> Dict:
        """Download video with size checking and progress tracking"""
        try:
            logger.info(f"⬇️ Downloading video from: {video_url}")
            
            # Headers for video download
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.reddit.com/',
                'Origin': 'https://www.reddit.com',
                'Range': 'bytes=0-'
            }
            
            # Make request with streaming
            response = self.session.get(
                video_url,
                headers=headers,
                stream=True,
                timeout=30,
                verify=False
            )
            
            if response.status_code not in [200, 206]:
                raise Exception(f"HTTP {response.status_code}: {response.reason}")
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > max_size_mb:
                    raise Exception(f"File too large: {size_mb:.2f}MB > {max_size_mb}MB")
                logger.info(f"📊 File size: {size_mb:.2f}MB")
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'mp4' in content_type:
                ext = '.mp4'
            elif 'webm' in content_type:
                ext = '.webm'
            else:
                ext = '.mp4'  # default
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"reddit_video_{timestamp}{ext}"
            file_path = os.path.join(temp_dir, filename)
            
            # Download with progress tracking
            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Check size limit during download
                        if downloaded_size > max_size_mb * 1024 * 1024:
                            f.close()
                            os.remove(file_path)
                            raise Exception(f"Download exceeded size limit: {max_size_mb}MB")
            
            final_size = os.path.getsize(file_path)
            logger.info(f"✅ Video downloaded successfully: {file_path} ({final_size} bytes)")
            
            return {
                'success': True,
                'file_path': file_path,
                'file_size': final_size,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return {
                'success': False,
                'error': f"Download failed: {str(e)}",
                'file_path': None
            }
    
    def extract_and_download(self, url: str, temp_dir: str) -> Dict:
        """Main method to extract and download Reddit video"""
        logger.info(f"🔍 Processing Reddit URL: {url}")
        
        # Normalize URL
        normalized_url = self.normalize_reddit_url(url)
        logger.info(f"📝 Normalized URL: {normalized_url}")
        
        # If it's already a direct video URL, download it
        if 'v.redd.it' in url or '.mp4' in url:
            logger.info("🎬 Direct video URL detected")
            return self.download_video(url, temp_dir)
        
        # Try extraction strategies
        strategies = self.get_extraction_strategies(normalized_url)
        errors = []
        
        for strategy in strategies:
            try:
                logger.info(f"📡 Trying {strategy['name']}")
                target_url = strategy['url_transform'](normalized_url)
                
                response = self.session.get(
                    target_url,
                    headers=strategy['headers'],
                    timeout=10,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        video_urls = self.extract_video_urls_from_json(data)
                        
                        if video_urls:
                            logger.info(f"🎬 Found {len(video_urls)} video URL(s)")
                            
                            # Try downloading the best quality video
                            for video_info in video_urls:
                                video_url = video_info['url']
                                quality = video_info['quality']
                                logger.info(f"🎯 Trying {quality}: {video_url}")
                                
                                result = self.download_video(video_url, temp_dir)
                                if result['success']:
                                    result['quality'] = quality
                                    result['strategy'] = strategy['name']
                                    return result
                                else:
                                    logger.warning(f"❌ Download failed for {quality}: {result['error']}")
                        else:
                            logger.warning(f"⚠️ No video URLs found in {strategy['name']} response")
                    
                    except json.JSONDecodeError as e:
                        error_msg = f"{strategy['name']}: JSON decode error - {str(e)}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                else:
                    error_msg = f"{strategy['name']}: HTTP {response.status_code}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    
            except Exception as e:
                error_msg = f"{strategy['name']}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        # All strategies failed
        logger.error(f"❌ All extraction strategies failed for {url}")
        return {
            'success': False,
            'error': f"All extraction strategies failed. Errors: {'; '.join(errors[:3])}",
            'file_path': None
        }

# Test function
def test_enhanced_downloader():
    """Test the enhanced Reddit downloader"""
    downloader = RedditDownloaderEnhanced()
    
    # Test with direct video URL
    test_url = 'https://v.redd.it/92567y9qsmif1/DASH_480.mp4?source=fallback'
    temp_dir = tempfile.mkdtemp()
    
    try:
        print(f"🧪 Testing enhanced Reddit downloader with: {test_url}")
        result = downloader.extract_and_download(test_url, temp_dir)
        
        if result['success']:
            print(f"✅ Success! Downloaded to: {result['file_path']}")
            print(f"📊 File size: {result['file_size']} bytes")
            if 'quality' in result:
                print(f"🎯 Quality: {result['quality']}")
            if 'strategy' in result:
                print(f"📡 Strategy: {result['strategy']}")
            
            # Cleanup
            os.remove(result['file_path'])
            print("🧹 Cleanup completed")
        else:
            print(f"❌ Failed: {result['error']}")
    
    finally:
        # Cleanup temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass

if __name__ == "__main__":
    test_enhanced_downloader()