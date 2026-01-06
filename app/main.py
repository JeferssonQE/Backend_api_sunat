"""Punto de entrada FastAPI"""
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uuid
from datetime import datetime
import time

from app.schemas import (
    EmisionRequest, TaskResponse, StatusResponse, HealthResponse, NotaCreditoRequest
)
from app.config import settings
from app.utils.logger import logger
from app.api.routes import router as downloads_router

app = FastAPI(
    title=settings.app_name,
    description="API REST para emisión de comprobantes en SUNAT",
    version=settings.version
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://frontend-factura-movil.vercel.app/"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Almacenamiento temporal de tareas
tasks_storage: Dict[str, dict] = {}

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
    active_tasks = len([t for t in tasks_storage.values() if t["status"] == "processing"])
    uptime = time.time() - start_time
    
    return HealthResponse(
        status="healthy",
        version=settings.version,
        selenium_ready=True,
        active_tasks=active_tasks,
        uptime_seconds=uptime
    )

@app.post("/api/v1/emitir", response_model=TaskResponse, status_code=202)
async def emitir_comprobante(
    request: EmisionRequest,
    background_tasks: BackgroundTasks
):
    """Envía un comprobante a SUNAT de forma asíncrona"""
    task_id = str(uuid.uuid4())
    
    # Guardar tarea en storage
    tasks_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "data": request.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None
    }
    
    # Agregar tarea en background
    background_tasks.add_task(process_emission, task_id, request.model_dump())
    
    logger.info(f"Tarea {task_id} creada para {request.tipo_documento}")
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Comprobante en cola para procesamiento",
        created_at=tasks_storage[task_id]["created_at"]
    )

@app.get("/api/v1/status/{task_id}", response_model=StatusResponse)
async def get_task_status(task_id: str):
    """Consulta el estado de una emisión"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    task = tasks_storage[task_id]
    
    duration = None
    if task["started_at"] and task["completed_at"]:
        start = datetime.fromisoformat(task["started_at"])
        end = datetime.fromisoformat(task["completed_at"])
        duration = (end - start).total_seconds()
    
    return StatusResponse(
        task_id=task["task_id"],
        status=task["status"],
        result=task["result"],
        started_at=task["started_at"],
        completed_at=task["completed_at"],
        duration_seconds=duration
    )

@app.post("/api/v1/validate")
async def validate_comprobante(request: EmisionRequest):
    """Valida datos antes de enviar (sin ejecutar scraping)"""
    warnings = []
    errors = []
    
    # Validar productos sin IGV
    for producto in request.productos:
        if producto.igv == 0:
            warnings.append(f"El producto '{producto.descripcion}' no tiene IGV")
    
    # Validar totales
    total_calculado = sum(p.precio_total for p in request.productos)
    if abs(total_calculado - request.resumen.total) > 0.01:
        errors.append(f"Total no coincide: calculado {total_calculado} vs declarado {request.resumen.total}")
    
    # Validar cliente según tipo de documento
    if request.tipo_documento == "BOLETA":
        if not request.cliente.dni and not request.cliente.nombre:
            errors.append("Boleta requiere DNI o nombre del cliente")
    elif request.tipo_documento == "FACTURA":
        if not request.cliente.ruc:
            errors.append("Factura requiere RUC del cliente")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

@app.post("/api/v1/nota-credito", response_model=TaskResponse, status_code=202)
async def emitir_nota_credito(
    request: NotaCreditoRequest,
    background_tasks: BackgroundTasks
):
    """Emite una nota de crédito en SUNAT de forma asíncrona"""
    task_id = str(uuid.uuid4())
    
    tasks_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "data": request.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None
    }
    
    background_tasks.add_task(process_nota_credito, task_id, request.model_dump())
    
    logger.info(f"Tarea {task_id} creada para NOTA_CREDITO - Boleta: {request.numero_boleta}")
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Nota de crédito en cola para procesamiento",
        created_at=tasks_storage[task_id]["created_at"]
    )

async def process_emission(task_id: str, data: dict):
    """Procesa la emisión del comprobante con Selenium"""
    try:
        # Actualizar estado
        tasks_storage[task_id]["status"] = "processing"
        tasks_storage[task_id]["started_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Procesando tarea {task_id}")
        
        # Importar y ejecutar scraper
        from app.services.scraper_service import send_billing_sunat
        result = send_billing_sunat(data)
        
        # Actualizar resultado
        if result.get("success"):
            tasks_storage[task_id]["status"] = "completed"
            tasks_storage[task_id]["result"] = result
        else:
            tasks_storage[task_id]["status"] = "failed"
            tasks_storage[task_id]["result"] = result
        
        tasks_storage[task_id]["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Tarea {task_id} completada con estado: {tasks_storage[task_id]['status']}")
        
    except Exception as e:
        logger.error(f"Error en tarea {task_id}: {str(e)}")
        tasks_storage[task_id]["status"] = "failed"
        tasks_storage[task_id]["completed_at"] = datetime.utcnow().isoformat()
        tasks_storage[task_id]["result"] = {
            "success": False,
            "error": str(e)
        }

async def process_nota_credito(task_id: str, data: dict):
    """Procesa la emisión de nota de crédito con Selenium"""
    try:
        tasks_storage[task_id]["status"] = "processing"
        tasks_storage[task_id]["started_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Procesando nota de crédito {task_id}")
        
        from app.services.nota_credito import send_nota_credito_sunat
        result = send_nota_credito_sunat(data)
        
        if result.get("success"):
            tasks_storage[task_id]["status"] = "completed"
            tasks_storage[task_id]["result"] = result
        else:
            tasks_storage[task_id]["status"] = "failed"
            tasks_storage[task_id]["result"] = result
        
        tasks_storage[task_id]["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Tarea {task_id} completada con estado: {tasks_storage[task_id]['status']}")
        
    except Exception as e:
        logger.error(f"Error en tarea {task_id}: {str(e)}")
        tasks_storage[task_id]["status"] = "failed"
        tasks_storage[task_id]["completed_at"] = datetime.utcnow().isoformat()
        tasks_storage[task_id]["result"] = {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
