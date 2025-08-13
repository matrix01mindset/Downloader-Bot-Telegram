#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test minimal pentru Render deployment
"""

import os
import sys
import logging
from flask import Flask, jsonify

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_minimal_app():
    """Creează o aplicație Flask minimală pentru test"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return jsonify({
            'status': 'success',
            'message': 'Minimal Render test app is running',
            'python_version': sys.version,
            'environment': {
                'RENDER': os.getenv('RENDER'),
                'PORT': os.getenv('PORT'),
                'FLASK_ENV': os.getenv('FLASK_ENV')
            }
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'message': 'App is running'
        })
    
    return app

def main():
    """Funcția principală"""
    try:
        logger.info("🚀 Începere test minimal Render")
        
        # Creează aplicația
        app = create_minimal_app()
        
        # Configurează portul
        port = int(os.getenv('PORT', 10000))
        
        logger.info(f"📡 Pornire server pe portul {port}")
        
        # Pornește serverul
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False
        )
        
    except Exception as e:
        logger.error(f"❌ Eroare în test minimal: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()