#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilități comune pentru header-urile HTTP și configurările de rețea
"""

import random
from typing import Dict, List, Any

class HTTPHeaders:
    """Gestionează header-urile HTTP comune pentru toate platformele"""
    
    @staticmethod
    def get_standard_browser_headers() -> Dict[str, str]:
        """Returnează header-urile standard de browser"""
        return {
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
    
    @staticmethod
    def get_user_agents() -> List[str]:
        """Returnează o listă de user agents pentru rotație"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
    
    @staticmethod
    def get_random_user_agent() -> str:
        """Returnează un user agent aleatoriu"""
        return random.choice(HTTPHeaders.get_user_agents())
    
    @staticmethod
    def get_platform_headers(platform: str = 'generic', include_user_agent: bool = True) -> Dict[str, str]:
        """Returnează header-urile optimizate pentru o platformă specifică"""
        headers = HTTPHeaders.get_standard_browser_headers().copy()
        
        if include_user_agent:
            headers['User-Agent'] = HTTPHeaders.get_random_user_agent()
        
        # Header-uri specifice platformei
        platform_specific = {
            'youtube': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            },
            'tiktok': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            },
            'facebook': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        if platform.lower() in platform_specific:
            headers.update(platform_specific[platform.lower()])
        
        return headers

class YDLConfig:
    """Configurații comune pentru yt-dlp"""
    
    @staticmethod
    def get_base_ydl_opts() -> Dict[str, Any]:
        """Returnează opțiunile de bază pentru yt-dlp"""
        return {
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 30,
            'fragment_retries': 3,
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            'buffersize': 16384,
            'http_headers': HTTPHeaders.get_platform_headers()
        }
    
    @staticmethod
    def get_platform_ydl_opts(platform: str) -> Dict[str, Any]:
        """Returnează opțiunile yt-dlp optimizate pentru o platformă specifică"""
        base_opts = YDLConfig.get_base_ydl_opts()
        base_opts['http_headers'] = HTTPHeaders.get_platform_headers(platform)
        
        # Configurații specifice platformei
        platform_configs = {
            'youtube': {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'skip': ['hls', 'dash']
                    }
                }
            },
            'tiktok': {
                'http_chunk_size': 5242880,  # 5MB chunks pentru TikTok
                'retries': 5,
            },
            'facebook': {
                'socket_timeout': 45,
                'retries': 5,
            }
        }
        
        if platform.lower() in platform_configs:
            base_opts.update(platform_configs[platform.lower()])
        
        return base_opts

class NetworkUtils:
    """Utilități comune pentru operațiuni de rețea"""
    
    @staticmethod
    def get_session_config() -> Dict[str, Any]:
        """Returnează configurația pentru sesiunile requests"""
        return {
            'timeout': (10, 30),  # (connect_timeout, read_timeout)
            'allow_redirects': True,
            'verify': True,
            'stream': False
        }
    
    @staticmethod
    def get_retry_config() -> Dict[str, Any]:
        """Returnează configurația pentru retry logic"""
        return {
            'max_retries': 3,
            'backoff_factor': 1.0,
            'status_forcelist': [429, 500, 502, 503, 504],
            'allowed_methods': ['GET', 'POST']
        }