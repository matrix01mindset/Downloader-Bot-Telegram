#!/usr/bin/env python3
"""
🚀 SECURE DEPLOYMENT SCRIPT - Telegram Video Downloader Bot
Versiunea: 3.0.0
Data: 2025-01-06

Script pentru deployment securizat care verifică și configurează
toate aspectele de securitate înainte de publicare.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import argparse
from datetime import datetime

# Import local utilities
try:
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.secrets_manager import get_secrets_manager, validate_required_secrets
    from scripts.security_check import SecurityChecker
except ImportError:
    print("⚠️  Warning: Could not import some utilities. Running in standalone mode.")

class SecureDeployment:
    """
    Manager pentru deployment securizat al botului.
    
    Caracteristici:
    - Verificări de securitate comprehensive
    - Configurare automatizată a secretelor
    - Validare configurații deployment
    - Cleanup automat de fișiere sensibile
    - Documentare pas cu pas
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.deployment_config = {}
        self.issues_found = []
        
        # Platforms suportate pentru deployment
        self.supported_platforms = {
            'render': {
                'name': 'Render',
                'webhook_format': 'https://{app_name}.onrender.com',
                'env_vars_method': 'dashboard',
                'docs': 'https://render.com/docs/environment-variables'
            },
            'railway': {
                'name': 'Railway', 
                'webhook_format': 'https://{app_name}.up.railway.app',
                'env_vars_method': 'dashboard',
                'docs': 'https://docs.railway.app/deploy/variables'
            },
            'heroku': {
                'name': 'Heroku',
                'webhook_format': 'https://{app_name}.herokuapp.com', 
                'env_vars_method': 'cli_or_dashboard',
                'docs': 'https://devcenter.heroku.com/articles/config-vars'
            },
            'fly': {
                'name': 'Fly.io',
                'webhook_format': 'https://{app_name}.fly.dev',
                'env_vars_method': 'fly_secrets',
                'docs': 'https://fly.io/docs/reference/secrets/'
            },
            'vercel': {
                'name': 'Vercel',
                'webhook_format': 'https://{app_name}.vercel.app',
                'env_vars_method': 'dashboard',
                'docs': 'https://vercel.com/docs/concepts/projects/environment-variables'
            }
        }
    
    def run_deployment_check(self, platform: str = None) -> bool:
        """
        Rulează verificarea completă pentru deployment.
        
        Args:
            platform: Platforma de hosting (render, railway, etc.)
            
        Returns:
            True dacă toate verificările au trecut
        """
        print("🚀 Starting secure deployment check...\n")
        
        success = True
        
        # 1. Verificări de securitate
        print("🛡️  Step 1: Security checks")
        if not self._run_security_checks():
            success = False
        
        # 2. Validarea secretelor
        print("\n🔐 Step 2: Secrets validation") 
        if not self._validate_secrets():
            success = False
        
        # 3. Verificarea configurațiilor
        print("\n⚙️  Step 3: Configuration validation")
        if not self._validate_configuration():
            success = False
        
        # 4. Verificarea dependințelor
        print("\n📦 Step 4: Dependencies check")
        if not self._check_dependencies():
            success = False
        
        # 5. Pregătirea fișierelor pentru deployment
        print("\n📁 Step 5: Deployment preparation")
        if not self._prepare_deployment_files(platform):
            success = False
        
        # 6. Generarea documentației de deployment
        print("\n📋 Step 6: Generate deployment guide")
        self._generate_deployment_guide(platform)
        
        return success
    
    def _run_security_checks(self) -> bool:
        """Rulează verificările de securitate."""
        try:
            # Import și rulează security checker
            checker = SecurityChecker(str(self.project_root))
            
            # Auto-fix problemele simple
            if checker.auto_fix():
                print("✅ Auto-fixed some security issues")
            
            # Scanează pentru probleme
            issues = checker.scan_project()
            
            # Verifică rezultatele
            critical_issues = [i for i in issues if i.get('severity') == 'CRITICAL']
            high_issues = [i for i in issues if i.get('severity') == 'HIGH']
            
            if critical_issues:
                print(f"❌ Found {len(critical_issues)} CRITICAL security issues:")
                for issue in critical_issues:
                    print(f"   - {issue.get('description', 'Unknown issue')}")
                print("\n🚨 CRITICAL issues must be fixed before deployment!")
                return False
            
            if high_issues:
                print(f"⚠️  Found {len(high_issues)} HIGH security issues:")
                for issue in high_issues:
                    print(f"   - {issue.get('description', 'Unknown issue')}")
                
                response = input("\n❓ Continue deployment with HIGH issues? (y/N): ")
                if response.lower() != 'y':
                    return False
            
            print("✅ Security checks passed")
            return True
            
        except Exception as e:
            print(f"❌ Security check failed: {e}")
            return False
    
    def _validate_secrets(self) -> bool:
        """Validează că toate secretele necesare sunt configurate."""
        try:
            # Verifică secretele necesare
            validation_results = validate_required_secrets()
            
            missing_secrets = [name for name, valid in validation_results.items() if not valid]
            
            if missing_secrets:
                print(f"❌ Missing required secrets: {', '.join(missing_secrets)}")
                print(f"📋 Please configure these in your .env file or environment variables")
                print(f"📄 Use .env.template as reference")
                return False
            
            print("✅ All required secrets are configured")
            return True
            
        except Exception as e:
            print(f"❌ Secrets validation failed: {e}")
            return False
    
    def _validate_configuration(self) -> bool:
        """Validează configurația aplicației."""
        try:
            config_file = self.project_root / 'config.yaml'
            
            if not config_file.exists():
                print("❌ config.yaml not found")
                return False
            
            # Citește și validează config.yaml
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Verificări de bază
            required_sections = ['app', 'server', 'telegram', 'platforms']
            missing_sections = [section for section in required_sections if section not in config]
            
            if missing_sections:
                print(f"❌ Missing config sections: {', '.join(missing_sections)}")
                return False
            
            # Verifică că token-urile folosesc variabile de mediu
            telegram_config = config.get('telegram', {})
            token = telegram_config.get('token', '')
            webhook_url = telegram_config.get('webhook_url', '')
            
            if not token.startswith('${'):
                print("❌ Telegram token should use environment variable: ${TELEGRAM_BOT_TOKEN}")
                return False
            
            if webhook_url and not webhook_url.startswith('${'):
                print("❌ Webhook URL should use environment variable: ${WEBHOOK_URL}")
                return False
            
            print("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
    
    def _check_dependencies(self) -> bool:
        """Verifică dependințele proiectului."""
        try:
            requirements_file = self.project_root / 'requirements.txt'
            
            if not requirements_file.exists():
                print("❌ requirements.txt not found")
                return False
            
            # Verifică că fișierul nu este gol
            with open(requirements_file, 'r') as f:
                content = f.read().strip()
            
            if not content:
                print("❌ requirements.txt is empty")
                return False
            
            # Verifică dependințele critice
            critical_deps = ['python-telegram-bot', 'yt-dlp', 'fastapi', 'uvicorn']
            missing_deps = []
            
            for dep in critical_deps:
                if dep not in content:
                    missing_deps.append(dep)
            
            if missing_deps:
                print(f"⚠️  Missing critical dependencies: {', '.join(missing_deps)}")
                print("📋 These might be required for full functionality")
            
            print("✅ Dependencies check passed")
            return True
            
        except Exception as e:
            print(f"❌ Dependencies check failed: {e}")
            return False
    
    def _prepare_deployment_files(self, platform: str) -> bool:
        """Pregătește fișierele pentru deployment."""
        try:
            # Verifică și creează fișierele necesare pentru deployment
            
            # 1. Dockerfile (dacă nu există)
            dockerfile_path = self.project_root / 'Dockerfile'
            if not dockerfile_path.exists():
                self._create_dockerfile()
                print("✅ Created Dockerfile")
            
            # 2. .dockerignore
            dockerignore_path = self.project_root / '.dockerignore'
            if not dockerignore_path.exists():
                self._create_dockerignore()
                print("✅ Created .dockerignore")
            
            # 3. Fișiere specifice platformei
            if platform:
                if platform == 'render':
                    self._create_render_yaml()
                    print("✅ Created render.yaml")
                elif platform == 'railway':
                    self._create_railway_json()
                    print("✅ Created railway.json")
                elif platform == 'heroku':
                    self._create_procfile()
                    print("✅ Created Procfile")
            
            # 4. Verifică că fișierele sensibile sunt excluse
            sensitive_files = ['.env', 'secrets/', '*.key', '*.token']
            gitignore_path = self.project_root / '.gitignore'
            
            if gitignore_path.exists():
                with open(gitignore_path, 'r') as f:
                    gitignore_content = f.read()
                
                for pattern in sensitive_files:
                    if pattern not in gitignore_content:
                        print(f"⚠️  {pattern} should be in .gitignore")
            
            print("✅ Deployment files prepared")
            return True
            
        except Exception as e:
            print(f"❌ Deployment preparation failed: {e}")
            return False
    
    def _create_dockerfile(self):
        """Creează un Dockerfile optimizat pentru producție."""
        dockerfile_content = '''# 🐳 Dockerfile pentru Telegram Video Downloader Bot
FROM python:3.11-slim

# Setează directorul de lucru
WORKDIR /app

# Instalează dependințele sistem necesare
RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    wget \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copiază requirements și instalează dependințele Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiază codul aplicației
COPY . .

# Creează un utilizator non-root pentru securitate
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Setează variabilele de mediu
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expune portul
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Comandă de start
CMD ["python", "main.py"]
'''
        
        with open(self.project_root / 'Dockerfile', 'w') as f:
            f.write(dockerfile_content)
    
    def _create_dockerignore(self):
        """Creează .dockerignore pentru a exclude fișierele sensibile."""
        dockerignore_content = '''# Fișiere sensibile - NU include în imagine
.env*
!.env.template
secrets/
*.key
*.token
*.pem

# Dezvoltare
.git/
.gitignore
README.md
*.md
.vscode/
.idea/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/

# Teste
test_*
tests/
*.test.py

# Logs
*.log
logs/

# Temporare
temp/
tmp/
*.tmp
*.cache

# Node modules (dacă există)
node_modules/

# OS files
.DS_Store
Thumbs.db
'''
        
        with open(self.project_root / '.dockerignore', 'w') as f:
            f.write(dockerignore_content)
    
    def _create_render_yaml(self):
        """Creează fișierul render.yaml pentru Render."""
        render_config = '''# 🚀 Render Deployment Configuration
services:
  - type: web
    name: telegram-video-downloader-bot
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: PORT
        value: "5000"
    healthCheckPath: /health
'''
        
        with open(self.project_root / 'render.yaml', 'w') as f:
            f.write(render_config)
    
    def _create_railway_json(self):
        """Creează fișierul railway.json pentru Railway."""
        railway_config = {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "DOCKERFILE"
            },
            "deploy": {
                "healthcheckPath": "/health",
                "healthcheckTimeout": 30
            }
        }
        
        with open(self.project_root / 'railway.json', 'w') as f:
            json.dump(railway_config, f, indent=2)
    
    def _create_procfile(self):
        """Creează Procfile pentru Heroku."""
        procfile_content = 'web: python main.py'
        
        with open(self.project_root / 'Procfile', 'w') as f:
            f.write(procfile_content)
    
    def _generate_deployment_guide(self, platform: str = None):
        """Generează un ghid complet de deployment."""
        platform_info = self.supported_platforms.get(platform, {}) if platform else {}
        
        guide_content = f'''# 🚀 GHID DEPLOYMENT SECURIZAT - TELEGRAM VIDEO DOWNLOADER BOT

Generat automat la: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Platformă țintă: {platform_info.get('name', 'Generic') if platform else 'Any'}

## 📋 PREREQUISITE

### 1. Token Bot Telegram
1. Deschide [@BotFather](https://t.me/BotFather) pe Telegram
2. Trimite `/newbot` și urmează instrucțiunile
3. Salvează token-ul primit (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. **IMPORTANT**: Nu partaja niciodată acest token!

### 2. Pregătește Repository-ul
```bash
# Verifică că toate fișierele sensibile sunt excluse
git status
git check-ignore .env

# Rulează verificările de securitate
python scripts/security_check.py --auto-fix

# Testează local
python main.py
```

## 🔐 CONFIGURAREA SECRETELOR

### Metoda 1: Fișier .env (pentru dezvoltare locală)
```bash
# Copiază template-ul
cp .env.template .env

# Editează .env cu valorile tale reale
nano .env
```

### Metoda 2: Variabile de Mediu (pentru producție)
'''

        if platform == 'render':
            guide_content += '''
## 🚀 DEPLOYMENT PE RENDER

### Pas 1: Pregătește Proiectul
```bash
# Commit toate schimbările
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### Pas 2: Creează Serviciul pe Render
1. Accesează [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Conectează repository-ul GitHub
4. Configurări:
   - **Name**: `telegram-video-downloader-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

### Pas 3: Configurează Variabilele de Mediu
În Render Dashboard → Environment:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_URL=https://telegram-video-downloader-bot.onrender.com
PORT=5000
DEBUG=false
```

### Pas 4: Deploy și Testează
1. Click "Create Web Service"
2. Așteaptă deployment-ul (2-5 minute)
3. Verifică logs pentru erori
4. Testează bot-ul pe Telegram

'''
        elif platform == 'railway':
            guide_content += '''
## 🚀 DEPLOYMENT PE RAILWAY

### Pas 1: Instalează Railway CLI
```bash
# Instalează CLI
npm install -g @railway/cli

# Login
railway login
```

### Pas 2: Deploy Proiectul
```bash
# Inițializează proiectul
railway init

# Deploy
railway up

# Configurează variabilele de mediu
railway variables set TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
railway variables set WEBHOOK_URL=https://your-app.up.railway.app
railway variables set PORT=5000
```

### Pas 3: Configurează Webhook URL
```bash
# Obține URL-ul aplicației
railway domain

# Actualizează WEBHOOK_URL cu URL-ul real
railway variables set WEBHOOK_URL=https://your-actual-domain.up.railway.app
```

'''
        elif platform == 'heroku':
            guide_content += '''
## 🚀 DEPLOYMENT PE HEROKU

### Pas 1: Pregătește Heroku CLI
```bash
# Instalează Heroku CLI
# Urmează ghidul oficial: https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login
```

### Pas 2: Creează Aplicația
```bash
# Creează aplicația
heroku create telegram-video-downloader-bot

# Adaugă remote-ul git
heroku git:remote -a telegram-video-downloader-bot
```

### Pas 3: Configurează Variabilele de Mediu
```bash
heroku config:set TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
heroku config:set WEBHOOK_URL=https://telegram-video-downloader-bot.herokuapp.com
heroku config:set PORT=5000
heroku config:set DEBUG=false
```

### Pas 4: Deploy
```bash
# Deploy
git push heroku main

# Verifică logs
heroku logs --tail
```

'''

        guide_content += '''
## 🛡️ SECURITATEA ÎN PRODUCȚIE

### Verificări Post-Deployment
1. **Testează Bot-ul**:
   - Trimite un mesaj botului pe Telegram
   - Încearcă să descarci un video
   - Verifică că nu apar erori

2. **Monitorizează Logs**:
   - Verifică logs pentru erori sau warning-uri
   - Monitorizează utilizarea memoriei și CPU

3. **Securitate**:
   - Verifică că `.env` NU este în repository
   - Confirmă că token-urile sunt configure corect
   - Testează rate limiting

### Rotația Token-urilor
```bash
# Generează un token nou la @BotFather
# Actualizează variabila de mediu
# Pentru Render: Dashboard → Environment
# Pentru Railway: railway variables set TELEGRAM_BOT_TOKEN=new_token
# Pentru Heroku: heroku config:set TELEGRAM_BOT_TOKEN=new_token
```

## 🔧 TROUBLESHOOTING

### Erori Comune

1. **"Webhook failed"**:
   - Verifică că WEBHOOK_URL este corect
   - Confirmă că aplicația răspunde la `/health`

2. **"Rate limited"**:
   - Verifică configurația rate limiting
   - Poate fi necesar să crești limitele

3. **"Video download failed"**:
   - Verifică logs pentru detalii
   - Poate fi o problemă cu yt-dlp sau platformele

### Comenzi Utile de Debug
```bash
# Verifică statusul aplicației
curl https://your-app-url.com/health

# Testează endpoint-urile
curl -X POST https://your-app-url.com/webhook -d '{}'

# Verifică configurația
env | grep TELEGRAM
```

## 📞 SUPORT

Dacă întâmpini probleme:
1. Verifică logs-urile aplicației
2. Rulează `python scripts/security_check.py`
3. Consultă documentația platformei de hosting
4. Contactează echipa de dezvoltare

---
**⚠️  IMPORTANT**: Nu partaja niciodată token-urile sau credențialele! Păstrează-le securizate!

*Ghid generat automat de Secure Deploy Script v3.0.0*
'''

        # Salvează ghidul
        guide_path = self.project_root / f'DEPLOYMENT_GUIDE_{platform or "GENERIC"}.md'
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"📋 Deployment guide saved: {guide_path}")

