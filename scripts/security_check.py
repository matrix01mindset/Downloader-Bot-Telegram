#!/usr/bin/env python3
"""
🛡️ SECURITY CHECK SCRIPT - Telegram Video Downloader Bot
Versiunea: 3.0.0
Data: 2025-01-06

Script pentru verificarea securității și prevenirea expunerii accidentale
a secretelor în repository-ul public.
"""

import os
import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
import argparse

class SecurityChecker:
    """
    Verificator de securitate pentru detectarea expunerii secretelor.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues_found = []
        
        # Patterns pentru detectarea secretelor
        self.secret_patterns = {
            'telegram_bot_token': r'\b\d{8,10}:[A-Za-z0-9_-]{35}\b',
            'api_key_generic': r'["\']?[A-Za-z0-9_-]{32,}["\']?\s*[:=]\s*["\']?[A-Za-z0-9_-]{20,}["\']?',
            'webhook_url': r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[/a-zA-Z0-9._-]*',
            'password_field': r'password\s*[:=]\s*["\'][^"\']{3,}["\']',
            'secret_field': r'secret\s*[:=]\s*["\'][^"\']{10,}["\']',
            'token_field': r'token\s*[:=]\s*["\'][^"\']{10,}["\']',
            'key_field': r'key\s*[:=]\s*["\'][^"\']{10,}["\']',
            'auth_header': r'Authorization:\s*Bearer\s+[A-Za-z0-9_-]+',
        }
        
        # Fișiere care trebuie ignorate
        self.ignore_files = {
            '.env.example', '.env.template', 'security_check.py',
            'secrets_manager.py', 'README.md'
        }
        
        # Directoare care trebuie ignorate
        self.ignore_dirs = {
            '__pycache__', '.git', 'node_modules', 'venv', 'env',
            '.vscode', '.idea', 'secrets'
        }
        
        # Extensii de fișiere de verificat
        self.check_extensions = {'.py', '.js', '.json', '.yaml', '.yml', '.txt', '.md', '.env'}
    
    def scan_project(self) -> List[Dict]:
        """
        Scanează întregul proiect pentru probleme de securitate.
        
        Returns:
            Lista cu problemele găsite
        """
        self.issues_found = []
        
        print("🔍 Starting security scan...")
        
        # Scanează toate fișierele
        for file_path in self._get_files_to_check():
            self._scan_file(file_path)
        
        # Verifică configurațiile specifice
        self._check_gitignore()
        self._check_env_files()
        self._check_config_files()
        
        return self.issues_found
    
    def _get_files_to_check(self) -> List[Path]:
        """Obține lista fișierelor de verificat."""
        files_to_check = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Filtrează directoarele ignorate
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                # Verifică extensia și numele fișierului
                if (file_path.suffix in self.check_extensions or 
                    file_path.name.startswith('.env')):
                    
                    # Nu ignora fișierele importante
                    if file_path.name not in self.ignore_files:
                        files_to_check.append(file_path)
        
        return files_to_check
    
    def _scan_file(self, file_path: Path):
        """Scanează un fișier specific pentru probleme de securitate."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Verifică pattern-urile de secrete
            for pattern_name, pattern in self.secret_patterns.items():
                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Calculează numărul liniei
                    line_number = content[:match.start()].count('\n') + 1
                    
                    # Verifică dacă este într-un comentariu sau exemplu
                    if self._is_safe_context(content, match.start(), pattern_name):
                        continue
                    
                    self.issues_found.append({
                        'type': 'potential_secret_exposure',
                        'severity': 'HIGH',
                        'file': str(file_path),
                        'line': line_number,
                        'pattern': pattern_name,
                        'matched_text': match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                        'description': f'Potential {pattern_name} found in {file_path.name}'
                    })
            
        except Exception as e:
            self.issues_found.append({
                'type': 'scan_error',
                'severity': 'MEDIUM',
                'file': str(file_path),
                'error': str(e),
                'description': f'Could not scan file: {e}'
            })
    
    def _is_safe_context(self, content: str, match_start: int, pattern_name: str) -> bool:
        """
        Verifică dacă match-ul este într-un context sigur (comentariu, exemplu, etc.).
        """
        # Obține contextul din jurul match-ului
        start_context = max(0, match_start - 200)
        end_context = min(len(content), match_start + 200)
        context = content[start_context:end_context].lower()
        
        # Indicatori că este context sigur
        safe_indicators = [
            'example', 'template', 'placeholder', 'your_token_here',
            'your_key_here', 'your_secret_here', 'replace_with',
            '# exemplu', '# example', '# template', 'fake_token',
            'dummy_key', 'test_secret', '123456789:abcdef',
            'sample_token', 'demo_key'
        ]
        
        # Verifică dacă este în comentariu
        lines_before = content[:match_start].split('\n')
        current_line = lines_before[-1] if lines_before else ""
        
        if current_line.strip().startswith('#') or current_line.strip().startswith('//'):
            return True
        
        # Verifică indicatorii siguri
        return any(indicator in context for indicator in safe_indicators)
    
    def _check_gitignore(self):
        """Verifică că .gitignore este configurat corect."""
        gitignore_path = self.project_root / '.gitignore'
        
        if not gitignore_path.exists():
            self.issues_found.append({
                'type': 'missing_gitignore',
                'severity': 'HIGH',
                'file': '.gitignore',
                'description': 'Missing .gitignore file - secrets could be accidentally committed'
            })
            return
        
        try:
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
            
            # Verifică intrările esențiale
            required_entries = ['.env', '*.env', 'secrets/', '*.key', '*.token']
            missing_entries = []
            
            for entry in required_entries:
                if entry not in gitignore_content:
                    missing_entries.append(entry)
            
            if missing_entries:
                self.issues_found.append({
                    'type': 'incomplete_gitignore',
                    'severity': 'MEDIUM',
                    'file': '.gitignore',
                    'missing_entries': missing_entries,
                    'description': f'Gitignore missing entries: {", ".join(missing_entries)}'
                })
                
        except Exception as e:
            self.issues_found.append({
                'type': 'gitignore_error',
                'severity': 'MEDIUM',
                'file': '.gitignore',
                'error': str(e),
                'description': f'Could not check .gitignore: {e}'
            })
    
    def _check_env_files(self):
        """Verifică fișierele .env pentru probleme."""
        env_files = list(self.project_root.glob('.env*'))
        
        for env_file in env_files:
            if env_file.name in ['.env.example', '.env.template']:
                continue  # Acestea sunt sigure
            
            # Orice alt fișier .env ar trebui să fie în .gitignore
            gitignore_path = self.project_root / '.gitignore'
            if gitignore_path.exists():
                try:
                    with open(gitignore_path, 'r') as f:
                        gitignore_content = f.read()
                    
                    if env_file.name not in gitignore_content and '.env' not in gitignore_content:
                        self.issues_found.append({
                            'type': 'env_file_not_ignored',
                            'severity': 'CRITICAL',
                            'file': str(env_file),
                            'description': f'Environment file {env_file.name} is not in .gitignore'
                        })
                except:
                    pass
    
    def _check_config_files(self):
        """Verifică fișierele de configurare pentru secrete hardcodate."""
        config_files = [
            self.project_root / 'config.yaml',
            self.project_root / 'config.json',
            self.project_root / 'settings.py'
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                    
                    # Verifică pentru token-uri hardcodate (nu placeholder-uri)
                    if 'token:' in content and '${' not in content:
                        # Verifică dacă pare a fi un token real
                        token_match = re.search(r'token:\s*["\']?([^"\'}\s]+)["\']?', content)
                        if token_match and not self._looks_like_placeholder(token_match.group(1)):
                            self.issues_found.append({
                                'type': 'hardcoded_token',
                                'severity': 'HIGH',
                                'file': str(config_file),
                                'description': f'Potential hardcoded token in {config_file.name}'
                            })
                            
                except Exception as e:
                    pass
    
    def _looks_like_placeholder(self, value: str) -> bool:
        """Verifică dacă o valoare pare să fie un placeholder, nu un secret real."""
        placeholder_indicators = [
            'your_token', 'your_key', 'your_secret', 'replace_with',
            'token_here', 'key_here', 'example', 'placeholder',
            '${', 'xxx', '***', 'yyy'
        ]
        
        return any(indicator in value.lower() for indicator in placeholder_indicators)
    
    def generate_report(self, output_file: str = None) -> str:
        """
        Generează un raport de securitate.
        
        Args:
            output_file: Fișierul pentru salvarea raportului
            
        Returns:
            Conținutul raportului
        """
        # Grupează problemele pe severitate
        critical_issues = [issue for issue in self.issues_found if issue.get('severity') == 'CRITICAL']
        high_issues = [issue for issue in self.issues_found if issue.get('severity') == 'HIGH']
        medium_issues = [issue for issue in self.issues_found if issue.get('severity') == 'MEDIUM']
        
        # Generează raportul
        report = f"""# 🛡️ RAPORT SECURITATE - TELEGRAM VIDEO DOWNLOADER BOT
Data: {os.environ.get('DATE', 'N/A')}
Proiect: {self.project_root}

## 📊 REZUMAT
- 🔴 Probleme Critice: {len(critical_issues)}
- 🟡 Probleme Înalte: {len(high_issues)}  
- 🟠 Probleme Medii: {len(medium_issues)}
- 📁 Total Fișiere Scanate: {len(self._get_files_to_check())}

## 🚨 PROBLEME CRITICE
"""
        
        if critical_issues:
            for issue in critical_issues:
                report += f"""
### {issue.get('type', 'Unknown')}
- **Fișier**: `{issue.get('file', 'N/A')}`
- **Linie**: {issue.get('line', 'N/A')}
- **Descriere**: {issue.get('description', 'N/A')}
- **Acțiune**: REZOLVĂ IMEDIAT - Risc mare de expunere secrete!
"""
        else:
            report += "\n✅ Nicio problemă critică găsită.\n"
        
        report += "\n## ⚠️ PROBLEME ÎNALTE\n"
        
        if high_issues:
            for issue in high_issues:
                report += f"""
### {issue.get('type', 'Unknown')}
- **Fișier**: `{issue.get('file', 'N/A')}`
- **Linie**: {issue.get('line', 'N/A')}
- **Pattern**: {issue.get('pattern', 'N/A')}
- **Descriere**: {issue.get('description', 'N/A')}
- **Text Găsit**: `{issue.get('matched_text', 'N/A')}`
"""
        else:
            report += "\n✅ Nicio problemă înaltă găsită.\n"
        
        report += "\n## 📋 PROBLEME MEDII\n"
        
        if medium_issues:
            for issue in medium_issues:
                report += f"""
### {issue.get('type', 'Unknown')}
- **Fișier**: `{issue.get('file', 'N/A')}`
- **Descriere**: {issue.get('description', 'N/A')}
"""
        else:
            report += "\n✅ Nicio problemă medie găsită.\n"
        
        report += f"""
## 🔧 RECOMANDĂRI

### Pentru Probleme Critice:
1. **Șterge imediat** orice secret real din fișierele versionate
2. **Rotește toate token-urile** și cheile expuse
3. **Verifică istoricul git** pentru a șterge secretele din istoricul repository-ului
4. **Folosește variabile de mediu** pentru toate secretele

### Pentru Securitate Generală:
1. **Folosește întotdeauna** `.env` pentru secrete locale
2. **Configurează corect** `.gitignore` pentru a exclude toate fișierele sensibile
3. **Folosește** servicii de management secrete pentru production
4. **Auditează regular** codul pentru expunerea accidentală

### Comenzi Utile:
```bash
# Verifică istoricul git pentru secrete
git log --all --full-history -- '*.env'

# Șterge un fișier din întregul istoric git (PERICULOS!)
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch path/to/secret/file' --prune-empty --tag-name-filter cat -- --all

# Verifică status-ul .gitignore
git check-ignore -v .env

# Scanează din nou pentru securitate
python scripts/security_check.py --auto-fix
```

## 📞 SUPORT
Dacă găsești probleme de securitate, contactează echipa de dezvoltare imediat!

---
*Generat automat de Security Checker v3.0.0*
"""
        
        # Salvează raportul dacă este specificat
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 Raport salvat în: {output_file}")
        
        return report
    
    def auto_fix(self) -> bool:
        """
        Încearcă să rezolve automat problemele de securitate simple.
        
        Returns:
            True dacă cel puțin o problemă a fost rezolvată
        """
        fixes_applied = 0
        
        # Creează .env.template dacă nu există
        template_path = self.project_root / '.env.template'
        if not template_path.exists():
            from utils.secrets_manager import SecretsManager
            manager = SecretsManager()
            
            with open(template_path, 'w') as f:
                f.write(manager.get_environment_template())
            
            print("✅ Created .env.template")
            fixes_applied += 1
        
        # Îmbunătățește .gitignore
        gitignore_path = self.project_root / '.gitignore'
        required_entries = [
            '# Security files', '.env', '.env.local', '.env.production',
            'secrets/', '*.key', '*.token', '*.pem', '*.p12'
        ]
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                current_content = f.read()
            
            entries_to_add = []
            for entry in required_entries:
                if entry not in current_content:
                    entries_to_add.append(entry)
            
            if entries_to_add:
                with open(gitignore_path, 'a') as f:
                    f.write('\n# Added by security checker\n')
                    for entry in entries_to_add:
                        f.write(f'{entry}\n')
                
                print(f"✅ Updated .gitignore with {len(entries_to_add)} entries")
                fixes_applied += 1
        
        return fixes_applied > 0

def main():
    """Funcția principală pentru rularea verificărilor de securitate."""
    parser = argparse.ArgumentParser(description="Security checker for Telegram Bot")
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--output', help='Output file for the report')
    parser.add_argument('--auto-fix', action='store_true', help='Try to auto-fix issues')
    parser.add_argument('--ci', action='store_true', help='CI mode - exit with error code if issues found')
    
    args = parser.parse_args()
    
    # Inițializează checker-ul
    checker = SecurityChecker(args.project_root)
    
    # Auto-fix dacă este solicitat
    if args.auto_fix:
        print("🔧 Attempting auto-fixes...")
        if checker.auto_fix():
            print("✅ Some issues were auto-fixed. Re-running scan...")
        else:
            print("ℹ️  No auto-fixable issues found.")
    
    # Scanează proiectul
    issues = checker.scan_project()
    
    # Generează raportul
    report = checker.generate_report(args.output)
    
    # Afișează rezumatul
    critical_count = len([i for i in issues if i.get('severity') == 'CRITICAL'])
    high_count = len([i for i in issues if i.get('severity') == 'HIGH'])
    medium_count = len([i for i in issues if i.get('severity') == 'MEDIUM'])
    
    print(f"\n🛡️  SECURITATE SCAN COMPLET")
    print(f"🔴 Critice: {critical_count}")
    print(f"🟡 Înalte: {high_count}")
    print(f"🟠 Medii: {medium_count}")
    
    # Exit code pentru CI
    if args.ci and (critical_count > 0 or high_count > 0):
        print("\n❌ Security issues found in CI mode!")
        sys.exit(1)
    
    if critical_count == 0 and high_count == 0:
        print("\n✅ Proiectul pare să fie securizat!")
        sys.exit(0)
    else:
        print(f"\n⚠️  Găsite {critical_count + high_count} probleme de securitate!")
        sys.exit(0)

if __name__ == "__main__":
    main()
