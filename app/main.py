"""Punto de entrada FastAPI - Backend SUNAT Emisión"""
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import HealthResponse
from app.utils.logger import logger
from app.services.worker_manager import worker_manager
from app.services.driver_semaphore import driver_semaphore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor del ciclo de vida de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando Backend SUNAT Emisión...")
    
    try:
        # Inicializar workers (no necesitamos inicializar pool)
        await worker_manager.start()
        
        logger.info("✅ Backend SUNAT listo para emisiones")
        
        yield  # La aplicación corre aquí
        
    finally:
        # Shutdown RÁPIDO - solo workers
        logger.info("🛑 Cerrando Backend SUNAT...")
        
        # Solo detener workers
        await worker_manager.stop()
        
        logger.info("✅ Backend SUNAT cerrado correctamente")


def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI"""
    app = FastAPI(
        title="Backend SUNAT Emisión",
        description="Microservicio especializado en emisión de comprobantes SUNAT",
        version=settings.version,
        lifespan=lifespan
    )
    
    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )
    
    logger.info(f"CORS configurado para orígenes: {settings.origins_list}")
    
    return app


# Crear aplicación
app = create_app()

# Solo rutas de emisión
from app.api.emission_routes import router as emission_router

app.include_router(emission_router)

# Tiempo de inicio del servidor
start_time = time.time()


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Backend SUNAT Emisión",
        "version": settings.version,
        "service": "emission-only",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check del servicio"""
    worker_status = await worker_manager.get_status()
    uptime = time.time() - start_time
    
    return HealthResponse(
        status="healthy",
        version=settings.version,
        selenium_ready=True,  # Siempre listo (no pool)
        active_tasks=worker_status["queue"]["processing"],
        uptime_seconds=uptime
    )


@app.get("/status", tags=["monitoring"])
async def system_status():
    """Estado detallado del sistema"""
    return await worker_manager.get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
