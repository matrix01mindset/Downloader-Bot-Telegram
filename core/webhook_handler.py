# core/webhook_handler.py - Webhook Handler Optimizat
# Versiunea: 3.0.0 - Arhitectura Nouă

import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

from utils.monitoring import monitoring, trace_operation
from utils.cache import cache
from core.message_processor import MessageProcessor
from api.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)

@dataclass
class WebhookStats:
    """Statistici pentru webhook"""
    total_updates: int = 0
    processed_messages: int = 0
    processed_callbacks: int = 0
    ignored_updates: int = 0
    error_count: int = 0
    average_processing_time: float = 0

class WebhookHandler:
    """
    Handler optimizat pentru webhook-uri Telegram
    Procesează update-urile cu rate limiting și deduplicare
    """
    
    def __init__(self, config: dict, platform_manager):
        self.config = config
        self.platform_manager = platform_manager
        
        # Telegram API
        bot_token = config.get('telegram', {}).get('token')
        if not bot_token:
            raise ValueError("Telegram bot token not found in config")
            
        self.telegram_api = TelegramAPI(bot_token)
        
        # Message processor
        self.message_processor = MessageProcessor(
            platform_manager=platform_manager,
            telegram_api=self.telegram_api,
            config=config
        )
        
        # Deduplicare mesaje
        self.processed_updates: Set[str] = set()
        self.max_processed_updates = 10000  # Limitează memoria
        
        # Statistici
        self.stats = WebhookStats()
        
        # Rate limiting per chat
        self.chat_rate_limits: Dict[int, float] = {}
        self.rate_limit_window = 60  # secunde
        self.max_requests_per_minute = config.get('rate_limiting', {}).get('per_user_per_minute', 5)
        
        logger.info("✅ Webhook handler initialized")
        
    @trace_operation("webhook.process_update")
    async def process_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesează un update de la Telegram
        """
        start_time = time.time()
        
        try:
            self.stats.total_updates += 1
            
            # Extrage informații de bază din update
            update_info = self._extract_update_info(update_data)
            if not update_info:
                self.stats.ignored_updates += 1
                return {'status': 'ignored', 'reason': 'invalid_update_format'}
            
            # Verifică deduplicarea
            if self._is_duplicate_update(update_info):
                self.stats.ignored_updates += 1
                logger.debug(f"Duplicate update ignored: {update_info['unique_id']}")
                return {'status': 'ignored', 'reason': 'duplicate_update'}
                
            # Verifică rate limiting
            if not self._check_rate_limit(update_info['chat_id']):
                self.stats.ignored_updates += 1
                logger.warning(f"Rate limit exceeded for chat {update_info['chat_id']}")
                
                # Trimite mesaj de rate limiting
                await self._send_rate_limit_message(update_info['chat_id'])
                return {'status': 'rate_limited', 'chat_id': update_info['chat_id']}
                
            # Marchează update-ul ca procesat
            self._mark_update_processed(update_info['unique_id'])
            
            # Procesează update-ul în funcție de tip
            result = None
            if update_info['type'] == 'message':
                result = await self._process_message_update(update_data, update_info)
                self.stats.processed_messages += 1
            elif update_info['type'] == 'callback_query':
                result = await self._process_callback_update(update_data, update_info)
                self.stats.processed_callbacks += 1
            else:
                result = {'status': 'ignored', 'reason': 'unsupported_update_type'}
                self.stats.ignored_updates += 1
                
            # Actualizează statistici
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            if monitoring:
                monitoring.record_metric("webhook.processing_time", processing_time)
                monitoring.record_metric("webhook.updates_processed", 1)
                
            return result or {'status': 'processed'}
            
        except Exception as e:
            self.stats.error_count += 1
            logger.error(f"Error processing webhook update: {e}")
            
            if monitoring:
                monitoring.record_error("webhook", "update_processing", str(e))
                
            return {'status': 'error', 'error': str(e)}
            
    def _extract_update_info(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrage informații relevante din update"""
        try:
            update_id = update_data.get('update_id')
            if not update_id:
                return None
                
            # Message update
            if 'message' in update_data:
                message = update_data['message']
                chat_id = message.get('chat', {}).get('id')
                user_id = message.get('from', {}).get('id')
                message_id = message.get('message_id')
                
                if not all([chat_id, user_id, message_id]):
                    return None
                    
                return {
                    'type': 'message',
                    'update_id': update_id,
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'message_id': message_id,
                    'unique_id': f"msg_{chat_id}_{message_id}_{update_id}",
                    'text': message.get('text', '')
                }
                
            # Callback query update
            elif 'callback_query' in update_data:
                callback = update_data['callback_query']
                chat_id = callback.get('message', {}).get('chat', {}).get('id')
                user_id = callback.get('from', {}).get('id')
                callback_id = callback.get('id')
                
                if not all([chat_id, user_id, callback_id]):
                    return None
                    
                return {
                    'type': 'callback_query',
                    'update_id': update_id,
                    'chat_id': chat_id,
                    'user_id': user_id,
                    'callback_id': callback_id,
                    'unique_id': f"callback_{chat_id}_{callback_id}_{update_id}",
                    'data': callback.get('data', '')
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting update info: {e}")
            return None
            
    def _is_duplicate_update(self, update_info: Dict[str, Any]) -> bool:
        """Verifică dacă update-ul este duplicat"""
        return update_info['unique_id'] in self.processed_updates
        
    def _mark_update_processed(self, unique_id: str):
        """Marchează update-ul ca procesat"""
        self.processed_updates.add(unique_id)
        
        # Limitează memoria prin eliminarea update-urilor vechi
        if len(self.processed_updates) > self.max_processed_updates:
            # Păstrează ultimele 80% din update-uri
            keep_count = int(self.max_processed_updates * 0.8)
            recent_updates = list(self.processed_updates)[-keep_count:]
            self.processed_updates = set(recent_updates)
            
    def _check_rate_limit(self, chat_id: int) -> bool:
        """Verifică rate limiting pentru chat"""
        current_time = time.time()
        
        # Curăță intrările vechi
        self._cleanup_rate_limits(current_time)
        
        # Verifică dacă chat-ul a depășit limita
        last_request_time = self.chat_rate_limits.get(chat_id, 0)
        
        if current_time - last_request_time < (self.rate_limit_window / self.max_requests_per_minute):
            return False
            
        # Actualizează timpul ultimei cereri
        self.chat_rate_limits[chat_id] = current_time
        return True
        
    def _cleanup_rate_limits(self, current_time: float):
        """Curăță intrările vechi de rate limiting"""
        cutoff_time = current_time - self.rate_limit_window
        
        expired_chats = [
            chat_id for chat_id, last_time in self.chat_rate_limits.items()
            if last_time < cutoff_time
        ]
        
        for chat_id in expired_chats:
            del self.chat_rate_limits[chat_id]
            
    async def _send_rate_limit_message(self, chat_id: int):
        """Trimite mesaj de rate limiting"""
        try:
            message = (
                "⏳ <b>Rate limit depășit</b>\n\n"
                f"Poți trimite maxim {self.max_requests_per_minute} cereri pe minut.\n"
                "Te rog așteaptă puțin înainte să încerci din nou."
            )
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending rate limit message: {e}")
            
    async def _process_message_update(self, update_data: Dict[str, Any], 
                                    update_info: Dict[str, Any]) -> Dict[str, Any]:
        """Procesează un update de tip mesaj"""
        try:
            message_data = update_data['message']
            result = await self.message_processor.process_message(
                message_data=message_data,
                update_info=update_info
            )
            return result
            
        except Exception as e:
            logger.error(f"Error processing message update: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _process_callback_update(self, update_data: Dict[str, Any],
                                     update_info: Dict[str, Any]) -> Dict[str, Any]:
        """Procesează un update de tip callback query"""
        try:
            callback_data = update_data['callback_query']
            result = await self.message_processor.process_callback_query(
                callback_data=callback_data,
                update_info=update_info
            )
            return result
            
        except Exception as e:
            logger.error(f"Error processing callback update: {e}")
            return {'status': 'error', 'error': str(e)}
            
    def _update_processing_stats(self, processing_time: float):
        """Actualizează statisticile de procesare"""
        # Calculează media mobilă a timpului de procesare
        if self.stats.average_processing_time == 0:
            self.stats.average_processing_time = processing_time
        else:
            # Media mobilă exponențială cu factor de 0.1
            self.stats.average_processing_time = (
                0.9 * self.stats.average_processing_time + 
                0.1 * processing_time
            )
            
    def get_stats(self) -> Dict[str, Any]:
        """Returnează statisticile webhook-ului"""
        return {
            "total_updates": self.stats.total_updates,
            "processed_messages": self.stats.processed_messages,
            "processed_callbacks": self.stats.processed_callbacks,
            "ignored_updates": self.stats.ignored_updates,
            "error_count": self.stats.error_count,
            "average_processing_time_ms": round(self.stats.average_processing_time * 1000, 2),
            "active_rate_limits": len(self.chat_rate_limits),
            "processed_updates_cache_size": len(self.processed_updates)
        }
        
    async def cleanup(self):
        """Curăță resursele"""
        logger.info("🧹 Cleaning up webhook handler...")
        
        # Curăță cache-urile
        self.processed_updates.clear()
        self.chat_rate_limits.clear()
        
        # Cleanup message processor
        if hasattr(self.message_processor, 'cleanup'):
            await self.message_processor.cleanup()
            
        logger.info("✅ Webhook handler cleanup complete")
        
    def reset_stats(self):
        """Resetează statisticile"""
        self.stats = WebhookStats()
        logger.info("📊 Webhook stats reset")
