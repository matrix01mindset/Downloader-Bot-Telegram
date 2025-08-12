#!/usr/bin/env python3
"""
🔐 SECRETS MANAGER - Telegram Video Downloader Bot
Versiunea: 3.0.0
Data: 2025-01-06

Gestionarea securizată a secretelor și credențialelor pentru bot.
IMPORTANT: Niciodată nu expune secretele în cod sau repository!
"""

import os
import json
import base64
import hashlib
from typing import Dict, Optional, Any, List
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class SecretsManager:
    """
    Manager pentru gestionarea securizată a secretelor.
    
    Caracteristici:
    - Încriptare AES pentru stocare locală
    - Suport pentru variabile de mediu
    - Validare și sanitizare
    - Audit logging pentru accesarea secretelor
    - Cache temporar securizat
    """
    
    def __init__(self, secrets_dir: str = "secrets"):
        self.secrets_dir = Path(secrets_dir)
        self.secrets_dir.mkdir(exist_ok=True, mode=0o700)  # Doar owner poate accesa
        self._cache = {}
        self._master_key = None
        
        # Fișiere importante
        self.env_template_file = Path(".env.template")
        self.secrets_config_file = self.secrets_dir / "config.encrypted"
        self.key_file = self.secrets_dir / ".key"
        
        # Inițializare
        self._ensure_security_setup()
    
    def _ensure_security_setup(self):
        """Asigură că setup-ul de securitate este corect."""
        try:
            # Verifică permisiunile directorului
            if os.name != 'nt':  # Unix systems
                stat_info = self.secrets_dir.stat()
                if oct(stat_info.st_mode)[-3:] != '700':
                    os.chmod(self.secrets_dir, 0o700)
                    logger.warning("Fixed secrets directory permissions")
            
            # Inițializează cheia master dacă nu există
            if not self.key_file.exists():
                self._generate_master_key()
            else:
                self._load_master_key()
                
        except Exception as e:
            logger.error(f"Security setup failed: {e}")
            raise
    
    def _generate_master_key(self):
        """Generează o cheie master pentru încriptare."""
        # Folosește o parolă derivată din informații sistem + salt random
        password = f"{os.environ.get('USER', 'default')}-{os.urandom(32).hex()}".encode()
        salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Salvează cheia și salt-ul
        key_data = {
            'key': key.decode(),
            'salt': base64.b64encode(salt).decode()
        }
        
        with open(self.key_file, 'w') as f:
            json.dump(key_data, f)
        
        # Setează permisiuni restrictive
        if os.name != 'nt':
            os.chmod(self.key_file, 0o600)
        
        self._master_key = Fernet(key)
        logger.info("Generated new master encryption key")
    
    def _load_master_key(self):
        """Încarcă cheia master existentă."""
        try:
            with open(self.key_file, 'r') as f:
                key_data = json.load(f)
            
            key = base64.urlsafe_b64encode(key_data['key'].encode())
            self._master_key = Fernet(key)
            logger.debug("Loaded master encryption key")
            
        except Exception as e:
            logger.error(f"Failed to load master key: {e}")
            raise
    
    def set_secret(self, name: str, value: str, encrypt: bool = True) -> bool:
        """
        Setează un secret securizat.
        
        Args:
            name: Numele secretului
            value: Valoarea secretului
            encrypt: Dacă să încripteze valoarea
            
        Returns:
            True dacă operația a reușit
        """
        try:
            if encrypt and self._master_key:
                encrypted_value = self._master_key.encrypt(value.encode()).decode()
                stored_value = f"encrypted:{encrypted_value}"
            else:
                stored_value = f"plain:{value}"
            
            # Salvează în cache
            self._cache[name] = stored_value
            
            # Audit log (fără valoarea secretului)
            logger.info(f"Secret '{name}' updated (encrypted: {encrypt})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set secret '{name}': {e}")
            return False
    
    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Obține un secret.
        
        Prioritatea de căutare:
        1. Variabile de mediu
        2. Cache intern
        3. Fișier încriptat
        4. Valoarea default
        
        Args:
            name: Numele secretului
            default: Valoarea default dacă secretul nu există
            
        Returns:
            Valoarea secretului sau None
        """
        try:
            # 1. Verifică variabilele de mediu mai întâi
            env_value = os.environ.get(name)
            if env_value:
                logger.debug(f"Secret '{name}' loaded from environment")
                return env_value
            
            # 2. Verifică cache-ul intern
            cached_value = self._cache.get(name)
            if cached_value:
                return self._decrypt_value(cached_value)
            
            # 3. Încearcă să încarce din fișierul încriptat
            stored_value = self._load_from_encrypted_file(name)
            if stored_value:
                self._cache[name] = stored_value
                return self._decrypt_value(stored_value)
            
            # 4. Returnează valoarea default
            if default:
                logger.debug(f"Secret '{name}' using default value")
                return default
            
            logger.warning(f"Secret '{name}' not found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get secret '{name}': {e}")
            return default
    
    def _decrypt_value(self, stored_value: str) -> str:
        """Decriptează o valoare stocată."""
        if stored_value.startswith("encrypted:"):
            encrypted_data = stored_value[10:]  # Remove "encrypted:" prefix
            decrypted = self._master_key.decrypt(encrypted_data.encode()).decode()
            return decrypted
        elif stored_value.startswith("plain:"):
            return stored_value[6:]  # Remove "plain:" prefix
        else:
            return stored_value
    
    def _load_from_encrypted_file(self, name: str) -> Optional[str]:
        """Încarcă un secret din fișierul încriptat."""
        try:
            if not self.secrets_config_file.exists():
                return None
            
            with open(self.secrets_config_file, 'r') as f:
                encrypted_data = json.load(f)
            
            return encrypted_data.get(name)
            
        except Exception as e:
            logger.error(f"Failed to load secret from file: {e}")
            return None
    
    def save_secrets_to_file(self) -> bool:
        """Salvează toate secretele din cache în fișierul încriptat."""
        try:
            with open(self.secrets_config_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
            
            # Setează permisiuni restrictive
            if os.name != 'nt':
                os.chmod(self.secrets_config_file, 0o600)
            
            logger.info("Secrets saved to encrypted file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
            return False
    
    def validate_secrets(self, required_secrets: List[str]) -> Dict[str, bool]:
        """
        Validează că toate secretele necesare sunt prezente.
        
        Args:
            required_secrets: Lista cu numele secretelor necesare
            
        Returns:
            Dict cu statusul fiecărui secret
        """
        validation_results = {}
        
        for secret_name in required_secrets:
            value = self.get_secret(secret_name)
            validation_results[secret_name] = value is not None and len(value.strip()) > 0
        
        return validation_results
    
    def get_safe_config_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returnează o versiune sigură a configurației pentru logging.
        Înlocuiește valorile sensibile cu placeholder-uri.
        
        Args:
            config: Configurația originală
            
        Returns:
            Configurația sanitizată
        """
        sensitive_keys = {
            'token', 'key', 'secret', 'password', 'auth', 'credential',
            'api_key', 'access_token', 'refresh_token', 'webhook_url'
        }
        
        def sanitize_value(key: str, value: Any) -> Any:
            if isinstance(value, dict):
                return {k: sanitize_value(k, v) for k, v in value.items()}
            elif isinstance(value, list):
                return [sanitize_value(key, item) for item in value]
            elif isinstance(value, str) and any(sensitive in key.lower() for sensitive in sensitive_keys):
                if len(value) > 8:
                    return f"{value[:4]}***{value[-4:]}"
                else:
                    return "***"
            else:
                return value
        
        return {key: sanitize_value(key, value) for key, value in config.items()}
    
    def rotate_master_key(self) -> bool:
        """
        Rotește cheia master (re-încriptează toate secretele cu o cheie nouă).
        
        Returns:
            True dacă rotația a reușit
        """
        try:
            # Decriptează toate secretele cu cheia veche
            decrypted_secrets = {}
            for name, stored_value in self._cache.items():
                decrypted_secrets[name] = self._decrypt_value(stored_value)
            
            # Generează o cheie nouă
            old_key_file = self.key_file.with_suffix('.old')
            self.key_file.rename(old_key_file)
            self._generate_master_key()
            
            # Re-încriptează toate secretele
            self._cache.clear()
            for name, value in decrypted_secrets.items():
                self.set_secret(name, value, encrypt=True)
            
            # Salvează în fișier
            self.save_secrets_to_file()
            
            # Șterge cheia veche
            old_key_file.unlink()
            
            logger.info("Master key rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Master key rotation failed: {e}")
            return False
    
    def clear_cache(self):
        """Curăță cache-ul de secrete din memorie."""
        self._cache.clear()
        logger.debug("Secrets cache cleared")
    
    def get_environment_template(self) -> str:
        """
        Generează un template .env cu placeholder-uri sigure.
        
        Returns:
            Conținutul template-ului .env
        """
        template = """# 🔐 TEMPLATE CONFIGURARE MEDIU - TELEGRAM VIDEO DOWNLOADER BOT
# Copiază acest fișier ca .env și completează cu valorile tale reale
# IMPORTANT: Nu commite niciodată fișierul .env în repository!

# 🤖 Token Bot Telegram (OBLIGATORIU)
# Obține de la @BotFather pe Telegram
# Exemplu: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# 🌐 URL Webhook pentru Production (OBLIGATORIU pentru hosting)
# Exemplu Render: https://your-app-name.onrender.com
# Exemplu Railway: https://your-app-name.up.railway.app
# Exemplu Heroku: https://your-app-name.herokuapp.com
WEBHOOK_URL=https://your-app-name.your-platform.com

# 🖥️ Configurări Server
PORT=5000
HOST=0.0.0.0

# 🔧 Configurări Avansate (OPȚIONALE)
DEBUG=false
LOG_LEVEL=INFO

# 🛡️ Securitate (OPȚIONALE)
RATE_LIMIT_ENABLED=true
MAX_FILE_SIZE_MB=45

# 📊 Monitorizare (OPȚIONALE)
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true

# 🎥 API Keys pentru Platforme (OPȚIONALE - pentru funcții avansate)
# Lasă goale dacă nu ai nevoie de ele
YOUTUBE_API_KEY=
INSTAGRAM_SESSION_ID=
TWITTER_BEARER_TOKEN=
FACEBOOK_ACCESS_TOKEN=

# ⚠️  IMPORTANTE:
# 1. Nu partaja niciodată aceste valori
# 2. Nu le include în repository
# 3. Folosește valori diferite pentru development și production
# 4. Rotește regulat token-urile și cheile
"""
        return template

# Instanță globală singleton
_secrets_manager = None

def get_secrets_manager() -> SecretsManager:
    """Returnează instanța singleton a SecretsManager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Funcție helper pentru obținerea rapidă a unui secret."""
    return get_secrets_manager().get_secret(name, default)

def validate_required_secrets() -> Dict[str, bool]:
    """
    Validează că toate secretele necesare sunt configurate.
    
    Returns:
        Dict cu statusul fiecărui secret necesar
    """
    required = [
        'TELEGRAM_BOT_TOKEN',
        'WEBHOOK_URL'
    ]
    
    return get_secrets_manager().validate_secrets(required)

if __name__ == "__main__":
    # Test și demonstrație
    manager = SecretsManager()
    
    # Generează template-ul .env
    template_path = Path(".env.template")
    if not template_path.exists():
        with open(template_path, 'w') as f:
            f.write(manager.get_environment_template())
        print(f"✅ Generated {template_path}")
    
    # Testează validarea
    validation_results = validate_required_secrets()
    print("\n🔍 Secret Validation Results:")
    for secret, is_valid in validation_results.items():
        status = "✅" if is_valid else "❌"
        print(f"{status} {secret}")
    
    print("\n🔐 Secrets Manager ready!")
