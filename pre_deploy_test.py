#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de testare înainte de deployment pe Render
Verifică toate componentele și configurațiile necesare
"""

import os
import sys
import json
import requests
import subprocess
from pathlib import Path
from datetime import datetime

class PreDeployTester:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_tests = 0
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
        
    def print_result(self, test_name, success, message=""):
        self.total_tests += 1
        if success:
            self.success_count += 1
            print(f"✅ {test_name}")
            if message:
                print(f"   ℹ️  {message}")
        else:
            print(f"❌ {test_name}")
            if message:
                print(f"   ⚠️  {message}")
                self.errors.append(f"{test_name}: {message}")
                
    def print_warning(self, test_name, message):
        print(f"⚠️  {test_name}")
        print(f"   💡 {message}")
        self.warnings.append(f"{test_name}: {message}")
        
    def test_environment_setup(self):
        """Testează configurarea mediului local"""
        self.print_header("VERIFICARE MEDIU LOCAL")
        
        # Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            self.print_result("Python Version", True, f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            self.print_result("Python Version", False, f"Python {python_version.major}.{python_version.minor} - Necesită Python 3.8+")
            
        # .env file
        env_exists = os.path.exists('.env')
        if env_exists:
            self.print_result(".env File", True, "Fișier .env găsit pentru testare locală")
        else:
            self.print_warning(".env File", "Nu există .env - normal pentru deployment, dar necesar pentru testare locală")
            
        # .env.example
        env_example_exists = os.path.exists('.env.example')
        self.print_result(".env.example File", env_example_exists, "Template pentru variabile de mediu")
        
        # Git repository
        git_exists = os.path.exists('.git')
        self.print_result("Git Repository", git_exists, "Repository Git inițializat")
        
    def test_required_files(self):
        """Testează prezența fișierelor necesare"""
        self.print_header("VERIFICARE FIȘIERE NECESARE")
        
        required_files = {
            'app.py': 'Aplicația principală',
            'requirements.txt': 'Dependențe Python',
            'Dockerfile': 'Configurare Docker',
            'render.yaml': 'Configurare Render',
            'Procfile': 'Comandă de start pentru Render',
            '.gitignore': 'Excluderi Git'
        }
        
        for file_path, description in required_files.items():
            exists = os.path.exists(file_path)
            self.print_result(f"{file_path}", exists, description)
            
    def test_environment_variables(self):
        """Testează variabilele de mediu"""
        self.print_header("VERIFICARE VARIABILE DE MEDIU")
        
        # Load .env if exists
        if os.path.exists('.env'):
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if '=' in line and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
            except Exception as e:
                self.print_result("Load .env", False, f"Eroare la încărcarea .env: {e}")
                
        # Check mandatory variables
        mandatory_vars = {
            'TELEGRAM_BOT_TOKEN': 'Token bot Telegram',
            'WEBHOOK_URL': 'URL webhook pentru Render'
        }
        
        for var_name, description in mandatory_vars.items():
            value = os.getenv(var_name)
            if value:
                # Mask sensitive data
                masked_value = f"{value[:10]}..." if len(value) > 10 else "***"
                self.print_result(f"{var_name}", True, f"{description} - {masked_value}")
            else:
                self.print_warning(f"{var_name}", f"{description} - Nu este setat (normal pentru deployment)")
                
        # Check optional variables
        optional_vars = {
            'LOG_LEVEL': 'INFO',
            'MAX_FILE_SIZE_MB': '50',
            'DOWNLOAD_TIMEOUT': '300',
            'RATE_LIMIT_PER_MINUTE': '30'
        }
        
        for var_name, default_value in optional_vars.items():
            value = os.getenv(var_name, default_value)
            self.print_result(f"{var_name} (optional)", True, f"Valoare: {value}")
            
    def test_dependencies(self):
        """Testează dependențele Python"""
        self.print_header("VERIFICARE DEPENDENȚE PYTHON")
        
        try:
            with open('requirements.txt', 'r') as f:
                requirements = f.read().splitlines()
                
            essential_packages = [
                'flask',
                'python-telegram-bot',
                'yt-dlp',
                'requests'
            ]
            
            for package in essential_packages:
                found = any(package.lower() in req.lower() for req in requirements)
                self.print_result(f"Package: {package}", found, "Pachet esențial găsit în requirements.txt")
                
            self.print_result("Requirements.txt", True, f"Total {len(requirements)} pachete")
            
        except Exception as e:
            self.print_result("Requirements.txt", False, f"Eroare la citirea fișierului: {e}")
            
    def test_telegram_bot_token(self):
        """Testează token-ul Telegram"""
        self.print_header("VERIFICARE TOKEN TELEGRAM")
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            self.print_warning("Token Test", "TELEGRAM_BOT_TOKEN nu este setat - normal pentru deployment")
            return
            
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    username = bot_info.get('username', 'unknown')
                    self.print_result("Token Validation", True, f"Bot valid: @{username}")
                else:
                    self.print_result("Token Validation", False, "Token invalid")
            else:
                self.print_result("Token Validation", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.print_result("Token Validation", False, f"Eroare de conexiune: {e}")
            
    def test_security_checks(self):
        """Verificări de securitate"""
        self.print_header("VERIFICĂRI SECURITATE")
        
        # Check .env in .gitignore
        try:
            with open('.gitignore', 'r', encoding='utf-8') as f:
                gitignore_content = f.read()
                
            env_ignored = '.env' in gitignore_content
            self.print_result(".env în .gitignore", env_ignored, "Fișierul .env este exclus din Git")
            
        except Exception as e:
            self.print_result(".gitignore Check", False, f"Eroare la citirea .gitignore: {e}")
            
        # Check for hardcoded tokens in main files
        files_to_check = ['app.py', 'downloader.py']
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Look for potential hardcoded tokens (basic check)
                    suspicious_patterns = [
                        r'\d{8,}:[A-Za-z0-9_-]{35}',  # Telegram token pattern
                        'bot_token = "',
                        'TOKEN = "'
                    ]
                    
                    has_hardcoded = False
                    for pattern in suspicious_patterns:
                        if pattern in content and 'PLACEHOLDER' not in content:
                            has_hardcoded = True
                            break
                            
                    self.print_result(f"Hardcoded Tokens în {file_path}", not has_hardcoded, 
                                    "Fără token-uri hardcodate" if not has_hardcoded else "Posibile token-uri hardcodate")
                    
                except Exception as e:
                    self.print_result(f"Security Check {file_path}", False, f"Eroare: {e}")
                    
    def test_docker_config(self):
        """Testează configurația Docker"""
        self.print_header("VERIFICARE CONFIGURAȚIE DOCKER")
        
        # Check Dockerfile
        if os.path.exists('Dockerfile'):
            try:
                with open('Dockerfile', 'r') as f:
                    dockerfile_content = f.read()
                    
                # Check for security best practices
                has_non_root = 'USER app' in dockerfile_content or 'USER ' in dockerfile_content
                self.print_result("Non-root User", has_non_root, "Dockerfile folosește utilizator non-root")
                
                has_healthcheck = 'HEALTHCHECK' in dockerfile_content
                self.print_result("Health Check", has_healthcheck, "Dockerfile include verificare sănătate")
                
                has_python = 'python:' in dockerfile_content
                self.print_result("Python Base Image", has_python, "Folosește imagine Python oficială")
                
            except Exception as e:
                self.print_result("Dockerfile Analysis", False, f"Eroare: {e}")
        else:
            self.print_result("Dockerfile", False, "Dockerfile nu există")
            
    def generate_report(self):
        """Generează raportul final"""
        self.print_header("RAPORT FINAL")
        
        success_rate = (self.success_count / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"📊 Statistici:")
        print(f"   ✅ Teste reușite: {self.success_count}/{self.total_tests} ({success_rate:.1f}%)")
        print(f"   ⚠️  Avertismente: {len(self.warnings)}")
        print(f"   ❌ Erori: {len(self.errors)}")
        
        if self.errors:
            print(f"\n❌ ERORI CRITICE:")
            for error in self.errors:
                print(f"   • {error}")
                
        if self.warnings:
            print(f"\n⚠️  AVERTISMENTE:")
            for warning in self.warnings:
                print(f"   • {warning}")
                
        print(f"\n🎯 STATUS DEPLOYMENT:")
        if len(self.errors) == 0:
            print(f"   🟢 GATA PENTRU DEPLOYMENT")
            print(f"   💡 Urmează pașii din RENDER_DEPLOYMENT_GUIDE.md")
        else:
            print(f"   🔴 NU ESTE GATA PENTRU DEPLOYMENT")
            print(f"   🔧 Rezolvă erorile critice mai întâi")
            
        # Save report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': self.total_tests,
            'success_count': self.success_count,
            'success_rate': success_rate,
            'errors': self.errors,
            'warnings': self.warnings,
            'ready_for_deployment': len(self.errors) == 0
        }
        
        with open('pre_deploy_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\n📄 Raport salvat în: pre_deploy_test_report.json")
        
    def run_all_tests(self):
        """Rulează toate testele"""
        print(f"🚀 TESTARE PRE-DEPLOYMENT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Director: {os.getcwd()}")
        
        self.test_environment_setup()
        self.test_required_files()
        self.test_environment_variables()
        self.test_dependencies()
        self.test_telegram_bot_token()
        self.test_security_checks()
        self.test_docker_config()
        
        self.generate_report()
        
def main():
    """Funcția principală"""
    tester = PreDeployTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test întrerupt de utilizator")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Eroare critică în timpul testării: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()