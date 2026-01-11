#!/usr/bin/env python3
"""
Load Testing para Backend SUNAT
Prueba múltiples solicitudes concurrentes para detectar problemas de rendimiento
"""
import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import List, Dict
import statistics


# Configuración del test
BASE_URL = "http://localhost:8080"
CONCURRENT_REQUESTS = 10  # Número de solicitudes simultáneas
TOTAL_REQUESTS = 50       # Total de solicitudes a enviar
REQUEST_DELAY = 0.1       # Delay entre solicitudes (segundos)


def create_test_payload() -> Dict:
    """Crea un payload de prueba para emisión"""
    return {
        "tipo_documento": "BOLETA",
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "cliente": {
            "dni": "12345678",
            "nombre": "Cliente Test Load"
        },
        "productos": [
            {
                "cantidad": 1.0,
                "unidad_medida": "UND",
                "descripcion": "PRODUCTO TEST LOAD",
                "precio_base": 100.0,
                "igv": 18,
                "precio_total": 118.0
            }
        ],
        "resumen": {
            "serie": "B001",
            "numero": f"{int(time.time()) % 10000:04d}",  # Número único
            "sub_total": 100.0,
            "igv_total": 18.0,
            "total": 118.0
        },
        "id_remitente": f"test-{int(time.time())}",
        "credenciales_encrypted": {
            "ruc_encrypted": "test_encrypted_ruc",
            "usuario_encrypted": "test_encrypted_user", 
            "password_encrypted": "test_encrypted_pass"
        }
    }


class LoadTestResult:
    """Resultado de una prueba de carga"""
    def __init__(self):
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.errors = []
        self.status_codes = []
        self.start_time = None
        self.end_time = None
    
    def add_result(self, success: bool, response_time: float, status_code: int = None, error: str = None):
        """Agrega resultado de una request"""
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)
        
        self.response_times.append(response_time)
        if status_code:
            self.status_codes.append(status_code)
    
    def get_summary(self) -> Dict:
        """Obtiene resumen de resultados"""
        total_requests = self.successful_requests + self.failed_requests
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "duration_seconds": duration,
            "requests_per_second": total_requests / duration if duration > 0 else 0,
            "response_times": {
                "min": min(self.response_times) if self.response_times else 0,
                "max": max(self.response_times) if self.response_times else 0,
                "avg": statistics.mean(self.response_times) if self.response_times else 0,
                "median": statistics.median(self.response_times) if self.response_times else 0,
            },
            "status_codes": dict(zip(*zip(*[(code, self.status_codes.count(code)) for code in set(self.status_codes)]))) if self.status_codes else {},
            "errors": list(set(self.errors))[:5]  # Primeros 5 errores únicos
        }


async def make_request(session: aiohttp.ClientSession, url: str, payload: Dict) -> tuple:
    """Hace una request HTTP y mide el tiempo"""
    start_time = time.time()
    
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response_time = time.time() - start_time
            
            if response.status == 202:  # Accepted
                return True, response_time, response.status, None
            else:
                error_text = await response.text()
                return False, response_time, response.status, f"HTTP {response.status}: {error_text[:100]}"
    
    except asyncio.TimeoutError:
        response_time = time.time() - start_time
        return False, response_time, None, "Timeout"
    
    except Exception as e:
        response_time = time.time() - start_time
        return False, response_time, None, str(e)[:100]


