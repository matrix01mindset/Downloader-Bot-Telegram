#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pentru configurarea rapidă a variabilelor de mediu pe Render
Generează comenzi și instrucțiuni pentru setup
"""

import os
import json
from datetime import datetime

class RenderEnvSetup:
    def __init__(self):
        self.service_name = "telegram-video-downloader"
        self.env_vars = {}
        
    def load_env_template(self):
        """Încarcă template-ul de variabile din .env.example"""
        if not os.path.exists('.env.example'):
            print("❌ .env.example nu există!")
            return False
            
        try:
            with open('.env.example', 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    self.env_vars[key] = value
                    
            print(f"✅ Încărcat {len(self.env_vars)} variabile din .env.example")
            return True
            
        except Exception as e:
            print(f"❌ Eroare la încărcarea .env.example: {e}")
            return False
            
    def get_user_inputs(self):
        """Colectează input-uri de la utilizator pentru variabilele critice"""
        print("\n🔧 CONFIGURARE VARIABILE DE MEDIU PENTRU RENDER")
        print("="*60)
        
        # Mandatory variables
        mandatory_vars = {
            'TELEGRAM_BOT_TOKEN': {
                'description': 'Token-ul botului Telegram (din @BotFather)',
                'example': '1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789',
                'required': True
            },
            'WEBHOOK_URL': {
                'description': 'URL-ul serviciului Render (va fi generat automat)',
                'example': 'https://telegram-video-downloader-xxxx.onrender.com',
                'required': True
            }
        }
        
        print("\n📋 VARIABILE OBLIGATORII:")
        for var_name, config in mandatory_vars.items():
            print(f"\n🔹 {var_name}")
            print(f"   📝 {config['description']}")
            print(f"   💡 Exemplu: {config['example']}")
            
            if var_name == 'WEBHOOK_URL':
                print("   ⚠️  IMPORTANT: Această valoare va fi setată după crearea serviciului Render")
                service_name = input(f"   🎯 Numele serviciului Render [{self.service_name}]: ").strip()
                if service_name:
                    self.service_name = service_name
                self.env_vars[var_name] = f"https://{self.service_name}.onrender.com"
            else:
                while True:
                    value = input(f"   ✏️  Introdu {var_name}: ").strip()
                    if value:
                        self.env_vars[var_name] = value
                        break
                    else:
                        print("   ❌ Această variabilă este obligatorie!")
                        
        # Optional variables with defaults
        optional_vars = {
            'LOG_LEVEL': 'INFO',
            'MAX_FILE_SIZE_MB': '50',
            'DOWNLOAD_TIMEOUT': '300',
            'RATE_LIMIT_PER_MINUTE': '30',
            'DEBUG_MODE': 'false',
            'ENABLE_DETAILED_LOGS': 'true'
        }
        
        print("\n📋 VARIABILE OPȚIONALE (Enter pentru valoarea default):")
        for var_name, default_value in optional_vars.items():
            current_value = self.env_vars.get(var_name, default_value)
            value = input(f"   🔹 {var_name} [{current_value}]: ").strip()
            self.env_vars[var_name] = value if value else current_value
            
        # Platform toggles
        platform_vars = {
            'FACEBOOK': 'true',
            'INSTAGRAM': 'true',
            'TIKTOK': 'true',
            'TWITTER': 'true',
            'YOUTUBE': 'false'
        }
        
        print("\n📋 PLATFORME ACTIVATE (true/false):")
        for var_name, default_value in platform_vars.items():
            current_value = self.env_vars.get(var_name, default_value)
            while True:
                value = input(f"   🔹 {var_name} [{current_value}]: ").strip().lower()
                if value in ['', 'true', 'false']:
                    self.env_vars[var_name] = value if value else current_value
                    break
                else:
                    print("   ❌ Introdu 'true' sau 'false'")
                    
    def generate_render_instructions(self):
        """Generează instrucțiuni pentru setarea variabilelor în Render"""
        print("\n🚀 INSTRUCȚIUNI PENTRU RENDER.COM")
        print("="*60)
        
        print("\n1️⃣ CREEAZĂ SERVICIUL:")
        print("   • Mergi pe https://render.com")
        print("   • Click 'New +' → 'Web Service'")
        print("   • Conectează repository-ul GitHub")
        print(f"   • Nume serviciu: {self.service_name}")
        
        print("\n2️⃣ SETEAZĂ VARIABILELE DE MEDIU:")
        print("   • În Render Dashboard → Tab 'Environment'")
        print("   • Adaugă următoarele variabile:")
        print()
        
        # Group variables by importance
        mandatory = ['TELEGRAM_BOT_TOKEN', 'WEBHOOK_URL']
        optional = [k for k in self.env_vars.keys() if k not in mandatory]
        
        print("   🔴 OBLIGATORII:")
        for var_name in mandatory:
            if var_name in self.env_vars:
                value = self.env_vars[var_name]
                if var_name == 'TELEGRAM_BOT_TOKEN':
                    display_value = f"{value[:10]}..." if len(value) > 10 else "[TOKEN_TĂU]"
                else:
                    display_value = value
                print(f"   {var_name} = {display_value}")
                
        print("\n   🟡 OPȚIONALE:")
        for var_name in optional:
            value = self.env_vars[var_name]
            print(f"   {var_name} = {value}")
            
    def generate_curl_commands(self):
        """Generează comenzi curl pentru testare"""
        print("\n🧪 COMENZI DE TESTARE")
        print("="*60)
        
        base_url = self.env_vars.get('WEBHOOK_URL', f'https://{self.service_name}.onrender.com')
        token = self.env_vars.get('TELEGRAM_BOT_TOKEN', 'YOUR_TOKEN')
        
        commands = {
            'Test Health': f'curl {base_url}/health',
            'Test Status': f'curl {base_url}/',
            'Test Debug': f'curl {base_url}/debug',
            'Set Webhook': f'curl {base_url}/set_webhook',
            'Telegram getMe': f'curl "https://api.telegram.org/bot{token[:10]}...YOUR_TOKEN/getMe"',
            'Telegram Webhook Info': f'curl "https://api.telegram.org/bot{token[:10]}...YOUR_TOKEN/getWebhookInfo"'
        }
        
        for description, command in commands.items():
            print(f"\n🔹 {description}:")
            print(f"   {command}")
            
    def save_configuration(self):
        """Salvează configurația pentru referință viitoare"""
        config_data = {
            'timestamp': datetime.now().isoformat(),
            'service_name': self.service_name,
            'environment_variables': self.env_vars,
            'render_url': f'https://{self.service_name}.onrender.com',
            'webhook_url': self.env_vars.get('WEBHOOK_URL')
        }
        
        filename = f'render_config_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Configurația salvată în: {filename}")
        except Exception as e:
            print(f"\n❌ Eroare la salvarea configurației: {e}")
            
    def create_env_file(self):
        """Creează fișier .env pentru testare locală"""
        print("\n📝 CREARE FIȘIER .ENV PENTRU TESTARE LOCALĂ")
        print("="*60)
        
        if os.path.exists('.env'):
            response = input("\n⚠️  .env există deja. Suprascriu? (y/N): ").strip().lower()
            if response != 'y':
                print("   ⏭️  Sărit crearea .env")
                return
                
        try:
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(f"# Variabile de mediu pentru testare locală\n")
                f.write(f"# Generat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for var_name, value in self.env_vars.items():
                    f.write(f"{var_name}={value}\n")
                    
            print("✅ Fișier .env creat pentru testare locală")
            print("⚠️  ATENȚIE: Nu commita .env în Git!")
            
        except Exception as e:
            print(f"❌ Eroare la crearea .env: {e}")
            
    def run_setup(self):
        """Rulează setup-ul complet"""
        print("🎯 CONFIGURARE RENDER ENVIRONMENT VARIABLES")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Load template
        if not self.load_env_template():
            print("\n❌ Nu pot continua fără .env.example")
            return False
            
        # Get user inputs
        self.get_user_inputs()
        
        # Generate instructions
        self.generate_render_instructions()
        self.generate_curl_commands()
        
        # Save configuration
        self.save_configuration()
        
        # Offer to create .env
        create_env = input("\n❓ Creez fișier .env pentru testare locală? (Y/n): ").strip().lower()
        if create_env != 'n':
            self.create_env_file()
            
        print("\n🎉 CONFIGURARE COMPLETĂ!")
        print("\n📖 Următorii pași:")
        print("   1. Urmează instrucțiunile de mai sus pentru Render")
        print("   2. Rulează 'python pre_deploy_test.py' pentru verificări")
        print("   3. Consultă RENDER_DEPLOYMENT_GUIDE.md pentru detalii")
        
        return True
        
def main():
    """Funcția principală"""
    setup = RenderEnvSetup()
    
    try:
        setup.run_setup()
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup întrerupt de utilizator")
    except Exception as e:
        print(f"\n\n💥 Eroare în timpul setup-ului: {e}")
        
if __name__ == "__main__":
    main()