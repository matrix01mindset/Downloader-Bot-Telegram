# 🔐 GHID SECURITATE - TELEGRAM VIDEO DOWNLOADER BOT

**Versiunea**: 3.0.0  
**Data**: 2025-01-06  
**Important**: Citește întregul ghid înainte de deployment!

## 🚨 AVERTISMENT SECURITATE

**⚠️ NU INCLUDE NICIODATĂ SECRETELE ÎN REPOSITORY-UL PUBLIC!**

Acest bot gestionează token-uri și credențiale sensibile care, dacă sunt expuse, pot compromite securitatea aplicației și conturilor tale. Urmează strict toate recomandările din acest ghid.

## 📋 CHECKLIST SECURITATE

Înainte de a publica codul:

- [ ] ✅ Am configurat corect `.gitignore`
- [ ] ✅ Am creat `.env.template` în loc de `.env`
- [ ] ✅ Toate secretele folosesc variabile de mediu (`${VARIABLE}`)
- [ ] ✅ Am rulat `python scripts/security_check.py`
- [ ] ✅ Nu există fișiere `.env`, `*.key`, `*.token` în repository
- [ ] ✅ Am testat local cu variabile de mediu
- [ ] ✅ Am pregătit documentația de deployment

## 🔧 SETUP SECURIZAT

### 1. Clonarea și Configurarea Inițială

```bash
# Clonează repository-ul
git clone https://github.com/your-username/telegram-video-downloader-bot.git
cd telegram-video-downloader-bot

# Instalează dependințele
pip install -r requirements.txt

# Copiază template-ul pentru configurare locală
cp .env.template .env
```

### 2. Configurarea Secretelor

#### Pentru Dezvoltare Locală:

```bash
# Editează .env cu token-ul tău real
nano .env

# Exemplu .env (înlocuiește cu valorile tale reale):
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_URL=https://your-ngrok-url.ngrok.io  # pentru testare locală
PORT=5000
DEBUG=true
```

#### Pentru Production:

**NICIODATĂ nu pune secretele în cod!** Folosește variabile de mediu ale platformei:

- **Render**: Dashboard → Environment Variables
- **Railway**: `railway variables set TELEGRAM_BOT_TOKEN=your_token`
- **Heroku**: `heroku config:set TELEGRAM_BOT_TOKEN=your_token`

### 3. Obținerea Token-ului Telegram

