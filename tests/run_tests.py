#!/usr/bin/env python3
# tests/run_tests.py - Script principal pentru rularea suite-ului de teste
# Versiunea: 2.0.0 - Arhitectura Modulară

import sys
import os
import pytest
import argparse
from pathlib import Path

# Adaugă directorul root la Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


def main():
    """Entry point principal pentru rularea testelor"""
    
    parser = argparse.ArgumentParser(description="Rulează suite-ul de teste pentru arhitectura modulară")
    parser.add_argument(
        "--module", 
        choices=["platform_manager", "memory_manager", "monitoring", "cache", "all"],
        default="all",
        help="Modulul specific de testat"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="count", 
        default=0,
        help="Nivel de verbozitate (folosește -v, -vv, sau -vvv)"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Rulează cu coverage reporting"
    )
    parser.add_argument(
        "--integration", 
        action="store_true",
        help="Rulează doar testele de integrare"
    )
    parser.add_argument(
        "--unit", 
        action="store_true",
        help="Rulează doar testele unitare"
    )
    parser.add_argument(
        "--fast", 
        action="store_true",
        help="Rulează doar testele rapide (exclude testele lente)"
    )
    parser.add_argument(
        "--output", 
        choices=["terminal", "html", "xml"],
        default="terminal",
        help="Formatul output-ului pentru rapoarte"
    )
    
    args = parser.parse_args()
    
    # Construiește argumentele pentru pytest
    pytest_args = []
    
    # Directorul de teste
    tests_dir = Path(__file__).parent
    
    # Selectează modulele de testat
    if args.module == "all":
        pytest_args.append(str(tests_dir))
    else:
        pytest_args.append(str(tests_dir / f"test_{args.module}.py"))
    
    # Configurează verbozitatea
    if args.verbose > 0:
        pytest_args.append("-" + "v" * min(args.verbose, 3))
    
    # Configurează coverage
    if args.coverage:
        pytest_args.extend([
            "--cov=core",
            "--cov=utils", 
            "--cov=platforms",
            "--cov-report=term-missing",
            "--cov-report=html:tests/htmlcov"
        ])
    
    # Filtrează tipurile de teste
    if args.integration:
        pytest_args.extend(["-m", "integration"])
    elif args.unit:
        pytest_args.extend(["-m", "not integration"])
        
    # Exclude testele lente
    if args.fast:
        pytest_args.extend(["-m", "not slow"])
    
    # Configurează output-ul
    if args.output == "html":
        pytest_args.extend(["--html=tests/report.html", "--self-contained-html"])
    elif args.output == "xml":
        pytest_args.extend(["--junitxml=tests/report.xml"])
    
    # Configurări generale
    pytest_args.extend([
        "--tb=short",  # Format traceback scurt
        "--strict-markers",  # Verifică markerii
        "--disable-warnings",  # Reduce noise
        "-ra",  # Afișează summary pentru toate testele
    ])
    
    print(f"🧪 Rulează teste pentru: {args.module}")
    print(f"📁 Director teste: {tests_dir}")
    print(f"⚙️  Argumentele pytest: {' '.join(pytest_args)}")
    print("=" * 70)
    
    # Rulează testele
    exit_code = pytest.main(pytest_args)
    
    # Raportează rezultatele
    if exit_code == 0:
        print("\n" + "=" * 70)
        print("✅ TOATE TESTELE AU TRECUT CU SUCCES!")
        print("🎉 Arhitectura modulară este validată și gata pentru deployment!")
    else:
        print("\n" + "=" * 70)
        print("❌ UNELE TESTE AU EȘUAT")
        print(f"💥 Cod de ieșire: {exit_code}")
        print("🔍 Verifică erorile de mai sus pentru detalii")
    
    # Informații suplimentare
    if args.coverage and exit_code == 0:
        print(f"📊 Raport coverage HTML disponibil în: {tests_dir / 'htmlcov' / 'index.html'}")
        
    if args.output == "html":
        print(f"📋 Raport HTML disponibil în: {tests_dir / 'report.html'}")
    elif args.output == "xml":
        print(f"📋 Raport XML disponibil în: {tests_dir / 'report.xml'}")
    
    return exit_code


def run_quick_tests():
    """Rulează testele rapide pentru validare rapidă"""
    print("🚀 RULARE TESTELE RAPIDE - VALIDARE ARHITECTURĂ")
    print("=" * 60)
    
    tests_dir = Path(__file__).parent
    
    pytest_args = [
        str(tests_dir),
        "-m", "not slow and not integration",
        "-v",
        "--tb=short",
        "--disable-warnings",
        "-x",  # Stop la prima eroare
        "--durations=10"  # Afișează cele mai lente 10 teste
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ TESTELE RAPIDE AU TRECUT - ARHITECTURA ESTE VALIDĂ!")
    else:
        print(f"\n❌ TESTELE RAPIDE AU EȘUAT - COD IEȘIRE: {exit_code}")
        
    return exit_code


def run_integration_tests():
    """Rulează doar testele de integrare"""
    print("🔗 RULARE TESTELE DE INTEGRARE")
    print("=" * 50)
    
    tests_dir = Path(__file__).parent
    
    pytest_args = [
        str(tests_dir),
        "-m", "integration",
        "-v",
        "--tb=long",
        "--disable-warnings"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ TESTELE DE INTEGRARE AU TRECUT!")
    else:
        print(f"\n❌ TESTELE DE INTEGRARE AU EȘUAT - COD IEȘIRE: {exit_code}")
        
    return exit_code


def validate_architecture():
    """Validează arhitectura prin rularea unui set minimal de teste critice"""
    print("🏗️  VALIDARE ARHITECTURĂ MODULARĂ")
    print("=" * 50)
    
    tests_dir = Path(__file__).parent
    
    # Teste critice pentru validare
    critical_tests = [
        "test_platform_manager.py::TestPlatformManager::test_register_platform",
        "test_memory_manager.py::TestMemoryManager::test_memory_manager_initialization", 
        "test_monitoring.py::TestMonitoringSystem::test_monitoring_system_initialization",
        "test_cache.py::TestSmartCache::test_smart_cache_initialization"
    ]
    
    for test in critical_tests:
        print(f"🧪 Validează: {test}")
        
        pytest_args = [
            str(tests_dir / test),
            "-v",
            "--tb=short",
            "--disable-warnings",
            "-x"
        ]
        
        exit_code = pytest.main(pytest_args)
        
        if exit_code != 0:
            print(f"❌ VALIDAREA A EȘUAT LA: {test}")
            return exit_code
            
    print("\n🎉 ARHITECTURA MODULARĂ ESTE VALIDĂ ȘI FUNCȚIONALĂ!")
    return 0


if __name__ == "__main__":
    # Verifică dacă vrem să rulăm validarea rapidă
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        exit_code = run_quick_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--validate":
        exit_code = validate_architecture()
    elif len(sys.argv) > 1 and sys.argv[1] == "--integration":
        exit_code = run_integration_tests()
    else:
        exit_code = main()
        
    sys.exit(exit_code)
