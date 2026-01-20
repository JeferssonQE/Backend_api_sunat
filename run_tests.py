#!/usr/bin/env python3
"""
Runner simple para tests de Backend SUNAT
Ejecuta tests organizados por categoría
"""
import os
import sys
import subprocess
from pathlib import Path

# Agregar path
sys.path.insert(0, str(Path(__file__).parent))


def run_config_tests():
    """Ejecutar tests de configuración básica"""
    print("🔧 EJECUTANDO TESTS DE CONFIGURACIÓN")
    print("=" * 50)
    
    result = subprocess.run([
        sys.executable, "tests/test_simple_config.py"
    ], capture_output=False)
    
    return result.returncode


def run_endpoint_tests():
    """Ejecutar tests de endpoints E2E"""
    print("\n🚀 EJECUTANDO TESTS DE ENDPOINTS E2E")
    print("=" * 50)
    
    result = subprocess.run([
        sys.executable, "tests/test_simple_endpoint_simple.py"
    ], capture_output=False)
    
    return result.returncode


def run_load_tests():
    """Ejecutar tests de carga"""
    print("\n⚡ EJECUTANDO TESTS DE CARGA")
    print("=" * 50)
    
    # Primero el test mock (rápido)
    print("🔧 Test de carga con mock completo...")
    result_mock = subprocess.run([
        sys.executable, "tests/test_load_mock.py"
    ], capture_output=False)
    
    if result_mock.returncode == 0:
        print("✅ Test mock exitoso")
        return 0
    else:
        print("❌ Test mock falló")
        print("\n⚠️ Nota: El test con scraper real está disponible en test_load_simple.py")
        print("   pero puede tomar varios minutos y usar muchos recursos.")
        return 1


def run_all_tests():
    """Ejecutar todos los tests en secuencia"""
    print("🧪 EJECUTANDO TODOS LOS TESTS - BACKEND SUNAT")
    print("=" * 60)
    
    tests = [
        ("Configuración", run_config_tests),
        ("Endpoints E2E", run_endpoint_tests),
        ("Carga", run_load_tests)
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n📋 Categoría: {name}")
        result = test_func()
        results.append((name, result))
        
        if result == 0:
            print(f"✅ {name} - EXITOSO")
        else:
            print(f"❌ {name} - FALLÓ")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result == 0)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASÓ" if result == 0 else "❌ FALLÓ"
        print(f"   {name}: {status}")
    
    print(f"\n🎯 RESULTADO: {passed}/{total} categorías exitosas")
    
    if passed == total:
        print("🎉 TODOS LOS TESTS PASARON")
        return 0
    else:
        print("⚠️ ALGUNOS TESTS FALLARON")
        return 1


def main():
    """Función principal del runner"""
    if len(sys.argv) < 2:
        print("📋 USO:")
        print("  python run_tests.py config     # Tests de configuración")
        print("  python run_tests.py endpoint   # Tests de endpoints E2E")
        print("  python run_tests.py load       # Tests de carga")
        print("  python run_tests.py all        # Todos los tests")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "config":
        return run_config_tests()
    elif command == "endpoint":
        return run_endpoint_tests()
    elif command == "load":
        return run_load_tests()
    elif command == "all":
        return run_all_tests()
    else:
        print(f"❌ Comando no reconocido: {command}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)