1. Deschide [@BotFather](https://t.me/BotFather) pe Telegram
2. Trimite `/newbot`
3. Urmează instrucțiunile pentru nume și username
4. Salvează token-ul primit (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. **IMPORTANT**: Nu partaja acest token cu nimeni!

## 🛡️ VERIFICĂRI SECURITATE

### Rularea Automată a Verificărilor

```bash
# Scanează pentru probleme de securitate
python scripts/security_check.py

# Scanează și încearcă să rezolve problemele automat
python scripts/security_check.py --auto-fix

# Generează raport detaliat
python scripts/security_check.py --output security_report.md
```

### Verificări Manuale

#### 1. Verifică .gitignore
```bash
# Verifică că .env este ignorat
git check-ignore .env
# Trebuie să returneze: .env

# Verifică statusul git
git status
# NU trebuie să apară fișiere .env, *.key, *.token
```

#### 2. Verifică Istoric Git
```bash
# Caută accidental commits cu secrete
git log --all --full-history -- "*.env"
git log --grep="token\|secret\|key" --oneline

# Dacă găsești commits problematice, contactează echipa!
```

## 🚀 DEPLOYMENT SECURIZAT

### Pregătirea pentru Deployment

```bash
# Rulează verificarea completă de deployment
python scripts/secure_deploy.py --platform render

# Pentru alte platforme:
python scripts/secure_deploy.py --platform railway
python scripts/secure_deploy.py --platform heroku
```

### Platforme Suportate

#### 1. **Render** (Recomandat pentru începători)
- ✅ Free tier disponibil
- ✅ Setup simplu prin GitHub
- ✅ Gestionare automată HTTPS
- 📋 Urmează `DEPLOYMENT_GUIDE_RENDER.md`

#### 2. **Railway**
- ✅ CLI puternic
- ✅ Deploy rapid
- ✅ Resurse generoase pe free tier
- 📋 Urmează `DEPLOYMENT_GUIDE_RAILWAY.md`

#### 3. **Heroku**
- ✅ Platformă matură
- ⚠️ Free tier limitat
- 📋 Urmează `DEPLOYMENT_GUIDE_HEROKU.md`

### Configurarea Variabilelor de Mediu în Production

Pentru orice platformă, configurează aceste variabile **în dashboard-ul platformei**, NU în cod:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_URL=https://your-app-name.platform.com
PORT=5000
DEBUG=false
LOG_LEVEL=INFO
```

## 🔒 BEST PRACTICES SECURITATE

### 1. Gestionarea Secretelor

**✅ CORECT:**
```yaml
# config.yaml
telegram:
  token: "${TELEGRAM_BOT_TOKEN}"
  webhook_url: "${WEBHOOK_URL}"
```

**❌ GREȘIT:**
```yaml
# config.yaml
telegram:
  token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"  # NICIODATĂ așa!
  webhook_url: "https://mybot.com"
```

### 2. Fișiere de Ignorat

Asigură-te că `.gitignore` conține:

```gitignore
# Secrete - OBLIGATORIU
.env*
!.env.template
!.env.example
secrets/
*.key
*.token
*.pem
*.p12

# Fișiere specifice platformelor
instagram_session.json
youtube_auth.json
tiktok_cookies.txt

# Backup-uri care pot conține secrete
*.env.backup*
config.backup*
```

### 3. Validarea Configurației

```bash
# Verifică că configurația folosește variabile de mediu
python -c "
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
token = config['telegram']['token']
assert token.startswith('\${'), 'Token must use environment variable!'
print('✅ Configuration is secure')
"
```

## 🔄 ROTAȚIA SECRETELOR

### Când să Rotești Token-urile:

1. **Periodic**: La fiecare 3-6 luni
2. **După Incident**: Dacă suspectezi compromiterea
3. **După Schimbări**: În echipă sau acces

### Cum să Rotești:

1. **Generează un token nou** la @BotFather:
   ```
   /token
   # Selectează bot-ul
   # Confirmă generarea unui token nou
   ```

2. **Actualizează în production**:
   ```bash
   # Render: Dashboard → Environment → Edit
   # Railway: railway variables set TELEGRAM_BOT_TOKEN=new_token
   # Heroku: heroku config:set TELEGRAM_BOT_TOKEN=new_token
   ```

3. **Testează** că bot-ul funcționează cu noul token

4. **Invalidează** token-ul vechi (opțional, @BotFather face asta automat)

## 🚨 ÎN CAZ DE COMPROMITERE

Dacă ai expus accidental un secret:

### 1. Acțiuni Imediate
```bash
# STOP aplicația imediat
# Pentru Heroku: heroku ps:scale web=0
# Pentru Render: Dashboard → Manual Deploy → Stop

# Rotește IMEDIAT toate secretele compromise
# Generează un token nou la @BotFather
```

### 2. Curățarea Repository-ului

```bash
# Pentru fișiere expuse recent
git rm --cached .env
git commit -m "Remove exposed secrets"

# Pentru secrete în istoricul git (PERICULOS - backup înainte!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (DOAR dacă ești sigur!)
git push origin --force --all
```

### 3. Monitorizare Post-Incident

- Monitorizează logs pentru activitate suspectă
- Verifică utilizarea bot-ului pentru pattern-uri anormale
- Consideră activarea de alertări suplimentare

## 📞 SUPORT SECURITATE

### Raportarea Vulnerabilităților

Dacă găsești o problemă de securitate:

1. **NU crea un issue public**
2. **Contactează privat** echipa de dezvoltare
3. **Include detalii**: Steps to reproduce, impact, etc.
4. **Așteaptă răspuns** înainte de divulgare publică

### Resurse Utile

- [OWASP Security Guidelines](https://owasp.org/www-project-api-security/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-security/about-secret-scanning)
- [Telegram Bot Security](https://core.telegram.org/bots/faq#security)

## 🔍 TOOLS SECURITATE

### Scripts Incluse

1. **`scripts/security_check.py`** - Scanner automat de securitate
2. **`scripts/secure_deploy.py`** - Verificări înainte de deployment
3. **`utils/secrets_manager.py`** - Manager securizat pentru secrete

### Verificări CI/CD

Adaugă în `.github/workflows/security.yml`:

```yaml
name: Security Check
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Security check
        run: python scripts/security_check.py --ci
```

---

## ⚖️ DISCLAIMER

Acest ghid oferă recomandări generale de securitate. Securitatea este o responsabilitate continuă și trebuie să te adaptezi constant la noile amenințări și best practices.

**Responsabilitatea finală pentru securitatea aplicației tale rămâne la tine.**

---

*Versiunea 3.0.0 - Ultima actualizare: 2025-01-06*
