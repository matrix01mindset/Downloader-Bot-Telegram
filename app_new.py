# app_new.py - Flask Application cu Arhitectura Nouă
# Versiunea: 3.0.0 - Arhitectura Nouă

import os
import sys
import asyncio
import logging
import yaml
from flask import Flask, request, jsonify
from typing import Dict, Any

# Import-uri pentru arhitectura nouă
from core.bot_manager import get_bot_manager
from core.webhook_handler import WebhookHandler
from utils.monitoring import monitoring, trace_operation
from utils.cache import cache

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Verifică variabilele de mediu critice
def check_environment():
    """Verifică variabilele de mediu necesare"""
    required_vars = ['TELEGRAM_BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Set these variables and restart the application.")
        sys.exit(1)
    
    logger.info("✅ All required environment variables are set")

def load_config() -> Dict[str, Any]:
    """Încarcă configurația din config.yaml și environment"""
    try:
        # Încarcă configurația de bază din YAML
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Override cu variabilele de mediu
        config['telegram']['token'] = os.getenv('TELEGRAM_BOT_TOKEN')
        config['telegram']['webhook_url'] = os.getenv('WEBHOOK_URL', '')
        config['server']['port'] = int(os.getenv('PORT', config['server']['port']))
        
        # Configurări specifice pentru Free Tier
        config['performance']['memory_limit_mb'] = int(os.getenv('MEMORY_LIMIT_MB', 200))
        config['performance']['max_concurrent_downloads'] = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', 2))
        
        logger.info("✅ Configuration loaded successfully")
        return config
        
    except Exception as e:
        logger.error(f"❌ Error loading configuration: {e}")
        # Configurație de fallback minimă
        return {
            'telegram': {
                'token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'webhook_url': os.getenv('WEBHOOK_URL', ''),
                'max_connections': 5
            },
            'server': {
                'host': '0.0.0.0',
                'port': int(os.getenv('PORT', 5000))
            },
            'cache': {'enabled': True},
            'performance': {
                'memory_limit_mb': 200,
                'max_concurrent_downloads': 2
            },
            'platforms': {
                'youtube': {'enabled': True, 'max_file_size_mb': 45},
                'tiktok': {'enabled': True, 'max_file_size_mb': 45},
                'instagram': {'enabled': True, 'max_file_size_mb': 45},
                'facebook': {'enabled': True, 'max_file_size_mb': 45}
            },
            'messages': {
                'welcome': '🎬 Bun venit la Video Downloader Bot!',
                'processing': '⚡ Procesez video-ul, te rog așteaptă...'
            }
        }

# Verifică mediul și încarcă configurația
check_environment()
config = load_config()

# Creează aplicația Flask
app = Flask(__name__)

# Variabile globale pentru componente
bot_manager = None
webhook_handler = None

async def initialize_application():
    """Inițializează aplicația async"""
    global bot_manager, webhook_handler
    
    try:
        logger.info("🚀 Initializing application...")
        
        # Inițializează bot manager
        bot_manager = await get_bot_manager(config)
        
        # Inițializează webhook handler
        webhook_handler = WebhookHandler(config, bot_manager.platform_manager)
        
        logger.info("✅ Application initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}")
        return False

def run_async(coro):
    """Utilitară pentru a rula corutine în context sincron"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Creează task dacă loop-ul rulează deja
            task = asyncio.create_task(coro)
            return task
        else:
            # Rulează direct dacă loop-ul nu rulează
            return loop.run_until_complete(coro)
    except RuntimeError:
        # Creează loop nou dacă nu există unul
        return asyncio.run(coro)

# Rute Flask

@app.route('/')
def index():
    """Endpoint principal"""
    try:
        status_info = {
            'status': 'running',
            'message': 'Telegram Video Downloader Bot is active',
            'version': '3.0.0',
            'architecture': 'modular'
        }
        
        if bot_manager:
            health_status = bot_manager.get_health_status()
            status_info['health'] = health_status
            
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        if not bot_manager:
            return jsonify({
                'status': 'unhealthy',
                'reason': 'Bot manager not initialized'
            }), 503
            
        if not bot_manager.is_ready():
            return jsonify({
                'status': 'unhealthy', 
                'reason': 'Bot manager not ready'
            }), 503
            
        health_status = bot_manager.get_health_status()
        
        return jsonify({
            'status': 'healthy',
            'details': health_status,
            'timestamp': health_status.get('uptime_seconds', 0)
        })
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Procesează webhook-urile de la Telegram"""
    try:
        if not webhook_handler:
            logger.error("Webhook handler not initialized")
            return jsonify({
                'status': 'error',
                'message': 'Service not ready'
            }), 503
            
        # Obține datele din request
        json_data = request.get_json()
        if not json_data:
            logger.warning("Empty JSON data received")
            return jsonify({
                'status': 'error', 
                'message': 'No JSON data'
            }), 400
            
        logger.debug(f"Webhook received: update_id={json_data.get('update_id')}")
        
        # Procesează update-ul async
        async def process_webhook():
            try:
                result = await webhook_handler.process_update(json_data)
                bot_manager.increment_request_count()
                
                if result.get('status') == 'error':
                    bot_manager.increment_error_count()
                else:
                    bot_manager.increment_success_count()
                    
                return result
            except Exception as e:
                logger.error(f"Error processing webhook: {e}")
                bot_manager.increment_error_count()
                
                if monitoring:
                    monitoring.record_error("webhook", "processing", str(e))
                    
                return {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Rulează procesarea în loop async
        result = run_async(process_webhook())
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error in webhook endpoint: {e}")
        
        if bot_manager:
            bot_manager.increment_error_count()
            
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Configurează webhook-ul Telegram"""
    try:
        if not bot_manager or not bot_manager.platform_manager:
            return jsonify({
                'status': 'error',
                'message': 'Bot manager not ready'
            }), 503
            
        webhook_url = config['telegram'].get('webhook_url')
        if not webhook_url:
            # Încearcă să detecteze URL-ul din request
            webhook_url = request.url_root.rstrip('/') + '/webhook'
            
        # Configurează webhook-ul async
        async def configure_webhook():
            from api.telegram_api import TelegramAPI
            
            telegram_api = TelegramAPI(config['telegram']['token'])
            
            result = await telegram_api.set_webhook(
                url=webhook_url,
                max_connections=config['telegram'].get('max_connections', 5),
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            )
            
            await telegram_api.close()
            return result
            
        result = run_async(configure_webhook())
        
        if result and result.get('ok'):
            logger.info(f"✅ Webhook configured: {webhook_url}")
            return jsonify({
                'status': 'success',
                'webhook_url': webhook_url,
                'telegram_response': result
            })
        else:
            logger.error(f"❌ Webhook configuration failed: {result}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to configure webhook',
                'telegram_response': result
            }), 500
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/stats')
def stats():
    """Endpoint pentru statistici"""
    try:
        if not bot_manager:
            return jsonify({
                'status': 'error',
                'message': 'Bot manager not initialized'
            }), 503
            
        stats_data = {
            'bot': bot_manager.get_health_status(),
            'cache': cache.get_stats() if hasattr(cache, 'get_stats') else {},
        }
        
        # Adaugă statistici platforme dacă sunt disponibile
        if bot_manager.platform_manager:
            stats_data['platforms'] = bot_manager.platform_manager.get_stats()
            
        # Adaugă statistici webhook dacă sunt disponibile
        if webhook_handler:
            stats_data['webhook'] = webhook_handler.get_stats()
            
        return jsonify(stats_data)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

@app.route('/ping')
def ping():
    """Endpoint simplu pentru ping"""
    return jsonify({
        'pong': True,
        'status': 'alive',
        'version': '3.0.0'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

# Cleanup la shutdown
import atexit

async def cleanup_application():
    """Curăță resursele la oprire"""
    try:
        logger.info("🧹 Starting application cleanup...")
        
        if webhook_handler:
            await webhook_handler.cleanup()
            
        if bot_manager:
            await bot_manager.shutdown()
            
        if hasattr(cache, 'cleanup'):
            await cache.cleanup()
            
        logger.info("✅ Application cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def sync_cleanup():
    """Wrapper sincron pentru cleanup"""
    try:
        run_async(cleanup_application())
    except Exception as e:
        logger.error(f"Error in sync cleanup: {e}")

atexit.register(sync_cleanup)

# Inițializare la startup
def initialize_on_startup():
    """Inițializează aplicația la pornire"""
    try:
        success = run_async(initialize_application())
        if not success:
            logger.error("❌ Application initialization failed")
            sys.exit(1)
        else:
            logger.info("✅ Application ready to serve requests")
    except Exception as e:
        logger.error(f"❌ Startup initialization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Inițializează aplicația
    initialize_on_startup()
    
    # Pornește serverul Flask
    host = config['server']['host']
    port = config['server']['port']
    
    logger.info(f"🚀 Starting Flask server on {host}:{port}")
    
    app.run(
        host=host,
        port=port,
        debug=False,  # Nu activa debug în producție
        threaded=True,
        use_reloader=False  # Evită reloader-ul în producție
    )
else:
    # Pentru deployment-uri (Gunicorn, etc.)
    # Inițializarea se va face în primul request
    @app.before_first_request
    def before_first_request():
        initialize_on_startup()
