# platforms/youtube.py - YouTube Platform cu PO Token Support și Anti-detection
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

class YouTubePlatform(BasePlatform):
    """
    YouTube platform cu gestionare avansată PO Token și anti-detection mechanisms
    
    Caracteristici:
    - Client rotation avânsat (mweb, tv_embedded, web_safari, android_vr)
    - PO Token detection și handling automat
    - Anti-detection cu User-Agent rotation
    - Fallback pe multiple strategii
    - Optimizat pentru Free Tier hosting
    """
    
    def __init__(self):
        super().__init__('youtube')
        
        # Domenii suportate
        self.supported_domains = [
            'youtube.com', 'www.youtube.com', 'm.youtube.com',
            'youtu.be', 'music.youtube.com'
        ]
        
        # Client rotation - ordonate după prioritate și eficiență
        self.client_types = ['mweb', 'tv_embedded', 'web_safari', 'android_vr', 'mediaconnect']
        self.current_client_index = 0
        
        # User agents reali pentru anti-detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'
        ]
        
        logger.info(f"🎬 YouTube platform initialized with {len(self.client_types)} client types")
        
    async def is_supported_url(self, url: str) -> bool:
        """Verifică dacă URL-ul este de YouTube"""
        if not url or not isinstance(url, str):
            return False
            
        return any(domain in url.lower() for domain in self.supported_domains)
        
    async def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extrage metadata YouTube fără descărcare
        
        Folosește client rotation pentru a evita blocarea
        """
        logger.info(f"🔍 Extracting YouTube metadata for: {url[:50]}...")
        
        for client_type in self.client_types:
            try:
                opts = self._get_client_options(client_type)
                opts['skip_download'] = True
                opts['quiet'] = True
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                    
                if info:
                    metadata = self._clean_metadata(info)
                    logger.info(f"✅ Metadata extracted with {client_type}: {metadata.get('title', 'Unknown')[:50]}")
                    return metadata
                    
            except Exception as e:
                logger.warning(f"⚠️ Metadata extraction failed with {client_type}: {e}")
                continue
                
        raise Exception("Failed to extract metadata with all client types")
        
    async def download_video(self, url: str, output_path: str) -> DownloadResult:
        """
        Descarcă videoclip YouTube cu client rotation și PO Token handling
        """
        logger.info(f"🎬 Starting YouTube download: {url[:50]}...")
        
        # Încearcă cu fiecare tip de client
        for i, client_type in enumerate(self.client_types):
            try:
                logger.info(f"🔄 Attempting YouTube download with {client_type} ({i+1}/{len(self.client_types)})")
                
                result = await self._download_with_client(url, output_path, client_type)
                if result.success:
                    logger.info(f"✅ YouTube download successful with {client_type}")
                    return result
                else:
                    logger.warning(f"⚠️ {client_type} failed: {result.error}")
                    
            except Exception as e:
                logger.error(f"❌ {client_type} exception: {e}")
                continue
                
        # Toate client types au eșuat
        return DownloadResult(
            success=False,
            error="All YouTube client types failed. Video may be restricted or require authentication.",
            platform=self.name
        )
        
    async def _download_with_client(self, url: str, output_path: str, client_type: str) -> DownloadResult:
        """Descarcă cu un tip specific de client"""
        
        try:
            # Configurează opțiunile pentru acest client
            opts = self._get_client_options(client_type)
            opts['outtmpl'] = output_path
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Extrage info mai întâi pentru verificări
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                # Verifică dacă necesită PO Token
                if self._requires_po_token(info):
                    logger.warning(f"🔐 PO Token required for {client_type}, trying alternative approach")
                    return await self._handle_po_token_requirement(url, output_path, client_type)
                
                # Validează constrângerile
                metadata = self._clean_metadata(info)
                validation = await self.validate_constraints(metadata)
                
                if not validation['valid']:
                    return DownloadResult(
                        success=False,
                        error=validation['error'],
                        platform=self.name
                    )
                
                # Descarcă videoclipul
                await asyncio.to_thread(ydl.download, [url])
                
                # Verifică că fișierul a fost creat
                if output_path and os.path.exists(output_path):
                    return DownloadResult(
                        success=True,
                        file_path=output_path,
                        metadata=metadata,
                        platform=self.name
                    )
                else:
                    return DownloadResult(
                        success=False,
                        error="Download completed but file not found",
                        platform=self.name
                    )
                    
        except yt_dlp.DownloadError as e:
            return self._handle_download_error(str(e), client_type)
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"Unexpected error with {client_type}: {str(e)}",
                platform=self.name
            )
            
    def _get_client_options(self, client_type: str) -> Dict[str, Any]:
        """Generează opțiuni yt-dlp pentru tipul de client specificat"""
        
        # Headers comune pentru toate client types
        headers = self._get_rotating_headers()
        
        # Configurație de bază optimizată pentru Free Tier
        base_opts = {
            'http_headers': headers,
            'nocheckcertificate': False,
            'prefer_insecure': False,
            'cachedir': False,  # Dezactivează cache pentru a evita probleme
            'no_warnings': False,  # Activăm warnings pentru debugging
            'extract_flat': False,
            'ignoreerrors': False,
            'geo_bypass': True,
            'socket_timeout': 30,  # Redus pentru Free Tier
            'retries': 2,  # Redus pentru Free Tier
            'fragment_retries': 2,
            'format': 'best[height<=720]/best[filesize<=512M]/best',  # Optimizat pentru Free Tier
            'writeinfojson': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        # Configurații specifice pentru fiecare client
        client_configs = {
            'mweb': {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['mweb'],
                        'player_skip': ['webpage'],  # Skip pentru rapiditate
                        'innertube_host': 'm.youtube.com',
                    }
                }
            },
            'tv_embedded': {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv_embedded'],
                        'player_skip': ['webpage', 'configs'],
                    }
                }
            },
            'web_safari': {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web_safari'],
                        'player_skip': ['webpage'],
                    }
                }
            },
            'android_vr': {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_vr'],
                        'player_skip': ['webpage', 'configs'],
                    }
                }
            },
            'mediaconnect': {
                'extractor_args': {
                    'youtube': {
                        'player_client': ['mediaconnect'],
                        'player_skip': ['webpage', 'configs'],
                    }
                }
            }
        }
        
        # Merge configurația de bază cu cea specifică client-ului
        final_opts = {**base_opts, **client_configs.get(client_type, {})}
        
        return final_opts
        
    def _get_rotating_headers(self) -> Dict[str, str]:
        """Generează headers HTTP reali cu rotație pentru anti-detection"""
        user_agent = random.choice(self.user_agents)
        
        base_headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en-US,en;q=0.9,ro;q=0.8']),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # Adaugă headers specifice pentru Chrome
        if 'Chrome' in user_agent and 'Edg' not in user_agent:
            base_headers.update({
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"',
                'sec-ch-ua-mobile': '?0' if 'Mobile' not in user_agent else '?1',
                'sec-ch-ua-platform': self._detect_platform_from_ua(user_agent),
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            })
            
        return base_headers
        
    def _detect_platform_from_ua(self, user_agent: str) -> str:
        """Detectează platforma din User-Agent pentru sec-ch-ua-platform"""
        if 'Windows' in user_agent:
            return '"Windows"'
        elif 'Mac' in user_agent:
            return '"macOS"'
        elif 'Linux' in user_agent:
            return '"Linux"'
        elif 'Android' in user_agent:
            return '"Android"'
        else:
            return '"Unknown"'
            
    def _requires_po_token(self, info: Dict[str, Any]) -> bool:
        """
        Detectează dacă videoclipul necesită PO Token
        
        Indicii că se necesită PO Token:
        - Erori specifice în info
        - Lipsă formate de calitate
        - Mesaje de eroare specifice
        """
        if not info:
            return False
            
        # Verifică erori în info
        if 'error' in info:
            error_msg = str(info['error']).lower()
            po_token_indicators = [
                'sign in to confirm',
                'po_token',
                'proof of origin',
                'player response is empty',
                'unable to extract'
            ]
            
            if any(indicator in error_msg for indicator in po_token_indicators):
                return True
                
        # Verifică disponibilitatea formatelor
        formats = info.get('formats', [])
        if not formats:
            logger.warning("No formats available, might require PO Token")
            return True
            
        return False
        
    async def _handle_po_token_requirement(self, url: str, output_path: str, client_type: str) -> DownloadResult:
        """
        Gestionează cerințele PO Token cu strategii alternative
        
        Strategii:
        1. Încearcă cu client types care nu necesită PO Token
        2. Folosește extractoare alternative
        3. Returnează eroare explicativă dacă toate eșuează
        """
        logger.warning(f"🔐 Handling PO Token requirement for {client_type}")
        
        # Lista client types care nu necesită PO Token (în ordine)
        no_po_token_clients = ['mweb', 'tv_embedded', 'android_vr']
        
        for alt_client in no_po_token_clients:
            if alt_client != client_type:  # Evită să încerce din nou același client
                try:
                    logger.info(f"🔄 Trying alternative client {alt_client} to avoid PO Token")
                    
                    result = await self._download_with_client(url, output_path, alt_client)
                    if result.success:
                        logger.info(f"✅ Successfully bypassed PO Token with {alt_client}")
                        return result
                        
                except Exception as e:
                    logger.warning(f"⚠️ Alternative client {alt_client} also failed: {e}")
                    continue
                    
        # Toate strategiile au eșuat
        return DownloadResult(
            success=False,
            error="🔐 Video requires authentication (PO Token). This video may be age-restricted or require sign-in. Try a different video or check if it's publicly accessible.",
            platform=self.name
        )
        
    def _handle_download_error(self, error_msg: str, client_type: str) -> DownloadResult:
        """Gestionează erorile de descărcare cu mesaje user-friendly"""
        error_lower = error_msg.lower()
        
        if 'private' in error_lower or 'unavailable' in error_lower:
            return DownloadResult(
                success=False,
                error="🔒 Video is private or unavailable",
                platform=self.name
            )
        elif 'age' in error_lower and 'restrict' in error_lower:
            return DownloadResult(
                success=False,
                error="🔞 Video is age-restricted and requires authentication",
                platform=self.name
            )
        elif 'geo' in error_lower or 'region' in error_lower:
            return DownloadResult(
                success=False,
                error="🌍 Video not available in your region",
                platform=self.name
            )
        elif 'copyright' in error_lower:
            return DownloadResult(
                success=False,
                error="©️ Video blocked due to copyright restrictions",
                platform=self.name
            )
        else:
            return DownloadResult(
                success=False,
                error=f"❌ YouTube download failed with {client_type}: {error_msg[:100]}",
                platform=self.name
            )

# Singleton instance pentru YouTube platform
youtube_platform = YouTubePlatform()
