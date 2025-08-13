# examples/demo_refactored_architecture.py - Demonstrație Arhitectură Refactorizată
# Versiunea: 4.0.0 - Exemplu Complet de Utilizare

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Adaugă calea către modulele proiectului
sys.path.append(str(Path(__file__).parent.parent))

try:
    # Import componente arhitectură refactorizată
    from core.refactored.platform_registry import PlatformRegistry
    from core.refactored.download_orchestrator import (
        DownloadOrchestrator, DownloadRequest, DownloadPriority
    )
    from core.refactored.health_monitor import HealthMonitor
    from platforms.implementations.youtube_platform import YouTubePlatform
    from platforms.implementations.tiktok_platform import TikTokPlatform
    from platforms.adapters.compatibility_layer import CompatibilityWrapper
    from utils.download.download_manager import DownloadManager
    from utils.network.network_manager import NetworkManager
    from utils.validation.validator import UniversalValidator
    from config.refactored.settings import Settings, Environment
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Asigură-te că toate modulele sunt create și disponibile.")
    sys.exit(1)

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('demo_refactored.log')
    ]
)

logger = logging.getLogger(__name__)

class RefactoredArchitectureDemo:
    """
    Demonstrație completă a arhitecturii refactorizate.
    Arată cum toate componentele lucrează împreună pentru o experiență optimizată.
    """
    
    def __init__(self):
        self.settings = None
        self.platform_registry = None
        self.download_orchestrator = None
        self.health_monitor = None
        self.validator = None
        
        # Statistici demo
        self.demo_stats = {
            'platforms_registered': 0,
            'downloads_completed': 0,
            'health_checks_performed': 0,
            'validations_performed': 0,
            'errors_encountered': 0
        }
    
    async def initialize(self):
        """Inițializează toate componentele arhitecturii"""
        logger.info("🚀 Inițializare Arhitectură Refactorizată v4.0.0")
        
        try:
            # 1. Încarcă configurările
            await self._load_settings()
            
            # 2. Inițializează validatorul universal
            await self._initialize_validator()
            
            # 3. Inițializează registrul de platforme
            await self._initialize_platform_registry()
            
            # 4. Inițializează orchestratorul de descărcări
            await self._initialize_download_orchestrator()
            
            # 5. Inițializează monitorul de sănătate
            await self._initialize_health_monitor()
            
            # 6. Înregistrează platformele
            await self._register_platforms()
            
            logger.info("✅ Arhitectura refactorizată a fost inițializată cu succes!")
            
        except Exception as e:
            logger.error(f"❌ Eroare la inițializarea arhitecturii: {e}")
            self.demo_stats['errors_encountered'] += 1
            raise
    
    async def _load_settings(self):
        """Încarcă configurările aplicației"""
        logger.info("📋 Încărcare configurări...")
        
        # Creează configurări pentru demo
        self.settings = Settings(
            environment=Environment.DEVELOPMENT,
            database=None,  # Nu folosim baza de date în demo
            cache=None,     # Nu folosim cache extern în demo
            network=None,   # Folosim configurările default
            download=None,  # Folosim configurările default
            platform=None,  # Folosim configurările default
            monitoring=None, # Folosim configurările default
            security=None,  # Folosim configurările default
            logging=None,   # Folosim configurările default
            performance=None # Folosim configurările default
        )
        
        # Aplică configurările pentru mediul de development
        self.settings.apply_environment_settings()
        
        logger.info(f"✅ Configurări încărcate pentru mediul: {self.settings.environment.value}")
    
    async def _initialize_validator(self):
        """Inițializează validatorul universal"""
        logger.info("🔍 Inițializare validator universal...")
        
        self.validator = UniversalValidator()
        await self.validator.initialize()
        
        logger.info("✅ Validator universal inițializat")
    
    async def _initialize_platform_registry(self):
        """Inițializează registrul de platforme"""
        logger.info("📚 Inițializare registru platforme...")
        
        self.platform_registry = PlatformRegistry()
        await self.platform_registry.initialize()
        
        logger.info("✅ Registru platforme inițializat")
    
    async def _initialize_download_orchestrator(self):
        """Inițializează orchestratorul de descărcări"""
        logger.info("🎭 Inițializare orchestrator descărcări...")
        
        self.download_orchestrator = DownloadOrchestrator(
            platform_registry=self.platform_registry,
            validator=self.validator
        )
        await self.download_orchestrator.initialize()
        
        logger.info("✅ Orchestrator descărcări inițializat")
    
    async def _initialize_health_monitor(self):
        """Inițializează monitorul de sănătate"""
        logger.info("🏥 Inițializare monitor sănătate...")
        
        self.health_monitor = HealthMonitor(
            platform_registry=self.platform_registry
        )
        await self.health_monitor.initialize()
        
        logger.info("✅ Monitor sănătate inițializat")
    
    async def _register_platforms(self):
        """Înregistrează platformele disponibile"""
        logger.info("🔌 Înregistrare platforme...")
        
        platforms_to_register = [
            ("YouTube", YouTubePlatform),
            ("TikTok", TikTokPlatform)
        ]
        
        for platform_name, platform_class in platforms_to_register:
            try:
                # Creează instanța platformei
                platform_instance = platform_class()
                
                # Inițializează platforma
                if await platform_instance.initialize():
                    # Înregistrează platforma
                    success = await self.platform_registry.register_platform(
                        platform_name.lower(), platform_instance
                    )
                    
                    if success:
                        self.demo_stats['platforms_registered'] += 1
                        logger.info(f"✅ Platforma {platform_name} înregistrată cu succes")
                    else:
                        logger.warning(f"⚠️ Platforma {platform_name} nu a putut fi înregistrată")
                else:
                    logger.warning(f"⚠️ Platforma {platform_name} nu a putut fi inițializată")
                    
            except Exception as e:
                logger.error(f"❌ Eroare la înregistrarea platformei {platform_name}: {e}")
                self.demo_stats['errors_encountered'] += 1
        
        # Afișează platformele înregistrate
        registered_platforms = await self.platform_registry.get_available_platforms()
        logger.info(f"📊 Total platforme înregistrate: {len(registered_platforms)}")
        
        for platform_name in registered_platforms:
            platform = await self.platform_registry.get_platform(platform_name)
            capabilities = platform.get_capabilities()
            domains = platform.get_supported_domains()
            logger.info(f"  • {platform_name}: {len(capabilities)} capabilități, {len(domains)} domenii")
    
    async def demonstrate_url_validation(self):
        """Demonstrează validarea URL-urilor"""
        logger.info("\n🔍 === DEMONSTRAȚIE VALIDARE URL-URI ===")
        
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.tiktok.com/@user/video/1234567890",
            "https://vm.tiktok.com/ZMeABC123/",
            "https://invalid-url",
            "not-a-url-at-all",
            "https://www.facebook.com/video/123"  # Platformă nesuportată
        ]
        
        for url in test_urls:
            try:
                # Validează URL-ul
                validation_report = await self.validator.validate_url(url)
                self.demo_stats['validations_performed'] += 1
                
                # Verifică suportul platformei
                platform_name = await self.platform_registry.find_platform_for_url(url)
                
                status = "✅ Valid" if validation_report.is_valid else "❌ Invalid"
                platform_status = f"📱 {platform_name}" if platform_name else "❓ Nesuportat"
                
                logger.info(f"  {status} | {platform_status} | {url[:50]}...")
                
                if not validation_report.is_valid:
                    for issue in validation_report.issues[:2]:  # Primele 2 probleme
                        logger.info(f"    ⚠️ {issue.message}")
                        
            except Exception as e:
                logger.error(f"  ❌ Eroare validare: {e}")
                self.demo_stats['errors_encountered'] += 1
    
    async def demonstrate_metadata_extraction(self):
        """Demonstrează extragerea de metadata"""
        logger.info("\n📊 === DEMONSTRAȚIE EXTRAGERE METADATA ===")
        
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.tiktok.com/@user/video/1234567890"
        ]
        
        for url in test_urls:
            try:
                # Găsește platforma
                platform_name = await self.platform_registry.find_platform_for_url(url)
                
                if platform_name:
                    platform = await self.platform_registry.get_platform(platform_name)
                    
                    logger.info(f"\n📱 Extragere metadata pentru {platform_name}:")
                    logger.info(f"  URL: {url}")
                    
                    # Extrage metadata
                    metadata = await platform.extract_metadata(url)
                    
                    logger.info(f"  📝 Titlu: {metadata.title}")
                    logger.info(f"  👤 Autor: {metadata.uploader}")
                    logger.info(f"  ⏱️ Durată: {metadata.duration}s")
                    logger.info(f"  👀 Vizualizări: {metadata.view_count:,}")
                    logger.info(f"  👍 Like-uri: {metadata.like_count:,}" if metadata.like_count else "  👍 Like-uri: N/A")
                    logger.info(f"  🏷️ Tag-uri: {', '.join(metadata.tags[:3])}..." if metadata.tags else "  🏷️ Tag-uri: N/A")
                    logger.info(f"  📦 Formate disponibile: {len(metadata.formats)}")
                    
                    # Afișează primele 2 formate
                    for i, fmt in enumerate(metadata.formats[:2]):
                        logger.info(f"    {i+1}. {fmt.quality.value} | {fmt.content_type.value} | {fmt.container}")
                        
                else:
                    logger.warning(f"  ❓ Platformă nesuportată pentru: {url}")
                    
            except Exception as e:
                logger.error(f"  ❌ Eroare extragere metadata: {e}")
                self.demo_stats['errors_encountered'] += 1
    
    async def demonstrate_download_process(self):
        """Demonstrează procesul de descărcare"""
        logger.info("\n⬇️ === DEMONSTRAȚIE PROCES DESCĂRCARE ===")
        
        # Creează directorul pentru descărcări
        download_dir = Path("demo_downloads")
        download_dir.mkdir(exist_ok=True)
        
        test_downloads = [
            {
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'filename': 'youtube_demo_video.mp4',
                'priority': DownloadPriority.HIGH
            },
            {
                'url': 'https://www.tiktok.com/@user/video/1234567890',
                'filename': 'tiktok_demo_video.mp4',
                'priority': DownloadPriority.MEDIUM
            }
        ]
        
        download_tasks = []
        
        for download_info in test_downloads:
            try:
                output_path = download_dir / download_info['filename']
                
                # Creează cererea de descărcare
                download_request = DownloadRequest(
                    url=download_info['url'],
                    output_path=str(output_path),
                    priority=download_info['priority']
                )
                
                logger.info(f"\n📥 Inițiere descărcare:")
                logger.info(f"  URL: {download_info['url']}")
                logger.info(f"  Fișier: {download_info['filename']}")
                logger.info(f"  Prioritate: {download_info['priority'].value}")
                
                # Trimite cererea către orchestrator
                job_id = await self.download_orchestrator.submit_download(download_request)
                download_tasks.append(job_id)
                
                logger.info(f"  🆔 Job ID: {job_id}")
                
            except Exception as e:
                logger.error(f"  ❌ Eroare la inițierea descărcării: {e}")
                self.demo_stats['errors_encountered'] += 1
        
        # Monitorizează progresul descărcărilor
        if download_tasks:
            logger.info(f"\n⏳ Monitorizare progres {len(download_tasks)} descărcări...")
            
            # Simulează monitorizarea (în realitate ar fi un loop continuu)
            await asyncio.sleep(2)
            
            for job_id in download_tasks:
                try:
                    status = await self.download_orchestrator.get_download_status(job_id)
                    
                    logger.info(f"  📊 Job {job_id}: {status.status.value}")
                    
                    if status.progress:
                        logger.info(f"    📈 Progres: {status.progress.percentage:.1f}%")
                        logger.info(f"    📦 Dimensiune: {status.progress.downloaded_bytes:,} / {status.progress.total_bytes:,} bytes")
                    
                    if status.result and status.result.success:
                        self.demo_stats['downloads_completed'] += 1
                        logger.info(f"    ✅ Descărcare completă: {status.result.file_path}")
                    elif status.error_message:
                        logger.error(f"    ❌ Eroare: {status.error_message}")
                        
                except Exception as e:
                    logger.error(f"  ❌ Eroare la verificarea statusului: {e}")
                    self.demo_stats['errors_encountered'] += 1
    
    async def demonstrate_health_monitoring(self):
        """Demonstrează monitorizarea sănătății"""
        logger.info("\n🏥 === DEMONSTRAȚIE MONITORIZARE SĂNĂTATE ===")
        
        try:
            # Efectuează verificări de sănătate
            health_report = await self.health_monitor.perform_health_check()
            self.demo_stats['health_checks_performed'] += 1
            
            logger.info(f"📊 Raport sănătate sistem:")
            logger.info(f"  🟢 Platforme sănătoase: {health_report.healthy_platforms}")
            logger.info(f"  🔴 Platforme cu probleme: {health_report.unhealthy_platforms}")
            logger.info(f"  📈 Scor general sănătate: {health_report.overall_health_score:.1f}%")
            
            # Afișează detalii pentru fiecare platformă
            for platform_name, platform_health in health_report.platform_health.items():
                status_icon = "🟢" if platform_health.is_healthy else "🔴"
                logger.info(f"\n  {status_icon} {platform_name}:")
                logger.info(f"    ⏱️ Timp răspuns: {platform_health.response_time:.2f}s")
                logger.info(f"    📊 Scor sănătate: {platform_health.health_score:.1f}%")
                
                if platform_health.metrics:
                    for metric_name, metric_value in list(platform_health.metrics.items())[:3]:
                        logger.info(f"    📈 {metric_name}: {metric_value}")
                
                if platform_health.alerts:
                    for alert in platform_health.alerts[:2]:  # Primele 2 alerte
                        logger.info(f"    ⚠️ {alert.severity.value}: {alert.message}")
            
            # Afișează metrici sistem
            system_metrics = await self.health_monitor.get_system_metrics()
            logger.info(f"\n🖥️ Metrici sistem:")
            logger.info(f"  💾 Utilizare memorie: {system_metrics.get('memory_usage', 'N/A')}%")
            logger.info(f"  🔄 Utilizare CPU: {system_metrics.get('cpu_usage', 'N/A')}%")
            logger.info(f"  💽 Spațiu disc: {system_metrics.get('disk_usage', 'N/A')}%")
            
        except Exception as e:
            logger.error(f"❌ Eroare la monitorizarea sănătății: {e}")
            self.demo_stats['errors_encountered'] += 1
    
    async def demonstrate_statistics_and_analytics(self):
        """Demonstrează statisticile și analitica"""
        logger.info("\n📈 === DEMONSTRAȚIE STATISTICI ȘI ANALITICA ===")
        
        try:
            # Statistici orchestrator
            orchestrator_stats = await self.download_orchestrator.get_statistics()
            logger.info(f"📊 Statistici Orchestrator:")
            logger.info(f"  📥 Total cereri: {orchestrator_stats.get('total_requests', 0)}")
            logger.info(f"  ✅ Descărcări reușite: {orchestrator_stats.get('successful_downloads', 0)}")
            logger.info(f"  ❌ Descărcări eșuate: {orchestrator_stats.get('failed_downloads', 0)}")
            logger.info(f"  ⏱️ Timp mediu descărcare: {orchestrator_stats.get('average_download_time', 0):.2f}s")
            
            # Statistici platforme
            registered_platforms = await self.platform_registry.get_available_platforms()
            
            for platform_name in registered_platforms:
                platform = await self.platform_registry.get_platform(platform_name)
                platform_stats = platform.get_statistics()
                
                logger.info(f"\n📱 Statistici {platform_name}:")
                logger.info(f"  🔍 Extrageri totale: {platform_stats.get('total_extractions', 0)}")
                logger.info(f"  ✅ Rata succes: {platform_stats.get('success_rate', 0):.1f}%")
                logger.info(f"  💾 Cache hits: {platform_stats.get('cache_hits', 0)}")
                logger.info(f"  📈 Cache hit rate: {platform_stats.get('cache_hit_rate', 0):.1f}%")
            
            # Statistici demo
            logger.info(f"\n🎯 Statistici Demo:")
            for stat_name, stat_value in self.demo_stats.items():
                logger.info(f"  📊 {stat_name.replace('_', ' ').title()}: {stat_value}")
            
        except Exception as e:
            logger.error(f"❌ Eroare la afișarea statisticilor: {e}")
            self.demo_stats['errors_encountered'] += 1
    
    async def run_complete_demo(self):
        """Rulează demonstrația completă"""
        logger.info("\n🎬 === ÎNCEPERE DEMONSTRAȚIE ARHITECTURĂ REFACTORIZATĂ ===")
        
        try:
            # Inițializare
            await self.initialize()
            
            # Demonstrații individuale
            await self.demonstrate_url_validation()
            await self.demonstrate_metadata_extraction()
            await self.demonstrate_download_process()
            await self.demonstrate_health_monitoring()
            await self.demonstrate_statistics_and_analytics()
            
            logger.info("\n🎉 === DEMONSTRAȚIE COMPLETĂ CU SUCCES ===")
            
        except Exception as e:
            logger.error(f"❌ Eroare în demonstrație: {e}")
            self.demo_stats['errors_encountered'] += 1
        
        finally:
            # Cleanup
            await self.cleanup()
    
    async def cleanup(self):
        """Curăță resursele"""
        logger.info("\n🧹 Curățare resurse...")
        
        try:
            if self.download_orchestrator:
                await self.download_orchestrator.shutdown()
            
            if self.health_monitor:
                await self.health_monitor.shutdown()
            
            if self.platform_registry:
                await self.platform_registry.shutdown()
            
            logger.info("✅ Curățare completă")
            
        except Exception as e:
            logger.error(f"❌ Eroare la curățare: {e}")


async def main():
    """Funcția principală pentru rularea demo-ului"""
    print("🚀 Demonstrație Arhitectură Refactorizată v4.0.0")
    print("=" * 60)
    print("Această demonstrație arată capabilitățile complete ale")
    print("arhitecturii refactorizate pentru descărcarea optimizată")
    print("de conținut de pe multiple platforme.")
    print("=" * 60)
    
    demo = RefactoredArchitectureDemo()
    await demo.run_complete_demo()
    
    print("\n" + "=" * 60)
    print("🎯 Demonstrația s-a încheiat!")
    print("Verifică fișierul 'demo_refactored.log' pentru detalii complete.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Demonstrația a fost oprită de utilizator.")
    except Exception as e:
        print(f"\n❌ Eroare neașteptată: {e}")
        sys.exit(1)