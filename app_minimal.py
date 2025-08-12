#!/usr/bin/env python3
# Aplicație minimală pentru debugging pe Render

import os
import logging
from flask import Flask, request, jsonify

# Configurare logging simplă
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Creează aplicația Flask
app = Flask(__name__)

# Variabile de mediu
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'NOT_SET')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'NOT_SET')
PORT = int(os.getenv('PORT', 10000))

logger.info(f"Starting minimal app on port {PORT}")
logger.info(f"Token: {'SET' if TOKEN != 'NOT_SET' else 'NOT_SET'}")
logger.info(f"Webhook URL: {WEBHOOK_URL}")

@app.route('/')
def index():
    """Pagina principală"""
    return jsonify({
        'status': 'running',
        'message': 'Telegram Bot Minimal Version',
        'version': '1.0.0',
        'token_status': 'SET' if TOKEN != 'NOT_SET' else 'NOT_SET',
        'webhook_url': WEBHOOK_URL
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check simplu - returnează întotdeauna 200"""
    return jsonify({
        'status': 'healthy',
        'message': 'Minimal bot is running',
        'port': PORT,
        'token_available': TOKEN != 'NOT_SET'
    }), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Webhook simplu"""
    if request.method == 'GET':
        return jsonify({
            'status': 'webhook_ready',
            'method': 'GET',
            'message': 'Webhook endpoint is accessible'
        }), 200
    
    # Pentru POST (mesaje de la Telegram)
    try:
        json_data = request.get_json()
        
        if not json_data:
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400
        
        logger.info(f"Received webhook: {json_data}")
        
        # Procesare simplă - doar loghează mesajul
        if 'message' in json_data:
            message = json_data['message']
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            
            logger.info(f"Message from chat {chat_id}: {text}")
            
            # Răspuns simplu pentru /start
            if text == '/start':
                # Aici ar trebui să trimitem un mesaj înapoi, dar pentru debugging doar loghează
                logger.info(f"Would send welcome message to chat {chat_id}")
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/test')
def test():
    """Endpoint de test"""
    return jsonify({
        'status': 'test_ok',
        'message': 'Test endpoint working',
        'environment': {
            'PORT': PORT,
            'TOKEN_SET': TOKEN != 'NOT_SET',
            'WEBHOOK_URL': WEBHOOK_URL
        }
    })

@app.route('/ping')
def ping():
    """Ping simplu"""
    return jsonify({'status': 'pong'}), 200

if __name__ == '__main__':
    logger.info(f"🚀 Starting minimal Flask server on port {PORT}")
    logger.info("📱 Minimal Telegram Bot - Debug Version")
    
    try:
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise