"""Punto de entrada FastAPI"""
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import HealthResponse
from app.utils.logger import logger
from app.utils.task_storage import TemporaryTaskStorage
from app.services.task_processor import TaskProcessor
from app.api.emission_routes import router as emission_router, init_emission_routes


def create_app() -> FastAPI:
    """
    Factory para crear la aplicación FastAPI.
    
    Returns:
        Instancia configurada de FastAPI
    """
    app = FastAPI(
        title=settings.app_name,
        description="API REST para emisión de comprobantes en SUNAT",
        version=settings.version
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

# Inicializar dependencias
tasks_storage = TemporaryTaskStorage(max_size=100, max_age_hours=1)
task_processor = TaskProcessor(tasks_storage)

# Inicializar rutas con dependencias
init_emission_routes(tasks_storage, task_processor)

# Registrar routers
app.include_router(emission_router)

# Tiempo de inicio del servidor
start_time = time.time()


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": settings.app_name,
        "version": settings.version,
        "docs": "/docs"
    }


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check del servicio"""
    all_tasks = tasks_storage.get_all_tasks()
    active_tasks = len([t for t in all_tasks if t.get("status") == "processing"])
    uptime = time.time() - start_time
    
    return HealthResponse(
        status="healthy",
        version=settings.version,
        selenium_ready=True,
        active_tasks=active_tasks,
        uptime_seconds=uptime
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
