#!/usr/bin/env python3
# Aplicație ultra-simplă pentru Render

import os
from flask import Flask, jsonify

app = Flask(__name__)
PORT = int(os.getenv('PORT', 10000))

@app.route('/')
def home():
    return jsonify({'status': 'OK', 'message': 'Bot is running'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    return jsonify({'status': 'webhook_ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)