async def health_check(session: aiohttp.ClientSession) -> bool:
    """Verifica que el servidor esté funcionando"""
    try:
        async with session.get(f"{BASE_URL}/api/v1/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
            return response.status == 200
    except:
        return False


async def run_load_test() -> LoadTestResult:
    """Ejecuta el test de carga"""
    result = LoadTestResult()
    result.start_time = time.time()
    
    print(f"🚀 Iniciando Load Test")
    print(f"   URL: {BASE_URL}")
    print(f"   Solicitudes concurrentes: {CONCURRENT_REQUESTS}")
    print(f"   Total de solicitudes: {TOTAL_REQUESTS}")
    print(f"   Delay entre requests: {REQUEST_DELAY}s")
    print()
    
    # Verificar que el servidor esté funcionando
    async with aiohttp.ClientSession() as session:
        if not await health_check(session):
            print("❌ El servidor no está disponible. Asegúrate de que esté ejecutándose.")
            return result
        
        print("✅ Servidor disponible. Iniciando test...")
        print()
        
        # Crear semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        
        async def limited_request(request_id: int):
            """Request con límite de concurrencia"""
            async with semaphore:
                payload = create_test_payload()
                success, response_time, status_code, error = await make_request(
                    session, f"{BASE_URL}/api/v1/emitir", payload
                )
                
                result.add_result(success, response_time, status_code, error)
                
                # Log progreso
                status_icon = "✅" if success else "❌"
                print(f"{status_icon} Request {request_id:3d}: {response_time:.3f}s - Status: {status_code}")
                
                # Delay entre requests
                if REQUEST_DELAY > 0:
                    await asyncio.sleep(REQUEST_DELAY)
        
        # Ejecutar todas las requests
        tasks = [limited_request(i + 1) for i in range(TOTAL_REQUESTS)]
        await asyncio.gather(*tasks)
    
    result.end_time = time.time()
    return result


def print_results(result: LoadTestResult):
    """Imprime resultados del test"""
    summary = result.get_summary()
    
    print("\n" + "="*60)
    print("📊 RESULTADOS DEL LOAD TEST")
    print("="*60)
    
    print(f"Total de solicitudes:     {summary['total_requests']}")
    print(f"Solicitudes exitosas:     {summary['successful_requests']}")
    print(f"Solicitudes fallidas:     {summary['failed_requests']}")
    print(f"Tasa de éxito:           {summary['success_rate']:.1f}%")
    print(f"Duración total:          {summary['duration_seconds']:.2f}s")
    print(f"Requests por segundo:    {summary['requests_per_second']:.2f}")
    
    print(f"\n⏱️  TIEMPOS DE RESPUESTA:")
    print(f"Mínimo:                  {summary['response_times']['min']:.3f}s")
    print(f"Máximo:                  {summary['response_times']['max']:.3f}s")
    print(f"Promedio:                {summary['response_times']['avg']:.3f}s")
    print(f"Mediana:                 {summary['response_times']['median']:.3f}s")
    
    if summary['status_codes']:
        print(f"\n📈 CÓDIGOS DE ESTADO:")
        for code, count in summary['status_codes'].items():
            print(f"HTTP {code}:                 {count} veces")
    
    if summary['errors']:
        print(f"\n❌ ERRORES ENCONTRADOS:")
        for i, error in enumerate(summary['errors'], 1):
            print(f"{i}. {error}")
    
    print("\n" + "="*60)
    
    # Evaluación de rendimiento
    success_rate = summary['success_rate']
    avg_response_time = summary['response_times']['avg']
    
    print("🎯 EVALUACIÓN:")
    
    if success_rate >= 95:
        print("✅ Excelente: Tasa de éxito > 95%")
    elif success_rate >= 80:
        print("⚠️  Bueno: Tasa de éxito > 80%")
    else:
        print("❌ Malo: Tasa de éxito < 80%")
    
    if avg_response_time <= 1.0:
        print("✅ Excelente: Tiempo promedio < 1s")
    elif avg_response_time <= 3.0:
        print("⚠️  Bueno: Tiempo promedio < 3s")
    else:
        print("❌ Malo: Tiempo promedio > 3s")
    
    if summary['requests_per_second'] >= 10:
        print("✅ Excelente: > 10 requests/segundo")
    elif summary['requests_per_second'] >= 5:
        print("⚠️  Bueno: > 5 requests/segundo")
    else:
        print("❌ Malo: < 5 requests/segundo")


async def main():
    """Función principal"""
    try:
        result = await run_load_test()
        print_results(result)
        
        # Guardar resultados en archivo
        summary = result.get_summary()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"load_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Resultados guardados en: {filename}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando test: {e}")


if __name__ == "__main__":
    print("🧪 Load Testing para Backend SUNAT")
    print("Asegúrate de que el servidor esté ejecutándose en http://localhost:8080")
    print()
    
    # Confirmar antes de ejecutar
    response = input("¿Continuar con el test? (y/n): ")
    if response.lower() in ['y', 'yes', 's', 'si']:
        asyncio.run(main())
    else:
        print("Test cancelado.")