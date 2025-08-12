#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Applicație simplificată pentru debugging Render deployment
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'online',
        'message': 'Telegram Video Downloader Bot - Render Test',
        'timestamp': '2025-08-12',
        'environment': {
            'PORT': os.environ.get('PORT', 'NOT SET'),
            'TELEGRAM_BOT_TOKEN': 'SET' if os.environ.get('TELEGRAM_BOT_TOKEN') else 'NOT SET',
            'WEBHOOK_URL': os.environ.get('WEBHOOK_URL', 'NOT SET')
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': '2025-08-12'
    })

@app.route('/debug')
def debug():
    return jsonify({
        'status': 'debug',
        'environment_vars': {
            key: 'SET' if value else 'NOT SET' 
            for key, value in os.environ.items() 
            if 'TOKEN' in key.upper() or 'WEBHOOK' in key.upper() or 'PORT' in key.upper()
        }
    })

@app.route('/ping')
def ping():
    return jsonify({'status': 'pong'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting simple Flask server on port {port}")
    print(f"📍 Environment check:")
    print(f"   - PORT: {os.environ.get('PORT', 'NOT SET')}")
    print(f"   - TELEGRAM_BOT_TOKEN: {'SET' if os.environ.get('TELEGRAM_BOT_TOKEN') else 'NOT SET'}")
    print(f"   - WEBHOOK_URL: {os.environ.get('WEBHOOK_URL', 'NOT SET')}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
