# core/message_processor.py - Message Processor Avansat
# Versiunea: 3.0.0 - Arhitectura Nouă

import logging
import asyncio
import re
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from utils.monitoring import monitoring, trace_operation
from utils.cache import cache, generate_cache_key
from utils.file_manager import FileManager
from core.retry_manager import RetryManager, RetryStrategy
from utils.activity_logger import activity_logger, log_command_executed, log_download_success, log_download_error

logger = logging.getLogger(__name__)

class MessageProcessor:
    """
    Procesor avansat pentru mesaje și callback-uri Telegram
    Gestionează comenzi, URL-uri video și interacțiuni cu utilizatorii
    """
    
    def __init__(self, platform_manager, telegram_api, config: dict):
        self.platform_manager = platform_manager
        self.telegram_api = telegram_api
        self.config = config
        
        # File manager pentru gestionarea fișierelor temporare
        self.file_manager = FileManager(config.get('files', {}))
        
        # Retry manager pentru operații eșuate
        self.retry_manager = RetryManager(config.get('retry', {}))
        
        # Pattern-uri pentru detectarea URL-urilor
        self.url_patterns = [
            r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)[\w\-_]+',
            r'https?://(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com|m\.tiktok\.com)[@/\w\-._]+',
            r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w\-_]+/?',
            r'https?://(?:www\.)?(?:facebook\.com|fb\.watch|fb\.me|m\.facebook\.com)/[\w\-._/?=&]+',
            r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[\w]+/status/\d+',
            r'https?://(?:www\.)?threads\.net/@[\w.]+/post/[\w\-_]+',
            r'https?://(?:www\.)?(?:pinterest\.com|pin\.it)/[\w\-._/?=&]+',
            r'https?://(?:www\.)?(?:reddit\.com|redd\.it)/r/[\w]+/comments/[\w\-_/]+',
            r'https?://(?:www\.)?vimeo\.com/[\w\-_]+',
            r'https?://(?:www\.)?(?:dailymotion\.com|dai\.ly)/[\w\-._/?=&]+'
        ]
        
        # Mesaje template
        self.messages = config.get('messages', {})
        
        logger.info("✅ Message processor initialized")
        
    @trace_operation("message_processor.process_message")
    async def process_message(self, message_data: Dict[str, Any], 
                             update_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesează un mesaj primit
        """
        try:
            chat_id = update_info['chat_id']
            user_id = update_info['user_id']
            text = message_data.get('text', '').strip()
            
            logger.info(f"Processing message from user {user_id} in chat {chat_id}: {text[:50]}...")
            
            # Procesează comenzile
            if text.startswith('/'):
                return await self._process_command(chat_id, user_id, text, message_data)
                
            # Verifică dacă textul conține URL-uri video
            detected_urls = self._extract_video_urls(text)
            if detected_urls:
                return await self._process_video_urls(chat_id, user_id, detected_urls)
                
            # Răspuns pentru mesaje fără URL-uri
            await self._send_help_message(chat_id)
            return {'status': 'help_sent'}
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self._send_error_message(chat_id, "A apărut o eroare la procesarea mesajului.")
            return {'status': 'error', 'error': str(e)}
            
    @trace_operation("message_processor.process_command")
    async def _process_command(self, chat_id: int, user_id: int, command: str, 
                             message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesează comenzile botului"""
        try:
            command_parts = command.lower().split()
            main_command = command_parts[0]
            
            # Log comanda executată
            log_command_executed(main_command, user_id, chat_id, True)
            
            if main_command in ['/start', '/menu']:
                await self._send_welcome_message(chat_id)
                return {'status': 'welcome_sent'}
                
            elif main_command == '/help':
                await self._send_help_message(chat_id, detailed=True)
                return {'status': 'help_sent'}
                
            elif main_command == '/ping':
                await self._handle_ping_command(chat_id)
                return {'status': 'ping_sent'}
                
            elif main_command == '/stats' and self._is_admin(user_id):
                await self._send_stats_message(chat_id)
                return {'status': 'stats_sent'}
                
            elif main_command == '/platforms':
                await self._send_platforms_message(chat_id)
                return {'status': 'platforms_sent'}
                
            elif main_command == '/quality':
                await self._send_quality_info(chat_id)
                return {'status': 'quality_info_sent'}
                
            elif main_command == '/log' and self._is_admin(user_id):
                await self._handle_log_command(chat_id)
                return {'status': 'log_sent'}
                
            else:
                await self._send_unknown_command_message(chat_id, command)
                return {'status': 'unknown_command'}
                
        except Exception as e:
            logger.error(f"Error processing command {command}: {e}")
            # Log eroarea comenzii
            log_command_executed(command, user_id, chat_id, False)
            await self._send_error_message(chat_id, f"Eroare la procesarea comenzii: {e}")
            return {'status': 'error', 'error': str(e)}
            
    def _extract_video_urls(self, text: str) -> List[str]:
        """Extrage URL-urile video din text"""
        urls = []
        
        for pattern in self.url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.extend(matches)
            
        # Deduplică URL-urile
        return list(set(urls))
        
    @trace_operation("message_processor.process_video_urls")
    async def _process_video_urls(self, chat_id: int, user_id: int, urls: List[str]) -> Dict[str, Any]:
        """Procesează URL-urile video detectate"""
        try:
            if len(urls) > 3:
                await self.telegram_api.send_message(
                    chat_id=chat_id,
                    text="⚠️ <b>Prea multe URL-uri</b>\n\n"
                         "Poți procesa maxim 3 URL-uri odată. "
                         "Te rog trimite-le în mesaje separate.",
                    parse_mode='HTML'
                )
                return {'status': 'too_many_urls'}
                
            results = []
            
            for url in urls:
                try:
                    # Trimite mesaj de procesare
                    status_message = await self.telegram_api.send_message(
                        chat_id=chat_id,
                        text=f"⚡ <b>Procesez video-ul...</b>\n\n"
                             f"🔗 <code>{url}</code>\n\n"
                             f"Te rog așteaptă...",
                        parse_mode='HTML'
                    )
                    
                    if not status_message or not status_message.get('ok'):
                        logger.error(f"Failed to send status message for {url}")
                        continue
                        
                    status_message_id = status_message['result']['message_id']
                    
                    # Procesează URL-ul cu retry logic
                    result = await self.retry_manager.execute_with_retry(
                        self._download_and_send_video,
                        chat_id, user_id, url, status_message_id,
                        error_type='network_error'
                    )
                    
                    # Log rezultatul descărcării
                    if result and result.get('status') == 'success':
                        log_download_success(result.get('platform', 'unknown'), url, 0, user_id, chat_id)
                    else:
                        error_msg = result.get('error', 'Unknown error') if result else 'No result'
                        log_download_error(result.get('platform', 'unknown') if result else 'unknown', url, error_msg, user_id, chat_id)
                    
                    results.append({
                        'url': url,
                        'result': result
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    
                    # Încearcă să trimită mesaj de eroare
                    try:
                        await self.telegram_api.send_message(
                            chat_id=chat_id,
                            text=f"❌ <b>Eroare la procesarea URL-ului:</b>\n\n"
                                 f"🔗 <code>{url}</code>\n\n"
                                 f"📝 <b>Eroare:</b> {str(e)}",
                            parse_mode='HTML'
                        )
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {send_error}")
                        
                    results.append({
                        'url': url,
                        'result': {'status': 'error', 'error': str(e)}
                    })
                    
            return {'status': 'urls_processed', 'results': results}
            
        except Exception as e:
            logger.error(f"Error processing video URLs: {e}")
            await self._send_error_message(chat_id, f"Eroare la procesarea URL-urilor: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _download_and_send_video(self, chat_id: int, user_id: int, url: str, 
                                     status_message_id: int) -> Dict[str, Any]:
        """Descarcă și trimite un video"""
        try:
            # Actualizează mesajul de status
            await self.telegram_api.edit_message_text(
                chat_id=chat_id,
                message_id=status_message_id,
                text=f"🔍 <b>Analizez video-ul...</b>\n\n"
                     f"🔗 <code>{url}</code>\n\n"
                     f"Extrag informații...",
                parse_mode='HTML'
            )
            
            # Verifică cache-ul pentru metadata
            cache_key = generate_cache_key("video_info", url)
            cached_info = await cache.get(cache_key)
            
            if not cached_info:
                # Obține informații despre video
                platform = await self.platform_manager.get_platform_for_url(url)
                if not platform:
                    raise Exception("Platformă nesuportată")
                    
                video_info = await platform.get_video_info(url)
                
                # Cache informațiile pentru 1 oră
                await cache.set(cache_key, video_info, ttl=3600)
            else:
                video_info = cached_info
                
            # Verifică constrângerile
            validation_result = await self._validate_video_constraints(video_info)
            if not validation_result['valid']:
                await self.telegram_api.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message_id,
                    text=f"❌ <b>Video invalid:</b>\n\n"
                         f"🔗 <code>{url}</code>\n\n"
                         f"📝 <b>Motiv:</b> {validation_result['error']}",
                    parse_mode='HTML'
                )
                return validation_result
                
            # Actualizează status pentru descărcare
            await self.telegram_api.edit_message_text(
                chat_id=chat_id,
                message_id=status_message_id,
                text=f"⬇️ <b>Descarc video-ul...</b>\n\n"
                     f"📹 <b>Titlu:</b> {video_info.title[:50]}...\n"
                     f"👤 <b>Creator:</b> {video_info.uploader or 'Necunoscut'}\n"
                     f"⏱️ <b>Durată:</b> {self._format_duration(video_info.duration)}\n\n"
                     f"Te rog așteaptă...",
                parse_mode='HTML'
            )
            
            # Descarcă video-ul
            download_result = await self.platform_manager.download_video(url, user_id)
            
            if not download_result['success']:
                await self.telegram_api.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message_id,
                    text=f"❌ <b>Eroare la descărcare:</b>\n\n"
                         f"🔗 <code>{url}</code>\n\n"
                         f"📝 <b>Eroare:</b> {download_result['error']}",
                    parse_mode='HTML'
                )
                return download_result
                
            # Trimite video-ul
            await self._send_video_file(
                chat_id=chat_id,
                file_path=download_result['file_path'],
                video_info=video_info,
                download_info=download_result
            )
            
            # Șterge mesajul de status
            try:
                await self.telegram_api.delete_message(
                    chat_id=chat_id,
                    message_id=status_message_id
                )
            except Exception as delete_error:
                logger.debug(f"Could not delete status message: {delete_error}")
                
            # Cleanup fișierul temporar
            await self.file_manager.cleanup_file(download_result['file_path'])
            
            return {'status': 'success', 'video_sent': True}
            
        except Exception as e:
            logger.error(f"Error downloading and sending video: {e}")
            
            # Actualizează mesajul cu eroarea
            try:
                await self.telegram_api.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message_id,
                    text=f"❌ <b>Eroare neașteptată:</b>\n\n"
                         f"🔗 <code>{url}</code>\n\n"
                         f"📝 <b>Eroare:</b> {str(e)}",
                    parse_mode='HTML'
                )
            except Exception:
                pass
                
            return {'status': 'error', 'error': str(e)}
            
    async def _send_video_file(self, chat_id: int, file_path: str, 
                              video_info, download_info: Dict[str, Any]):
        """Trimite fișierul video către utilizator"""
        try:
            # Creează caption-ul
            caption = self._create_video_caption(video_info, download_info)
            
            # Trimite video-ul
            with open(file_path, 'rb') as video_file:
                result = await self.telegram_api.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    parse_mode='HTML',
                    supports_streaming=True
                )
                
                if result and result.get('ok'):
                    logger.info(f"✅ Video sent successfully to chat {chat_id}")
                    
                    if monitoring:
                        monitoring.record_metric("videos_sent_successfully", 1)
                else:
                    logger.error(f"❌ Failed to send video to chat {chat_id}: {result}")
                    raise Exception("Failed to send video via Telegram API")
                    
        except Exception as e:
            logger.error(f"Error sending video file: {e}")
            raise
            
    def _create_video_caption(self, video_info, download_info: Dict[str, Any]) -> str:
        """Creează caption pentru video"""
        try:
            title = video_info.title or 'Video'
            uploader = video_info.uploader or ''
            description = video_info.description or ''
            duration = video_info.duration or 0
            file_size = download_info.get('file_size', 0)
            
            # Construiește caption-ul
            caption_parts = []
            
            # Titlu
            caption_parts.append(f"✅ <b>{self._escape_html(title[:100])}</b>")
            
            # Creator
            if uploader:
                caption_parts.append(f"👤 <b>Creator:</b> {self._escape_html(uploader[:50])}")
                
            # Durată
            if duration > 0:
                caption_parts.append(f"⏱️ <b>Durată:</b> {self._format_duration(duration)}")
                
            # Mărime fișier
            if file_size > 0:
                size_mb = file_size / (1024 * 1024)
                caption_parts.append(f"📦 <b>Mărime:</b> {size_mb:.1f} MB")
                
            # Descriere (limitată)
            if description and len(description.strip()) > 10:
                desc_preview = description.strip()[:150]
                if len(description) > 150:
                    desc_preview += "..."
                caption_parts.append(f"\n📝 <b>Descriere:</b>\n{self._escape_html(desc_preview)}")
                
            # Footer
            caption_parts.append("\n🎬 <b>Descărcare completă!</b>")
            
            caption = "\n".join(caption_parts)
            
            # Limitează la 1024 caractere (limita Telegram)
            if len(caption) > 1024:
                caption = caption[:1020] + "..."
                
            return caption
            
        except Exception as e:
            logger.error(f"Error creating video caption: {e}")
            return f"✅ <b>{self._escape_html(video_info.title or 'Video')}</b>\n\n🎬 Descărcare completă!"
            
    async def _validate_video_constraints(self, video_info) -> Dict[str, Any]:
        """Validează constrângerile video-ului"""
        try:
            # Verifică durata (max 3 ore)
            max_duration = 3 * 60 * 60  # 3 ore în secunde
            if video_info.duration and video_info.duration > max_duration:
                return {
                    'valid': False,
                    'error': f'Video prea lung: {self._format_duration(video_info.duration)} '
                            f'(maxim: {self._format_duration(max_duration)})'
                }
                
            # Alte validări pot fi adăugate aici
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating video constraints: {e}")
            return {'valid': False, 'error': f'Eroare la validare: {e}'}
            
    # Metode pentru comenzi specifice
    async def _send_welcome_message(self, chat_id: int):
        """Trimite mesajul de bun venit"""
        message = self.messages.get('welcome', 
            "🎬 <b>Bun venit la Video Downloader Bot!</b>\n\n"
            "📱 Trimite-mi un link de pe platformele suportate pentru a descărca videoclipuri!"
        )
        
        # Adaugă butoane inline
        keyboard = [
            [
                {"text": "📖 Cum funcționează", "callback_data": "help"},
                {"text": "🌐 Platforme", "callback_data": "platforms"}
            ],
            [
                {"text": "⚙️ Setări", "callback_data": "settings"},
                {"text": "📊 Statistici", "callback_data": "stats"}
            ]
        ]
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML',
            reply_markup={'inline_keyboard': keyboard}
        )
        
    async def _send_help_message(self, chat_id: int, detailed: bool = False):
        """Trimite mesajul de ajutor"""
        if detailed:
            message = (
                "🤖 <b>Bot Descărcare Video - Ghid Complet</b>\n\n"
                
                "📋 <b>Comenzi disponibile:</b>\n"
                "• /start - Pornește botul\n"
                "• /help - Ghid complet\n"
                "• /platforms - Platforme suportate\n"
                "• /ping - Test funcționalitate\n\n"
                
                "🆘 <b>Cum să folosești botul:</b>\n"
                "1️⃣ Copiază link-ul videoclipului\n"
                "2️⃣ Trimite-l în acest chat\n"
                "3️⃣ Așteaptă procesarea (10-60s)\n"
                "4️⃣ Primești videoclipul descărcat\n\n"
                
                "⚠️ <b>Limitări:</b>\n"
                "• Mărime max: 45MB (limita Telegram)\n"
                "• Durată max: 3 ore\n"
                "• Doar videoclipuri publice\n"
                "• Maxim 3 URL-uri per mesaj\n\n"
                
                "💡 <b>Sfaturi:</b>\n"
                "• Folosește link-uri directe\n"
                "• Verifică că videoclipul este public\n"
                "• Pentru probleme, folosește /ping"
            )
        else:
            message = (
                "📖 <b>Ajutor rapid</b>\n\n"
                "Trimite-mi un link de pe o platformă suportată "
                "și voi descărca videoclipul pentru tine!\n\n"
                "Folosește /help pentru ghidul complet."
            )
            
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        
    async def _send_platforms_message(self, chat_id: int):
        """Trimite lista platformelor suportate"""
        platforms = []
        
        if self.platform_manager and self.platform_manager.platforms:
            for platform_name, platform in self.platform_manager.platforms.items():
                status_emoji = "✅" if hasattr(platform, 'is_healthy') and platform.is_healthy() else "⚠️"
                platforms.append(f"{status_emoji} <b>{platform_name.title()}</b>")
        
        if platforms:
            platform_list = "\n".join(platforms)
        else:
            platform_list = "❌ Nu sunt disponibile platforme momentan"
            
        message = (
            f"🌐 <b>Platforme suportate ({len(platforms)}):</b>\n\n"
            f"{platform_list}\n\n"
            f"💡 <b>Notă:</b> Trimite link-uri de pe aceste platforme "
            f"pentru a descărca videoclipuri."
        )
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        
    async def _handle_ping_command(self, chat_id: int):
        """Gestionează comanda de ping"""
        start_time = time.time()
        
        # Trimite mesaj inițial
        message = await self.telegram_api.send_message(
            chat_id=chat_id,
            text="🏓 <b>Ping...</b>",
            parse_mode='HTML'
        )
        
        if message and message.get('ok'):
            # Calculează timpul de răspuns
            response_time = (time.time() - start_time) * 1000
            
            # Actualizează mesajul
            await self.telegram_api.edit_message_text(
                chat_id=chat_id,
                message_id=message['result']['message_id'],
                text=f"🏓 <b>Pong!</b>\n\n"
                     f"⏱️ <b>Timp răspuns:</b> {response_time:.1f}ms\n"
                     f"✅ <b>Status:</b> Funcțional",
                parse_mode='HTML'
            )
    
    async def _handle_log_command(self, chat_id: int):
        """Gestionează comanda /log - trimite raportul de activitate"""
        try:
            # Trimite mesaj de procesare
            status_message = await self.telegram_api.send_message(
                chat_id=chat_id,
                text="📊 <b>Generez raportul de activitate...</b>\n\nTe rog așteaptă...",
                parse_mode='HTML'
            )
            
            # Generează raportul
            report = activity_logger.generate_report(hours=24)
            
            # Creează fișierul temporar
            import tempfile
            import os
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bot_activity_log_{timestamp}.txt"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(report)
                temp_file_path = temp_file.name
            
            try:
                # Trimite fișierul
                await self.telegram_api.send_document(
                    chat_id=chat_id,
                    document=temp_file_path,
                    filename=filename,
                    caption=f"📊 <b>Raport Activitate Bot</b>\n\n"
                           f"📅 <b>Perioada:</b> Ultimele 24 ore\n"
                           f"🕐 <b>Generat la:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                           f"✅ Activități cu succes\n"
                           f"❌ Erori și probleme",
                    parse_mode='HTML'
                )
                
                # Șterge mesajul de status
                if status_message and status_message.get('ok'):
                    await self.telegram_api.delete_message(
                        chat_id=chat_id,
                        message_id=status_message['result']['message_id']
                    )
                    
            finally:
                # Șterge fișierul temporar
                try:
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_file_path}: {cleanup_error}")
                    
        except Exception as e:
            logger.error(f"Error handling log command: {e}")
            await self._send_error_message(chat_id, f"Eroare la generarea raportului: {e}")
            
    def _format_duration(self, duration_seconds: Optional[float]) -> str:
        """Formatează durata în format human-readable"""
        if not duration_seconds or duration_seconds <= 0:
            return "Necunoscută"
            
        try:
            seconds = int(duration_seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
                
        except Exception:
            return "Necunoscută"
            
    def _escape_html(self, text: str) -> str:
        """Escape caractere HTML"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
                   
    def _is_admin(self, user_id: int) -> bool:
        """Verifică dacă utilizatorul este admin"""
        security_config = self.config.get('security', {})
        admin_ids = security_config.get('admin_user_ids', [])
        return user_id in admin_ids
        
    async def _send_error_message(self, chat_id: int, error_text: str):
        """Trimite mesaj de eroare"""
        try:
            message = f"❌ <b>Eroare</b>\n\n{self._escape_html(error_text)}"
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
            
    async def _send_unknown_command_message(self, chat_id: int, command: str):
        """Trimite mesaj pentru comandă necunoscută"""
        message = (
            f"❓ <b>Comandă necunoscută:</b> <code>{self._escape_html(command)}</code>\n\n"
            f"Folosește /help pentru lista comenzilor disponibile."
        )
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        
    # Callback query processing
    async def process_callback_query(self, callback_data: Dict[str, Any],
                                   update_info: Dict[str, Any]) -> Dict[str, Any]:
        """Procesează callback query-urile"""
        try:
            chat_id = update_info['chat_id']
            user_id = update_info['user_id']
            callback_id = update_info['callback_id']
            data = callback_data.get('data', '')
            
            # Răspunde la callback query
            await self.telegram_api.answer_callback_query(
                callback_query_id=callback_id,
                text="Procesez...",
                show_alert=False
            )
            
            # Procesează datele callback-ului
            if data == 'help':
                await self._send_help_message(chat_id, detailed=True)
            elif data == 'platforms':
                await self._send_platforms_message(chat_id)
            elif data == 'settings':
                await self._send_settings_message(chat_id)
            elif data == 'stats' and self._is_admin(user_id):
                await self._send_stats_message(chat_id)
            else:
                await self.telegram_api.answer_callback_query(
                    callback_query_id=callback_id,
                    text="❌ Acțiune necunoscută",
                    show_alert=True
                )
                
            return {'status': 'callback_processed', 'data': data}
            
        except Exception as e:
            logger.error(f"Error processing callback query: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _send_settings_message(self, chat_id: int):
        """Trimite mesajul cu setările"""
        message = (
            "⚙️ <b>Setări Bot</b>\n\n"
            
            "📏 <b>Limitări:</b>\n"
            "• Mărime max: 45MB\n"
            "• Durată max: 3 ore\n"
            "• Calitate max: 720p\n\n"
            
            "🔒 <b>Securitate:</b>\n"
            "• Rate limiting activ\n"
            "• Validare URL-uri\n"
            "• Cleanup automat fișiere\n\n"
            
            "⚡ <b>Performanță:</b>\n"
            "• Cache inteligent\n"
            "• Retry automat\n"
            "• Optimizat pentru Free Tier"
        )
        
        await self.telegram_api.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        
    async def _send_stats_message(self, chat_id: int):
        """Trimite mesajul cu statisticile sistemului"""
        try:
            # Obține statistici de la platform manager
            platform_stats = self.platform_manager.get_manager_stats()
            
            # Obține statistici de la bot manager (dacă este disponibil)
            bot_stats = {}
            try:
                # Încearcă să obțină statistici de la bot manager prin import global
                import sys
                if 'app_new' in sys.modules:
                    app_module = sys.modules['app_new']
                    if hasattr(app_module, 'bot_manager') and app_module.bot_manager:
                        bot_stats = app_module.bot_manager.get_health_status()
            except Exception as e:
                logger.warning(f"Could not get bot manager stats: {e}")
            
            # Calculează statistici generale
            total_requests = platform_stats.get('total_requests', 0)
            successful_extractions = platform_stats.get('successful_extractions', 0)
            successful_downloads = platform_stats.get('successful_downloads', 0)
            failed_requests = platform_stats.get('failed_requests', 0)
            
            # Calculează total downloads și success rate
            total_downloads = successful_downloads
            if total_requests > 0:
                success_rate = (successful_downloads / total_requests) * 100
            else:
                success_rate = 0
                
            # Pentru compatibilitate cu bot_manager stats
            if bot_stats:
                total_requests = max(total_requests, bot_stats.get('total_requests', 0))
                successful_requests = bot_stats.get('successful_requests', successful_downloads)
                if total_requests > 0:
                    success_rate = (successful_requests / total_requests) * 100
            
            # Formatează uptime
            uptime_seconds = bot_stats.get('uptime_seconds', 0)
            uptime_formatted = self._format_uptime(uptime_seconds)
            
            # Formatează memoria
            memory_mb = bot_stats.get('memory_usage_mb', 0)
            
            # Construiește mesajul principal
            message = (
                "📊 <b>System Statistics:</b>\n\n"
                f"• <b>Uptime:</b> {uptime_formatted}\n"
                f"• <b>Downloads:</b> {total_downloads:,}\n"
                f"• <b>Success Rate:</b> {success_rate:.1f}%\n"
                f"• <b>Memory Usage:</b> {memory_mb:.0f}MB\n\n"
            )
            
            # Adaugă statistici per platformă
            platform_data = platform_stats.get('platform_stats', {})
            if platform_data:
                message += "🌐 <b>Platforms:</b>\n"
                
                # Sortează platformele după numărul de cereri
                sorted_platforms = sorted(
                    platform_data.items(), 
                    key=lambda x: x[1].get('requests', 0), 
                    reverse=True
                )
                
                for platform_name, stats in sorted_platforms[:5]:  # Top 5 platforme
                    requests = stats.get('requests', 0)
                    if requests > 0:
                        percentage = (requests / total_requests * 100) if total_requests > 0 else 0
                        successes = stats.get('successes', 0)
                        platform_success_rate = (successes / requests * 100) if requests > 0 else 0
                        
                        message += f"  • <b>{platform_name.title()}:</b> {requests:,} ({percentage:.1f}%) - {platform_success_rate:.1f}% success\n"
            
            # Adaugă metrici de performanță
            message += "\n⚡ <b>Performance:</b>\n"
            
            # Telegram API stats
            telegram_stats = getattr(self.telegram_api, 'stats', {})
            if telegram_stats:
                avg_response_time = telegram_stats.get('average_response_time', 0)
                message += f"  • <b>Avg API Response:</b> {avg_response_time:.2f}s\n"
            
            # Platform average response time
            total_response_time = 0
            total_platform_requests = 0
            for platform_name, stats in platform_data.items():
                platform_requests = stats.get('requests', 0)
                avg_time = stats.get('average_response_time', 0)
                if platform_requests > 0 and avg_time > 0:
                    total_response_time += avg_time * platform_requests
                    total_platform_requests += platform_requests
            
            if total_platform_requests > 0:
                overall_avg_time = total_response_time / total_platform_requests
                message += f"  • <b>Avg Download Time:</b> {overall_avg_time:.2f}s\n"
            
            # Active downloads
            active_downloads = bot_stats.get('active_downloads', 0)
            message += f"  • <b>Active Downloads:</b> {active_downloads}\n"
            
            # Adaugă informații despre sistem
            message += "\n🔧 <b>System Info:</b>\n"
            platforms_loaded = platform_stats.get('platforms_loaded', 0)
            message += f"  • <b>Platforms Loaded:</b> {platforms_loaded}\n"
            
            cache_enabled = bot_stats.get('cache_enabled', False)
            message += f"  • <b>Cache:</b> {'✅ Enabled' if cache_enabled else '❌ Disabled'}\n"
            
            monitoring_enabled = bot_stats.get('monitoring_enabled', False)
            message += f"  • <b>Monitoring:</b> {'✅ Enabled' if monitoring_enabled else '❌ Disabled'}\n"
            
            await self.telegram_api.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"Error sending stats message: {e}")
            await self._send_error_message(chat_id, f"Eroare la obținerea statisticilor: {e}")
    
    def _format_uptime(self, seconds: int) -> str:
        """Formatează uptime-ul în format lizibil"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = ((seconds % 86400) % 3600) // 60
            return f"{days}d {hours}h {minutes}m"
            
    async def cleanup(self):
        """Curăță resursele"""
        logger.info("🧹 Cleaning up message processor...")
        
        if hasattr(self.file_manager, 'cleanup_all'):
            await self.file_manager.cleanup_all()
            
        logger.info("✅ Message processor cleanup complete")
