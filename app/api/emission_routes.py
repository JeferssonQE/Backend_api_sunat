"""Rutas de emisión de comprobantes"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from datetime import datetime
import uuid

from app.schemas import (
    EmisionRequest, 
    TaskResponse, 
    StatusResponse, 
    NotaCreditoRequest
)
from app.utils.logger import logger
from app.utils.task_storage import TemporaryTaskStorage
from app.services.task_processor import TaskProcessor
from app.services.credential_service import CredentialService, CredentialError


# Router para emisión
router = APIRouter(prefix="/api/v1", tags=["emission"])

# Storage y processor (se inyectarán desde main.py)
tasks_storage: TemporaryTaskStorage = None
task_processor: TaskProcessor = None


def init_emission_routes(storage: TemporaryTaskStorage, processor: TaskProcessor):
    """
    Inicializa las dependencias del router.
    
    Args:
        storage: Instancia del storage temporal
        processor: Instancia del procesador de tareas
    """
    global tasks_storage, task_processor
    tasks_storage = storage
    task_processor = processor


@router.post("/emitir", response_model=TaskResponse, status_code=202)
async def emitir_comprobante(
    request: EmisionRequest,
    background_tasks: BackgroundTasks
):
    """Envía un comprobante a SUNAT de forma asíncrona"""
    task_id = str(uuid.uuid4())
    
    try:
        # Desencriptar y validar credenciales (ÚNICO formato aceptado)
        credenciales = CredentialService.decrypt_and_validate(
            request.credenciales_encrypted.model_dump()
        )
        logger.info(
            f"Procesando credenciales para {request.tipo_documento} "
            f"con credenciales: {CredentialService.sanitize_for_log(credenciales)}"
        )
        
    except CredentialError as e:
        logger.error(f"Error procesando credenciales: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Preparar datos para la tarea
    data = request.model_dump()
    data["credenciales"] = credenciales
    # Eliminar versión encriptada
    data.pop("credenciales_encrypted", None)
    
    # Guardar tarea en storage temporal
    task_data = {
        "task_id": task_id,
        "status": "pending",
        "data": data,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None
    }
    tasks_storage.set(task_id, task_data)
    
    # Log sanitizado (sin mostrar credenciales)
    sanitized_creds = CredentialService.sanitize_for_log(credenciales)
    logger.info(
        f"Tarea {task_id} creada para {request.tipo_documento} "
        f"con credenciales: {sanitized_creds}"
    )
    
    # Agregar tarea en background
    background_tasks.add_task(
        task_processor.process_emission, 
        task_id, 
        data
    )
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Comprobante en cola para procesamiento",
        created_at=task_data["created_at"]
    )


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_task_status(task_id: str):
    """Consulta el estado de una emisión"""
    task = tasks_storage.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404, 
            detail="Tarea no encontrada o expirada. Las tareas se mantienen por 1 hora."
        )
    
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


@router.post("/nota-credito", response_model=TaskResponse, status_code=202)
async def emitir_nota_credito(
    request: NotaCreditoRequest,
    background_tasks: BackgroundTasks
):
    """Emite una nota de crédito en SUNAT de forma asíncrona"""
    task_id = str(uuid.uuid4())
    
    try:
        # Desencriptar y validar credenciales (ÚNICO formato aceptado)
        credenciales = CredentialService.decrypt_and_validate(
            request.credenciales_encrypted.model_dump()
        )
        
    except CredentialError as e:
        logger.error(f"Error procesando credenciales: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Preparar datos para la tarea
    data = request.model_dump()
    data["credenciales"] = credenciales
    # Eliminar versión encriptada
    data.pop("credenciales_encrypted", None)
    
    task_data = {
        "task_id": task_id,
        "status": "pending",
        "data": data,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "result": None
    }
    tasks_storage.set(task_id, task_data)
    
    # Log sanitizado (sin mostrar credenciales)
    sanitized_creds = CredentialService.sanitize_for_log(credenciales)
    logger.info(
        f"Tarea {task_id} creada para NOTA_CREDITO "
        f"Boleta: {request.numero_boleta} "
        f"con credenciales: {sanitized_creds}"
    )
    
    background_tasks.add_task(
        task_processor.process_nota_credito,
        task_id,
        data
    )
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Nota de crédito en cola para procesamiento",
        created_at=task_data["created_at"]
    )
