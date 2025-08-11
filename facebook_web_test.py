#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Web Test Interface
Interfață web pentru testarea și debugging Facebook
"""

from flask import Flask, render_template_string, request, jsonify
import logging
import sys
import os
import tempfile
import yt_dlp
from datetime import datetime
import json
import traceback

# Configurare logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import modulele locale
try:
    from facebook_fix_patch import (
        enhanced_facebook_extractor_args,
        normalize_facebook_share_url,
        create_robust_facebook_opts,
        generate_facebook_url_variants,
        try_facebook_with_rotation
    )
    logger.info("✅ Facebook fix patch loaded successfully")
except ImportError as e:
    logger.error(f"❌ Nu s-a putut încărca facebook_fix_patch: {e}")
    sys.exit(1)

app = Flask(__name__)

# Template HTML pentru interfața web
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook Debug Test Interface</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            color: #4267B2;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .test-section {
            margin: 30px 0;
            padding: 20px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            background: #f8f9fa;
        }
        .test-section h3 {
            color: #4267B2;
            margin-top: 0;
            font-size: 1.3em;
        }
        input[type="url"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            margin: 10px 0;
        }
        button {
            background: #4267B2;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
            transition: background 0.3s;
        }
        button:hover {
            background: #365899;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin: 20px 0;
            padding: 15px;
            border-radius: 8px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-height: 400px;
            overflow-y: auto;
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .loading {
            text-align: center;
            color: #4267B2;
            font-style: italic;
        }
        .url-variants {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #dee2e6;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4267B2;
        }
        .stat-label {
            color: #6c757d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 Facebook Debug Test Interface</h1>
        
        <div class="test-section">
            <h3>📝 Test URL Facebook</h3>
            <input type="url" id="testUrl" placeholder="Introdu URL Facebook (ex: https://www.facebook.com/share/v/...)" />
            <div>
                <button onclick="testNormalization()">🔧 Test Normalizare</button>
                <button onclick="testExtraction()">📋 Test Extragere Info</button>
                <button onclick="testRotation()">🔄 Test Rotație</button>
                <button onclick="testDownload()">💾 Test Descărcare</button>
                <button onclick="runAllTests()">🚀 Toate Testele</button>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalTests">0</div>
                <div class="stat-label">Teste Rulate</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="successTests">0</div>
                <div class="stat-label">Teste Reușite</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="failedTests">0</div>
                <div class="stat-label">Teste Eșuate</div>
            </div>
        </div>
        
        <div id="results"></div>
    </div>
    
    <script>
        let totalTests = 0;
        let successTests = 0;
        let failedTests = 0;
        
        function updateStats() {
            document.getElementById('totalTests').textContent = totalTests;
            document.getElementById('successTests').textContent = successTests;
            document.getElementById('failedTests').textContent = failedTests;
        }
        
        function addResult(title, content, type = 'info') {
            const resultsDiv = document.getElementById('results');
            const resultDiv = document.createElement('div');
            resultDiv.className = `result ${type}`;
            resultDiv.innerHTML = `<strong>${title}</strong>\n${content}`;
            resultsDiv.appendChild(resultDiv);
            resultsDiv.scrollTop = resultsDiv.scrollHeight;
        }
        
        function showLoading(message) {
            addResult('⏳ Loading...', message, 'loading');
        }
        
        async function makeRequest(endpoint, data) {
            totalTests++;
            updateStats();
            
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    successTests++;
                    addResult(result.title, result.content, 'success');
                } else {
                    failedTests++;
                    addResult(result.title, result.content, 'error');
                }
                
                updateStats();
                return result;
            } catch (error) {
                failedTests++;
                addResult('❌ Eroare de rețea', error.message, 'error');
                updateStats();
                return { success: false, error: error.message };
            }
        }
        
        function getTestUrl() {
            const url = document.getElementById('testUrl').value.trim();
            if (!url) {
                alert('Te rog să introduci un URL Facebook!');
                return null;
            }
            return url;
        }
        
        async function testNormalization() {
            const url = getTestUrl();
            if (!url) return;
            
            showLoading('Testez normalizarea URL-ului...');
            await makeRequest('/test_normalization', { url });
        }
        
        async function testExtraction() {
            const url = getTestUrl();
            if (!url) return;
            
            showLoading('Testez extragerea informațiilor...');
            await makeRequest('/test_extraction', { url });
        }
        
        async function testRotation() {
            const url = getTestUrl();
            if (!url) return;
            
            showLoading('Testez sistemul de rotație...');
            await makeRequest('/test_rotation', { url });
        }
        
        async function testDownload() {
            const url = getTestUrl();
            if (!url) return;
            
            showLoading('Testez simularea descărcării...');
            await makeRequest('/test_download', { url });
        }
        
        async function runAllTests() {
            const url = getTestUrl();
            if (!url) return;
            
            addResult('🚀 Începe toate testele', `URL: ${url}`, 'info');
            
            await testNormalization();
            await testExtraction();
            await testRotation();
            await testDownload();
            
            addResult('✅ Toate testele complete', 'Verifică rezultatele de mai sus', 'success');
        }
        
        // Auto-focus pe input
        document.getElementById('testUrl').focus();
        
        // Enter key pentru a rula toate testele
        document.getElementById('testUrl').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                runAllTests();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/test_normalization', methods=['POST'])
def test_normalization():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'title': '❌ Test Normalizare',
                'content': 'URL-ul este gol!'
            })
        
        # Test normalizare
        normalized = normalize_facebook_share_url(url)
        variants = generate_facebook_url_variants(normalized)
        
        result_content = f"URL Original: {url}\n"
        result_content += f"URL Normalizat: {normalized}\n\n"
        result_content += f"Variante generate: {len(variants)}\n"
        
        for i, variant in enumerate(variants, 1):
            result_content += f"{i}. {variant}\n"
        
        return jsonify({
            'success': True,
            'title': '✅ Test Normalizare Reușit',
            'content': result_content
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'title': '❌ Eroare Test Normalizare',
            'content': f"Eroare: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        })

@app.route('/test_extraction', methods=['POST'])
def test_extraction():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'title': '❌ Test Extragere',
                'content': 'URL-ul este gol!'
            })
        
        # Test extragere cu configurație robustă
        opts = create_robust_facebook_opts()
        opts['skip_download'] = True
        opts['quiet'] = False
        
        result_content = f"URL: {url}\n\n"
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    result_content += "✅ EXTRAGERE REUȘITĂ!\n\n"
                    result_content += f"Titlu: {info.get('title', 'N/A')}\n"
                    result_content += f"Durată: {info.get('duration', 'N/A')} secunde\n"
                    result_content += f"Uploader: {info.get('uploader', 'N/A')}\n"
                    result_content += f"Descriere: {info.get('description', 'N/A')[:100]}...\n"
                    result_content += f"Formate disponibile: {len(info.get('formats', []))}\n"
                    
                    # Afișează primele 3 formate
                    formats = info.get('formats', [])
                    if formats:
                        result_content += "\nPrimele formate:\n"
                        for i, fmt in enumerate(formats[:3], 1):
                            result_content += f"{i}. {fmt.get('format_id', 'N/A')} - {fmt.get('ext', 'N/A')} - {fmt.get('resolution', 'N/A')}\n"
                    
                    return jsonify({
                        'success': True,
                        'title': '✅ Test Extragere Reușit',
                        'content': result_content
                    })
                else:
                    return jsonify({
                        'success': False,
                        'title': '❌ Test Extragere Eșuat',
                        'content': result_content + "Nu s-au putut extrage informații!"
                    })
                    
        except Exception as extract_error:
            error_msg = str(extract_error)
            result_content += f"❌ EROARE LA EXTRAGERE: {error_msg}\n\n"
            
            # Analizează tipul de eroare
            if 'Cannot parse data' in error_msg:
                result_content += "🔍 DIAGNOSTICARE: Cannot parse data error\n"
                result_content += "Cauze posibile:\n"
                result_content += "- URL în format nou nesuportat\n"
                result_content += "- Conținut cu caractere speciale\n"
                result_content += "- Probleme temporare Facebook API\n"
            elif 'private' in error_msg.lower():
                result_content += "🔒 DIAGNOSTICARE: Conținut privat\n"
            elif 'not available' in error_msg.lower():
                result_content += "📵 DIAGNOSTICARE: Conținut indisponibil\n"
            
            return jsonify({
                'success': False,
                'title': '❌ Test Extragere Eșuat',
                'content': result_content
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'title': '❌ Eroare Test Extragere',
            'content': f"Eroare: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        })

@app.route('/test_rotation', methods=['POST'])
def test_rotation():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'title': '❌ Test Rotație',
                'content': 'URL-ul este gol!'
            })
        
        # Test rotație
        opts = create_robust_facebook_opts()
        opts['skip_download'] = True
        
        result_content = f"URL: {url}\n\n"
        result_content += "🔄 Începe testul de rotație...\n\n"
        
        success_url, info, rotation_info = try_facebook_with_rotation(
            url, opts, max_attempts=4
        )
        
        if success_url and info:
            result_content += "✅ ROTAȚIE REUȘITĂ!\n\n"
            result_content += f"URL reușit: {success_url}\n"
            result_content += f"Format reușit: {rotation_info.get('successful_format', 'N/A')}\n"
            result_content += f"Încercare: {rotation_info.get('attempt_number', 'N/A')}\n"
            result_content += f"Formate încercate: {rotation_info.get('attempted_formats', [])}\n\n"
            result_content += f"Video găsit: {info.get('title', 'N/A')}\n"
            result_content += f"Durată: {info.get('duration', 'N/A')} secunde\n"
            
            return jsonify({
                'success': True,
                'title': '✅ Test Rotație Reușit',
                'content': result_content
            })
        else:
            result_content += "❌ ROTAȚIE EȘUATĂ!\n\n"
            if rotation_info:
                result_content += f"Tip eroare: {rotation_info.get('error_type', 'N/A')}\n"
                result_content += f"Formate încercate: {rotation_info.get('attempted_formats', [])}\n"
                result_content += f"Încercări totale: {rotation_info.get('total_attempts', 'N/A')}\n"
                if rotation_info.get('error_message'):
                    result_content += f"Ultima eroare: {rotation_info['error_message']}\n"
            
            return jsonify({
                'success': False,
                'title': '❌ Test Rotație Eșuat',
                'content': result_content
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'title': '❌ Eroare Test Rotație',
            'content': f"Eroare: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        })

@app.route('/test_download', methods=['POST'])
def test_download():
    try:
        data = request.get_json()
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'title': '❌ Test Descărcare',
                'content': 'URL-ul este gol!'
            })
        
        # Test simulare descărcare
        with tempfile.TemporaryDirectory() as temp_dir:
            opts = create_robust_facebook_opts()
            opts.update({
                'outtmpl': os.path.join(temp_dir, '%(title).50s.%(ext)s'),
                'skip_download': False,
                'test': True,  # Simulare - nu descarcă efectiv
                'quiet': False
            })
            
            result_content = f"URL: {url}\n"
            result_content += f"Director temporar: {temp_dir}\n\n"
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                    result_content += "✅ SIMULARE DESCĂRCARE REUȘITĂ!\n"
                    result_content += "Videoul poate fi descărcat cu succes.\n"
                    
                    return jsonify({
                        'success': True,
                        'title': '✅ Test Descărcare Reușit',
                        'content': result_content
                    })
                    
            except Exception as download_error:
                error_msg = str(download_error)
                result_content += f"❌ SIMULARE EȘUATĂ: {error_msg}\n\n"
                
                # Încearcă cu rotația
                result_content += "🔄 Încerc cu sistemul de rotație...\n"
                
                try:
                    rotation_opts = opts.copy()
                    rotation_opts['skip_download'] = True
                    
                    success_url, info, rotation_info = try_facebook_with_rotation(
                        url, rotation_opts, max_attempts=3
                    )
                    
                    if success_url:
                        result_content += f"✅ ROTAȚIA A GĂSIT URL FUNCȚIONAL!\n"
                        result_content += f"Format reușit: {rotation_info.get('successful_format', 'N/A')}\n"
                        result_content += f"URL funcțional: {success_url}\n"
                        
                        return jsonify({
                            'success': True,
                            'title': '✅ Test Descărcare Reușit (cu Rotație)',
                            'content': result_content
                        })
                    else:
                        result_content += "❌ ROTAȚIA A EȘUAT COMPLET\n"
                        if rotation_info:
                            result_content += f"Formate încercate: {rotation_info.get('attempted_formats', [])}\n"
                        
                        return jsonify({
                            'success': False,
                            'title': '❌ Test Descărcare Eșuat',
                            'content': result_content
                        })
                        
                except Exception as rotation_error:
                    result_content += f"❌ EROARE ÎN ROTAȚIE: {str(rotation_error)}\n"
                    
                    return jsonify({
                        'success': False,
                        'title': '❌ Test Descărcare Eșuat',
                        'content': result_content
                    })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'title': '❌ Eroare Test Descărcare',
            'content': f"Eroare: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        })

if __name__ == '__main__':
    print("🚀 Pornesc Facebook Web Test Interface...")
    print("📱 Accesează: http://localhost:5001")
    print("🔧 Pentru debugging Facebook în timp real")
    print("⏹️  Apasă Ctrl+C pentru a opri")
    
    app.run(host='0.0.0.0', port=5001, debug=True)