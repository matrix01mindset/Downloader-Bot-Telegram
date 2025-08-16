# Design Document

## Overview

Acest design abordează problemele critice identificate în botul Telegram pentru descărcarea videoclipurilor, cu focus pe compatibilitatea cu Render free tier și funcționarea corectă pe toate platformele suportate. Soluția se bazează pe principiul "zero breaking changes" - toate îmbunătățirile vor fi implementate fără a afecta funcționalitatea existentă.

Problemele principale rezolvate includ: gestionarea caption-urilor prea lungi, inconsistențele în procesarea descrierilor, optimizarea pentru Render free tier, îmbunătățirea strategiilor de fallback pentru platforme, și gestionarea corectă a caracterelor speciale.

## Architecture

### Current Architecture
```
User → Telegram → Webhook → Flask App → yt-dlp → Video File → Telegram
```

### Enhanced Architecture
```
User → Telegram → Webhook → Flask App → Caption Manager → Platform Handler → yt-dlp → File Processor → Telegram
                                    ↓
                              Error Handler → Retry Logic → Fallback Strategies
```

### Key Components
1. **Caption Manager**: Centralizează gestionarea caption-urilor cu limitări stricte
2. **Platform Handler**: Gestionează strategii specifice pentru fiecare platformă
3. **Error Handler**: Procesează erorile și aplică strategii de retry
4. **File Processor**: Optimizează fișierele pentru limitările Telegram
5. **Render Optimizer**: Configurații specifice pentru Render free tier

## Components and Interfaces

### 1. Caption Manager

**Purpose**: Centralizează crearea și validarea caption-urilor pentru Telegram

**Interface**:
```python
def create_safe_caption(title, uploader=None, description=None, duration=None, file_size=None, max_length=1000):
    """
    Creează caption sigur pentru Telegram cu truncare inteligentă
    
    Args:
        title (str): Titlul videoclipului (obligatoriu)
        uploader (str): Numele creatorului (opțional)
        description (str): Descrierea videoclipului (opțional)
        duration (int): Durata în secunde (opțional)
        file_size (int): Mărimea fișierului în bytes (opțional)
        max_length (int): Lungimea maximă a caption-ului (default: 1000)
    
    Returns:
        str: Caption formatat și sigur pentru Telegram
    """
```

**Key Features**:
- Truncare inteligentă a descrierilor lungi
- Escapare HTML pentru caractere speciale
- Prioritizarea informațiilor importante
- Buffer de siguranță pentru limitele Telegram
- Gestionarea caracterelor Unicode și emoticoanelor

### 2. Platform Handler

**Purpose**: Gestionează strategii specifice pentru fiecare platformă

**Interface**:
```python
class PlatformHandler:
    def get_platform_config(self, url):
        """Returnează configurația optimă pentru platformă"""
        
    def get_fallback_strategies(self, platform):
        """Returnează strategiile de fallback pentru platformă"""
        
    def normalize_url(self, url, platform):
        """Normalizează URL-ul pentru compatibilitate"""
```

**Platform-Specific Strategies**:
- **TikTok**: User agents mobili, headers specifici
- **Instagram**: Configurații pentru Reels și IGTV
- **Facebook**: Multiple strategii API, normalizare URL
- **Twitter/X**: Gestionarea noilor formate de URL

### 3. Error Handler

**Purpose**: Procesează erorile și aplică strategii de retry

**Interface**:
```python
class ErrorHandler:
    def classify_error(self, error_msg, platform):
        """Clasifică tipul de eroare"""
        
    def get_retry_strategy(self, error_type, attempt):
        """Returnează strategia de retry"""
        
    def get_user_message(self, error_type, platform):
        """Returnează mesaj prietenos pentru utilizator"""
```

**Error Types**:
- `CAPTION_TOO_LONG`: Caption depășește limitele
- `PRIVATE_VIDEO`: Videoclip privat
- `PLATFORM_ERROR`: Eroare specifică platformei
- `NETWORK_ERROR`: Probleme de conectivitate
- `FILE_TOO_LARGE`: Fișier prea mare

### 4. Render Optimizer

**Purpose**: Optimizează configurațiile pentru Render free tier

**Key Optimizations**:
- Timeout-uri reduse pentru evitarea limitelor
- Connection pool sizing optimizat
- Memory management îmbunătățit
- Cleanup automat fișiere temporare
- Configurații webhook optimizate

## Data Models

### VideoMetadata
```python
@dataclass
class VideoMetadata:
    title: str
    uploader: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    platform: str = "unknown"
    url: str = ""
    thumbnail_url: Optional[str] = None
```

### DownloadResult
```python
@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[str] = None
    metadata: Optional[VideoMetadata] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    retry_suggested: bool = False
```

### PlatformConfig
```python
@dataclass
class PlatformConfig:
    name: str
    user_agents: List[str]
    headers: Dict[str, str]
    extractor_args: Dict[str, Any]
    timeout: int = 30
    max_retries: int = 3
    fallback_configs: List[Dict] = field(default_factory=list)
```

