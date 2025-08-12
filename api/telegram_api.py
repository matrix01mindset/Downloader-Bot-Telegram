# api/telegram_api.py - Telegram API Wrapper Optimizat
# Versiunea: 3.0.0 - Arhitectura Nouă

import aiohttp
import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, Union, BinaryIO
from dataclasses import dataclass

from utils.monitoring import monitoring, trace_operation
from utils.cache import cache, generate_cache_key

logger = logging.getLogger(__name__)

@dataclass
class TelegramAPIStats:
    """Statistici pentru API-ul Telegram"""
    requests_sent: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    average_response_time: float = 0
    rate_limit_hits: int = 0

class TelegramAPI:
    """
    Wrapper optimizat pentru API-ul Telegram Bot
    Oferă funcții de nivel înalt cu retry logic, rate limiting și cache
    """
    
    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("Bot token cannot be empty")
            
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Session HTTP persistent pentru conexiuni reutilizabile
        self.session = None
        
        # Statistici
        self.stats = TelegramAPIStats()
        
        # Rate limiting
        self.rate_limit_per_second = 30  # Limita Telegram: 30 req/sec
        self.last_request_times = []
        
        # Timeouts optimizate pentru Free Tier
        self.default_timeout = aiohttp.ClientTimeout(
            total=60,      # Total timeout pentru upload video
            connect=10,    # Connect timeout
            sock_read=30   # Socket read timeout
        )
        
        logger.info(f"✅ Telegram API initialized for bot: {bot_token[:10]}...")
        
    async def _ensure_session(self):
        """Asigură că session-ul HTTP este disponibil"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,           # Total connection pool size
                limit_per_host=30,   # Per-host connection pool size
                ttl_dns_cache=300,   # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.default_timeout,
                headers={
                    'User-Agent': 'TelegramBot/3.0.0'
                }
            )
            
    async def _check_rate_limit(self):
        """Verifică și respectă rate limiting-ul Telegram"""
        current_time = time.time()
        
        # Curăță request-urile vechi (> 1 secundă)
        self.last_request_times = [
            t for t in self.last_request_times 
            if current_time - t < 1.0
        ]
        
        # Verifică dacă am depășit limita
        if len(self.last_request_times) >= self.rate_limit_per_second:
            wait_time = 1.0 - (current_time - self.last_request_times[0])
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.stats.rate_limit_hits += 1
                
        # Adaugă request-ul curent
        self.last_request_times.append(current_time)
        
    @trace_operation("telegram_api.request")
    async def _make_request(self, method: str, endpoint: str, 
                          data: Optional[Dict[str, Any]] = None,
                          files: Optional[Dict[str, Any]] = None,
                          timeout: Optional[aiohttp.ClientTimeout] = None) -> Dict[str, Any]:
        """
        Face un request către API-ul Telegram cu gestionare optimizată a erorilor
        """
        start_time = time.time()
        
        try:
            await self._ensure_session()
            await self._check_rate_limit()
            
            url = f"{self.base_url}/{endpoint}"
            
            # Pregătește payload-ul
            if files:
                # Multipart pentru fișiere
                form_data = aiohttp.FormData()
                
                if data:
                    for key, value in data.items():
                        if value is not None:
                            form_data.add_field(key, str(value))
                            
                for key, file_data in files.items():
                    if isinstance(file_data, dict):
                        form_data.add_field(
                            key, 
                            file_data['file'], 
                            filename=file_data.get('filename', key)
                        )
                    else:
                        form_data.add_field(key, file_data)
                        
                payload = form_data
                
            elif data:
                # JSON pentru date simple
                payload = json.dumps(data)
                headers = {'Content-Type': 'application/json'}
                
            else:
                payload = None
                headers = {}
                
            # Face request-ul
            async with self.session.request(
                method=method,
                url=url,
                data=payload,
                headers=headers if not files else {},
                timeout=timeout or self.default_timeout
            ) as response:
                
                # Calculează statistici
                response_time = time.time() - start_time
                self._update_stats(response, response_time)
                
                # Citește răspunsul
                response_text = await response.text()
                
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    result = {'ok': False, 'description': f'Invalid JSON response: {response_text[:100]}'}
                    
                # Gestionează erorile Telegram
                if not result.get('ok', False):
                    error_code = result.get('error_code', response.status)
                    description = result.get('description', 'Unknown error')
                    
                    # Rate limiting detection
                    if error_code == 429:
                        retry_after = result.get('parameters', {}).get('retry_after', 1)
                        logger.warning(f"Telegram rate limit hit, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        self.stats.rate_limit_hits += 1
                        
                        # Retry once după rate limit
                        return await self._make_request(method, endpoint, data, files, timeout)
                        
                    # Alte erori
                    logger.error(f"Telegram API error {error_code}: {description}")
                    
                    if monitoring:
                        monitoring.record_error("telegram_api", f"error_{error_code}", description)
                        
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"Telegram API timeout for {endpoint}")
            if monitoring:
                monitoring.record_error("telegram_api", "timeout", endpoint)
            return {'ok': False, 'description': 'Request timeout'}
            
        except Exception as e:
            logger.error(f"Telegram API exception for {endpoint}: {e}")
            if monitoring:
                monitoring.record_error("telegram_api", "exception", str(e))
            return {'ok': False, 'description': f'Request failed: {str(e)}'}
            
    def _update_stats(self, response: aiohttp.ClientResponse, response_time: float):
        """Actualizează statisticile API"""
        self.stats.requests_sent += 1
        
        if 200 <= response.status < 300:
            self.stats.requests_successful += 1
        else:
            self.stats.requests_failed += 1
            
        # Actualizează timpul de răspuns mediu
        if self.stats.average_response_time == 0:
            self.stats.average_response_time = response_time
        else:
            self.stats.average_response_time = (
                0.9 * self.stats.average_response_time + 
                0.1 * response_time
            )
            
        if monitoring:
            monitoring.record_metric("telegram_api.response_time", response_time)
            monitoring.record_metric("telegram_api.requests", 1)
            
    # Metode API principale
    
    async def get_me(self) -> Dict[str, Any]:
        """Obține informații despre bot"""
        return await self._make_request('GET', 'getMe')
        
    async def send_message(self, chat_id: int, text: str, 
                          parse_mode: Optional[str] = None,
                          reply_markup: Optional[Dict[str, Any]] = None,
                          disable_web_page_preview: bool = True,
                          disable_notification: bool = False,
                          reply_to_message_id: Optional[int] = None) -> Dict[str, Any]:
        """Trimite un mesaj text"""
        
        data = {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': disable_web_page_preview,
            'disable_notification': disable_notification
        }
        
        if parse_mode:
            data['parse_mode'] = parse_mode
            
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
            
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
            
        return await self._make_request('POST', 'sendMessage', data)
        
    async def edit_message_text(self, chat_id: int, message_id: int, text: str,
                               parse_mode: Optional[str] = None,
                               reply_markup: Optional[Dict[str, Any]] = None,
                               disable_web_page_preview: bool = True) -> Dict[str, Any]:
        """Editează un mesaj text existent"""
        
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'disable_web_page_preview': disable_web_page_preview
        }
        
        if parse_mode:
            data['parse_mode'] = parse_mode
            
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
            
        return await self._make_request('POST', 'editMessageText', data)
        
    async def delete_message(self, chat_id: int, message_id: int) -> Dict[str, Any]:
        """Șterge un mesaj"""
        
        data = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        return await self._make_request('POST', 'deleteMessage', data)
        
    async def send_video(self, chat_id: int, video: Union[str, BinaryIO],
                        duration: Optional[int] = None,
                        width: Optional[int] = None,
                        height: Optional[int] = None,
                        thumbnail: Optional[BinaryIO] = None,
                        caption: Optional[str] = None,
                        parse_mode: Optional[str] = None,
                        supports_streaming: bool = True,
                        disable_notification: bool = False,
                        reply_to_message_id: Optional[int] = None,
                        reply_markup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trimite un video"""
        
        data = {
            'chat_id': chat_id,
            'supports_streaming': supports_streaming,
            'disable_notification': disable_notification
        }
        
        if duration:
            data['duration'] = duration
        if width:
            data['width'] = width  
        if height:
            data['height'] = height
        if caption:
            data['caption'] = caption
        if parse_mode:
            data['parse_mode'] = parse_mode
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
            
        files = {}
        
        if isinstance(video, str):
            # Video ca URL sau file_id
            data['video'] = video
        else:
            # Video ca fișier
            files['video'] = video
            
        if thumbnail:
            files['thumbnail'] = thumbnail
            
        # Timeout extins pentru video uploads
        video_timeout = aiohttp.ClientTimeout(
            total=300,     # 5 minute total
            connect=10,
            sock_read=60
        )
        
        return await self._make_request('POST', 'sendVideo', data, files, video_timeout)
        
    async def send_document(self, chat_id: int, document: Union[str, BinaryIO],
                           thumbnail: Optional[BinaryIO] = None,
                           caption: Optional[str] = None,
                           parse_mode: Optional[str] = None,
                           disable_content_type_detection: bool = False,
                           disable_notification: bool = False,
                           reply_to_message_id: Optional[int] = None,
                           reply_markup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trimite un document"""
        
        data = {
            'chat_id': chat_id,
            'disable_content_type_detection': disable_content_type_detection,
            'disable_notification': disable_notification
        }
        
        if caption:
            data['caption'] = caption
        if parse_mode:
            data['parse_mode'] = parse_mode
        if reply_to_message_id:
            data['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
            
        files = {}
        
        if isinstance(document, str):
            data['document'] = document
        else:
            files['document'] = document
            
        if thumbnail:
            files['thumbnail'] = thumbnail
            
        # Timeout extins pentru document uploads
        document_timeout = aiohttp.ClientTimeout(
            total=300,     # 5 minute total
            connect=10,
            sock_read=60
        )
        
        return await self._make_request('POST', 'sendDocument', data, files, document_timeout)
        
    async def answer_callback_query(self, callback_query_id: str,
                                   text: Optional[str] = None,
                                   show_alert: bool = False,
                                   url: Optional[str] = None,
                                   cache_time: int = 0) -> Dict[str, Any]:
        """Răspunde la un callback query"""
        
        data = {
            'callback_query_id': callback_query_id,
            'show_alert': show_alert,
            'cache_time': cache_time
        }
        
        if text:
            data['text'] = text
        if url:
            data['url'] = url
            
        return await self._make_request('POST', 'answerCallbackQuery', data)
        
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Obține informații despre un fișier"""
        
        data = {'file_id': file_id}
        return await self._make_request('GET', 'getFile', data)
        
    async def download_file(self, file_path: str) -> Optional[bytes]:
        """Descarcă un fișier de pe serverele Telegram"""
        
        try:
            await self._ensure_session()
            
            url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    self.stats.bytes_received += len(content)
                    return content
                else:
                    logger.error(f"Failed to download file: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
            
    # Metode pentru webhook management
    
    async def set_webhook(self, url: str, certificate: Optional[BinaryIO] = None,
                         ip_address: Optional[str] = None,
                         max_connections: int = 40,
                         allowed_updates: Optional[list] = None,
                         drop_pending_updates: bool = False,
                         secret_token: Optional[str] = None) -> Dict[str, Any]:
        """Configurează webhook-ul"""
        
        data = {
            'url': url,
            'max_connections': max_connections,
            'drop_pending_updates': drop_pending_updates
        }
        
        if ip_address:
            data['ip_address'] = ip_address
        if allowed_updates:
            data['allowed_updates'] = json.dumps(allowed_updates)
        if secret_token:
            data['secret_token'] = secret_token
            
        files = {}
        if certificate:
            files['certificate'] = certificate
            
        return await self._make_request('POST', 'setWebhook', data, files)
        
    async def delete_webhook(self, drop_pending_updates: bool = False) -> Dict[str, Any]:
        """Șterge webhook-ul"""
        
        data = {'drop_pending_updates': drop_pending_updates}
        return await self._make_request('POST', 'deleteWebhook', data)
        
    async def get_webhook_info(self) -> Dict[str, Any]:
        """Obține informații despre webhook"""
        
        return await self._make_request('GET', 'getWebhookInfo')
        
    # Metode utile
    
    @trace_operation("telegram_api.send_message_with_fallback")
    async def send_message_with_fallback(self, chat_id: int, text: str,
                                       parse_mode: Optional[str] = 'HTML',
                                       **kwargs) -> Dict[str, Any]:
        """
        Trimite mesaj cu fallback la text simplu dacă parse_mode eșuează
        """
        
        # Încearcă cu parse_mode
        result = await self.send_message(chat_id, text, parse_mode, **kwargs)
        
        if result.get('ok'):
            return result
            
        # Dacă eșuează cu parse_mode, încearcă fără
        if parse_mode:
            logger.warning(f"Parse mode {parse_mode} failed, trying plain text")
            result = await self.send_message(chat_id, text, None, **kwargs)
            
        return result
        
    async def send_long_message(self, chat_id: int, text: str, 
                              parse_mode: Optional[str] = None,
                              max_length: int = 4096,
                              **kwargs) -> list:
        """
        Trimite mesaje lungi împărțite în bucăți
        """
        
        if len(text) <= max_length:
            result = await self.send_message(chat_id, text, parse_mode, **kwargs)
            return [result]
            
        results = []
        start = 0
        
        while start < len(text):
            end = min(start + max_length, len(text))
            
            # Încearcă să găsești o întrerupere naturală
            if end < len(text):
                last_newline = text.rfind('\n', start, end)
                last_space = text.rfind(' ', start, end)
                
                if last_newline > start + max_length * 0.8:
                    end = last_newline + 1
                elif last_space > start + max_length * 0.8:
                    end = last_space + 1
                    
            chunk = text[start:end].strip()
            if chunk:
                result = await self.send_message(chat_id, chunk, parse_mode, **kwargs)
                results.append(result)
                
                # Delay între mesaje pentru a evita rate limiting
                await asyncio.sleep(0.1)
                
            start = end
            
        return results
        
    # Cleanup și statistici
    
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statisticile API"""
        
        success_rate = 0
        if self.stats.requests_sent > 0:
            success_rate = (self.stats.requests_successful / self.stats.requests_sent) * 100
            
        return {
            'requests_sent': self.stats.requests_sent,
            'requests_successful': self.stats.requests_successful,
            'requests_failed': self.stats.requests_failed,
            'success_rate_percent': round(success_rate, 2),
            'average_response_time_ms': round(self.stats.average_response_time * 1000, 2),
            'bytes_sent': self.stats.bytes_sent,
            'bytes_received': self.stats.bytes_received,
            'rate_limit_hits': self.stats.rate_limit_hits,
            'session_active': self.session is not None and not self.session.closed
        }
        
    async def close(self):
        """Închide session-ul HTTP"""
        
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("✅ Telegram API session closed")
            
    async def __aenter__(self):
        """Context manager entry"""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
