"""Script de inicio del Backend SUNAT Emisión"""
import sys
import signal
import uvicorn
from app.config import settings


def signal_handler(signum, frame):
    """Manejo de señales para cierre elegante"""
    print(f"Señal {signum} recibida, cerrando servidor...")
    sys.exit(0)


def main():
    """Función principal de inicio"""
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Backend SUNAT Emisión")
    print(f"Iniciando servidor en {settings.api_host}:{settings.api_port}")
    print(f"Documentación: http://{settings.api_host}:{settings.api_port}/docs")
    print("📋 Especializado en emisión de comprobantes SUNAT")
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True,  # Para desarrollo
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        print("👋 Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error ejecutando servidor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