## Error Handling

### Error Classification Strategy

1. **Caption Errors**:
   - Detectare: "caption too long", "message too long"
   - Acțiune: Retry cu caption truncat
   - Fallback: Caption minimal cu doar titlul

2. **Platform Errors**:
   - Detectare: "private video", "not available", "parsing error"
   - Acțiune: Încercare configurații alternative
   - Fallback: Mesaj explicativ pentru utilizator

3. **Network Errors**:
   - Detectare: "timeout", "connection error", "network error"
   - Acțiune: Retry cu delay exponențial
   - Fallback: Sugestie să încerce din nou

4. **File Size Errors**:
   - Detectare: "file too large", "exceeds limit"
   - Acțiune: Redownload cu calitate mai mică
   - Fallback: Explicație despre limitări

### Retry Logic

```python
def retry_with_backoff(func, max_attempts=3, base_delay=1):
    """
    Retry cu exponential backoff
    Delays: 1s, 2s, 4s
    """
```

### Graceful Degradation

1. **Caption Truncation Levels**:
   - Level 1: Truncare descriere la 500 caractere
   - Level 2: Truncare descriere la 200 caractere
   - Level 3: Doar titlu și creator
   - Level 4: Doar titlu

2. **Quality Fallback**:
   - Level 1: 720p, <50MB
   - Level 2: 480p, <30MB
   - Level 3: 360p, <20MB
   - Level 4: Worst quality available

## Testing Strategy

### Unit Tests
- `test_caption_manager.py`: Testează crearea caption-urilor
- `test_platform_handler.py`: Testează strategiile pentru platforme
- `test_error_handler.py`: Testează clasificarea și gestionarea erorilor
- `test_render_optimizer.py`: Testează optimizările pentru Render

### Integration Tests
- `test_full_download_flow.py`: Testează fluxul complet de descărcare
- `test_webhook_handling.py`: Testează gestionarea webhook-urilor
- `test_platform_compatibility.py`: Testează toate platformele

### Load Tests
- `test_render_limits.py`: Testează limitările Render free tier
- `test_concurrent_downloads.py`: Testează descărcări simultane
- `test_memory_usage.py`: Testează utilizarea memoriei

### Test Data
- Videoclipuri cu descrieri foarte lungi
- Videoclipuri cu caractere speciale și emoticoane
- Videoclipuri de pe toate platformele suportate
- Scenarii de eroare simulate

### Acceptance Criteria Testing
- Testare cu utilizatori reali pe Telegram
- Verificarea tuturor cerințelor din requirements.md
- Testare pe Render free tier în condiții reale
- Monitoring post-deployment pentru 48 ore

## Performance Considerations

### Render Free Tier Optimizations
- **Memory**: Cleanup agresiv fișiere temporare
- **CPU**: Timeout-uri reduse, procese optimizate
- **Network**: Connection pooling, retry logic inteligent
- **Storage**: Ștergere imediată fișiere după upload

### Response Time Targets
- Webhook response: <5 secunde
- Video download: <60 secunde (videoclipuri normale)
- Error handling: <2 secunde
- Caption generation: <1 secundă

### Scalability Considerations
- Suport pentru maximum 10 utilizatori simultani (limita Render free)
- Queue system pentru cereri multiple
- Rate limiting pentru a evita abuse-ul
- Monitoring utilizare resurse

## Security Considerations

### Input Validation
- Validarea URL-urilor pentru platforme suportate
- Sanitizarea input-urilor utilizator
- Verificarea mărimii fișierelor înainte de procesare

### Error Information Disclosure
- Nu expunerea informațiilor sensibile în mesajele de eroare
- Logging securizat fără token-uri sau date personale
- Gestionarea sigură a fișierelor temporare

### Rate Limiting
- Limitarea cererilor per utilizator
- Protecție împotriva spam-ului
- Blacklist pentru utilizatori abuzivi

## Deployment Strategy

### Phase 1: Local Testing
- Implementarea tuturor componentelor
- Testare locală comprehensivă
- Validarea tuturor cerințelor

### Phase 2: Staging Deployment
- Deploy pe Render cu configurații de test
- Testare în condiții reale
- Monitoring și debugging

### Phase 3: Production Deployment
- Deploy final cu toate optimizările
- Monitoring continuu
- Rollback plan în caz de probleme

### Rollback Strategy
- Păstrarea versiunii curente ca backup
- Script automat de rollback
- Monitoring alerting pentru probleme critice

## Monitoring and Maintenance

### Key Metrics
- Success rate descărcări per platformă
- Timp mediu de răspuns
- Utilizare memorie și CPU
- Rate erori per tip

### Alerting
- Erori critice în webhook
- Utilizare excesivă resurse
- Rate scăzut de succes
- Probleme platforme specifice

### Maintenance Tasks
- Cleanup periodic fișiere temporare
- Update yt-dlp la versiuni noi
- Monitoring schimbări API platforme
- Optimizare configurații bazată pe metrici