#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checklist final pentru deployment pe Render
Verifică toate cerințele și configurațiile
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

class DeploymentChecker:
    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []
        
    def add_check(self, name, status, message="", critical=False):
        """Adaugă o verificare la listă"""
        check = {
            'name': name,
            'status': status,
            'message': message,
            'critical': critical,
            'timestamp': datetime.now().isoformat()
        }
        self.checks.append(check)
        
        if not status and critical:
            self.errors.append(f"{name}: {message}")
        elif not status:
            self.warnings.append(f"{name}: {message}")
            
    def print_check(self, name, status, message="", critical=False):
        """Afișează rezultatul unei verificări"""
        icon = "✅" if status else ("❌" if critical else "⚠️")
        print(f"{icon} {name}")
        if message:
            print(f"   💬 {message}")
        self.add_check(name, status, message, critical)
        
    def check_required_files(self):
        """Verifică fișierele necesare pentru deployment"""
        print("\n📁 VERIFICARE FIȘIERE NECESARE")
        print("="*50)
        
        required_files = {
            'app.py': {'critical': True, 'desc': 'Aplicația principală'},
            'requirements.txt': {'critical': True, 'desc': 'Dependențe Python'},
            'Procfile': {'critical': True, 'desc': 'Comandă start pentru Render'},
            'render.yaml': {'critical': False, 'desc': 'Configurare Render (opțional)'},
            'Dockerfile': {'critical': False, 'desc': 'Configurare Docker (opțional)'},
            '.gitignore': {'critical': True, 'desc': 'Excluderi Git'},
            '.env.example': {'critical': True, 'desc': 'Template variabile de mediu'}
        }
        
        for filename, config in required_files.items():
            exists = os.path.exists(filename)
            self.print_check(
                f"Fișier: {filename}",
                exists,
                config['desc'] if exists else f"Lipsește: {config['desc']}",
                config['critical']
            )
            
    def check_git_repository(self):
        """Verifică configurația Git"""
        print("\n🔧 VERIFICARE GIT REPOSITORY")
        print("="*50)
        
        # Check if git is initialized
        git_exists = os.path.exists('.git')
        self.print_check(
            "Git Repository",
            git_exists,
            "Repository Git inițializat" if git_exists else "Git nu este inițializat",
            True
        )
        
        if git_exists:
            try:
                # Check git status
                result = subprocess.run(['git', 'status', '--porcelain'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    uncommitted = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                    self.print_check(
                        "Git Status",
                        uncommitted == 0,
                        f"Repository curat" if uncommitted == 0 else f"{uncommitted} fișiere necommitate",
                        False
                    )
                    
                # Check remote
                result = subprocess.run(['git', 'remote', '-v'], 
                                      capture_output=True, text=True, timeout=10)
                has_remote = 'origin' in result.stdout if result.returncode == 0 else False
                self.print_check(
                    "Git Remote",
                    has_remote,
                    "Remote origin configurat" if has_remote else "Remote origin nu este configurat",
                    True
                )
                
            except Exception as e:
                self.print_check("Git Commands", False, f"Eroare la verificarea Git: {e}", False)
                
    def check_security_config(self):
        """Verifică configurația de securitate"""
        print("\n🔒 VERIFICARE SECURITATE")
        print("="*50)
        
        # Check .env in .gitignore
        gitignore_ok = False
        if os.path.exists('.gitignore'):
            try:
                with open('.gitignore', 'r', encoding='utf-8') as f:
                    content = f.read()
                gitignore_ok = '.env' in content
            except Exception:
                pass
                
        self.print_check(
            ".env în .gitignore",
            gitignore_ok,
            "Fișierul .env este exclus din Git" if gitignore_ok else "PERICOL: .env nu este exclus din Git!",
            True
        )
        
        # Check that .env is not in repository
        env_not_tracked = True
        if os.path.exists('.env'):
            try:
                result = subprocess.run(['git', 'ls-files', '.env'], 
                                      capture_output=True, text=True, timeout=5)
                env_not_tracked = result.returncode != 0 or not result.stdout.strip()
            except Exception:
                pass
                
        self.print_check(
            ".env nu este în Git",
            env_not_tracked,
            "Fișierul .env nu este tracked în Git" if env_not_tracked else "PERICOL: .env este în Git!",
            True
        )
        
        # Check for hardcoded secrets in main files
        files_to_scan = ['app.py', 'downloader.py']
        for filename in files_to_scan:
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for actual hardcoded tokens (not placeholders)
                    import re
                    token_pattern = r'\d{8,}:[A-Za-z0-9_-]{35}'
                    has_secrets = bool(re.search(token_pattern, content)) and 'PLACEHOLDER' not in content.upper()
                    
                    self.print_check(
                        f"Secrete în {filename}",
                        not has_secrets,
                        "Fără secrete hardcodate" if not has_secrets else "Posibile secrete hardcodate",
                        True
                    )
                except Exception as e:
                    self.print_check(f"Scanare {filename}", False, f"Eroare: {e}", False)
                    
    def check_render_config(self):
        """Verifică configurația pentru Render"""
        print("\n🚀 VERIFICARE CONFIGURAȚIE RENDER")
        print("="*50)
        
        # Check Procfile
        procfile_ok = False
        if os.path.exists('Procfile'):
            try:
                with open('Procfile', 'r') as f:
                    content = f.read().strip()
                procfile_ok = content.startswith('web:') and 'python' in content
            except Exception:
                pass
                
        self.print_check(
            "Procfile Valid",
            procfile_ok,
            "Procfile conține comandă web validă" if procfile_ok else "Procfile invalid sau lipsește",
            True
        )
        
        # Check render.yaml
        render_yaml_ok = False
        if os.path.exists('render.yaml'):
            try:
                with open('render.yaml', 'r') as f:
                    content = f.read()
                render_yaml_ok = 'services:' in content and 'web' in content
            except Exception:
                pass
                
        self.print_check(
            "render.yaml Valid",
            render_yaml_ok,
            "render.yaml conține configurație validă" if render_yaml_ok else "render.yaml invalid sau lipsește",
            False
        )
        
        # Check requirements.txt
        requirements_ok = False
        essential_packages = ['flask', 'python-telegram-bot', 'yt-dlp', 'requests']
        
        if os.path.exists('requirements.txt'):
            try:
                with open('requirements.txt', 'r') as f:
                    content = f.read().lower()
                missing_packages = [pkg for pkg in essential_packages if pkg not in content]
                requirements_ok = len(missing_packages) == 0
                
                self.print_check(
                    "Requirements.txt Complete",
                    requirements_ok,
                    "Toate pachetele esențiale sunt prezente" if requirements_ok else f"Lipsesc: {', '.join(missing_packages)}",
                    True
                )
            except Exception as e:
                self.print_check("Requirements.txt", False, f"Eroare la citire: {e}", True)
        else:
            self.print_check("Requirements.txt", False, "Fișierul requirements.txt lipsește", True)
            
    def check_environment_template(self):
        """Verifică template-ul de variabile de mediu"""
        print("\n🌍 VERIFICARE TEMPLATE VARIABILE DE MEDIU")
        print("="*50)
        
        if os.path.exists('.env.example'):
            try:
                with open('.env.example', 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                required_vars = ['TELEGRAM_BOT_TOKEN', 'WEBHOOK_URL']
                optional_vars = ['LOG_LEVEL', 'MAX_FILE_SIZE_MB', 'DOWNLOAD_TIMEOUT']
                
                for var in required_vars:
                    has_var = var in content
                    self.print_check(
                        f"Variabilă: {var}",
                        has_var,
                        "Prezentă în template" if has_var else "Lipsește din template",
                        True
                    )
                    
                for var in optional_vars:
                    has_var = var in content
                    self.print_check(
                        f"Variabilă opțională: {var}",
                        has_var,
                        "Prezentă în template" if has_var else "Lipsește din template",
                        False
                    )
                    
            except Exception as e:
                self.print_check(".env.example", False, f"Eroare la citire: {e}", True)
        else:
            self.print_check(".env.example", False, "Fișierul .env.example lipsește", True)
            
    def generate_final_report(self):
        """Generează raportul final"""
        print("\n📊 RAPORT FINAL DEPLOYMENT")
        print("="*50)
        
        total_checks = len(self.checks)
        passed_checks = len([c for c in self.checks if c['status']])
        critical_errors = len(self.errors)
        warnings_count = len(self.warnings)
        
        print(f"\n📈 Statistici:")
        print(f"   ✅ Verificări reușite: {passed_checks}/{total_checks}")
        print(f"   ❌ Erori critice: {critical_errors}")
        print(f"   ⚠️  Avertismente: {warnings_count}")
        
        if critical_errors > 0:
            print(f"\n❌ ERORI CRITICE (trebuie rezolvate):")
            for error in self.errors:
                print(f"   • {error}")
                
        if warnings_count > 0:
            print(f"\n⚠️  AVERTISMENTE (recomandate):")
            for warning in self.warnings:
                print(f"   • {warning}")
                
        # Final verdict
        ready_for_deployment = critical_errors == 0
        
        print(f"\n🎯 VERDICT FINAL:")
        if ready_for_deployment:
            print(f"   🟢 GATA PENTRU DEPLOYMENT PE RENDER!")
            print(f"\n📋 Următorii pași:")
            print(f"   1. Rulează: python render_env_setup.py")
            print(f"   2. Urmează: RENDER_DEPLOYMENT_GUIDE.md")
            print(f"   3. Testează: python pre_deploy_test.py")
        else:
            print(f"   🔴 NU ESTE GATA PENTRU DEPLOYMENT")
            print(f"   🔧 Rezolvă erorile critice mai întâi")
            
        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'ready_for_deployment': ready_for_deployment,
            'statistics': {
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'critical_errors': critical_errors,
                'warnings': warnings_count
            },
            'checks': self.checks,
            'errors': self.errors,
            'warnings': self.warnings
        }
        
        try:
            with open('deployment_checklist_report.json', 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\n💾 Raport detaliat salvat în: deployment_checklist_report.json")
        except Exception as e:
            print(f"\n❌ Eroare la salvarea raportului: {e}")
            
        return ready_for_deployment
        
    def run_all_checks(self):
        """Rulează toate verificările"""
        print("🔍 CHECKLIST FINAL DEPLOYMENT PE RENDER")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Director: {os.getcwd()}")
        print("="*60)
        
        self.check_required_files()
        self.check_git_repository()
        self.check_security_config()
        self.check_render_config()
        self.check_environment_template()
        
        return self.generate_final_report()
        
def main():
    """Funcția principală"""
    checker = DeploymentChecker()
    
    try:
        ready = checker.run_all_checks()
        sys.exit(0 if ready else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Verificare întreruptă de utilizator")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Eroare critică în timpul verificării: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    import sys
    main()