def main():
    """Funcția principală."""
    parser = argparse.ArgumentParser(description="Secure deployment for Telegram Bot")
    parser.add_argument('--platform', choices=['render', 'railway', 'heroku', 'fly', 'vercel'], 
                       help='Target deployment platform')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--skip-security', action='store_true', help='Skip security checks (not recommended)')
    
    args = parser.parse_args()
    
    deployer = SecureDeployment(args.project_root)
    
    print(f"🚀 SECURE DEPLOYMENT - TELEGRAM VIDEO DOWNLOADER BOT")
    print(f"Platform: {args.platform or 'Generic'}")
    print(f"Project: {Path(args.project_root).absolute()}")
    print("=" * 60)
    
    # Rulează verificările de deployment
    if deployer.run_deployment_check(args.platform):
        print("\n✅ DEPLOYMENT CHECK PASSED!")
        print("🚀 Your bot is ready for secure deployment!")
        
        if args.platform:
            print(f"📋 Check DEPLOYMENT_GUIDE_{args.platform.upper()}.md for detailed instructions")
        
        print("\n🔑 Next steps:")
        print("1. Configure environment variables on your hosting platform")
        print("2. Deploy your code")
        print("3. Test the bot functionality")
        print("4. Monitor logs and metrics")
        
    else:
        print("\n❌ DEPLOYMENT CHECK FAILED!")
        print("🛠️  Please fix the issues above before deploying")
        print("💡 Run with --skip-security to bypass security checks (not recommended)")
        sys.exit(1)

if __name__ == "__main__":
    main()
