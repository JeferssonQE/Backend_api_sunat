"""Procesamiento de tareas de emisión de comprobantes"""
from datetime import datetime
from typing import Dict

from app.utils.logger import logger
from app.utils.task_storage import TemporaryTaskStorage


class TaskProcessor:
    """Procesador de tareas de emisión de comprobantes"""
    
    def __init__(self, storage: TemporaryTaskStorage):
        """
        Inicializa el procesador de tareas.
        
        Args:
            storage: Instancia del storage temporal
        """
        self.storage = storage
    
    async def process_emission(self, task_id: str, data: Dict) -> None:
        """
        Procesa la emisión del comprobante con Selenium.
        
        Args:
            task_id: ID de la tarea
            data: Datos del comprobante a emitir
        """
        try:
            # Actualizar estado a processing
            self._update_task_status(task_id, "processing", started=True)
            
            logger.info(f"Procesando tarea {task_id}")
            
            # Importar y ejecutar scraper
            from app.services.scraper_service import send_billing_sunat
            result = send_billing_sunat(data)
            
            # Actualizar resultado
            status = "completed" if result.get("success") else "failed"
            self._update_task_result(task_id, status, result)
            
            logger.info(f"Tarea {task_id} completada con estado: {status}")
            
        except Exception as e:
            logger.error(f"Error en tarea {task_id}: {str(e)}")
            self._update_task_result(
                task_id, 
                "failed", 
                {"success": False, "error": str(e)}
            )
    
    async def process_nota_credito(self, task_id: str, data: Dict) -> None:
        """
        Procesa la emisión de nota de crédito con Selenium.
        
        Args:
            task_id: ID de la tarea
            data: Datos de la nota de crédito
        """
        try:
            self._update_task_status(task_id, "processing", started=True)
            
            logger.info(f"Procesando nota de crédito {task_id}")
            
            from app.services.nota_credito import send_nota_credito_sunat
            result = send_nota_credito_sunat(data)
            
            status = "completed" if result.get("success") else "failed"
            self._update_task_result(task_id, status, result)
            
            logger.info(f"Tarea {task_id} completada con estado: {status}")
            
        except Exception as e:
            logger.error(f"Error en tarea {task_id}: {str(e)}")
            self._update_task_result(
                task_id,
                "failed",
                {"success": False, "error": str(e)}
            )
    
    def _update_task_status(
        self, 
        task_id: str, 
        status: str, 
        started: bool = False
    ) -> None:
        """
        Actualiza el estado de una tarea.
        
        Args:
            task_id: ID de la tarea
            status: Nuevo estado
            started: Si True, actualiza started_at
        """
        task = self.storage.get(task_id)
        if task:
            task["status"] = status
            if started:
                task["started_at"] = datetime.utcnow().isoformat()
            self.storage.set(task_id, task)
    
    def _update_task_result(
        self, 
        task_id: str, 
        status: str, 
        result: Dict
    ) -> None:
        """
        Actualiza el resultado de una tarea.
        
        Args:
            task_id: ID de la tarea
            status: Estado final
            result: Resultado de la operación
        """
        task = self.storage.get(task_id)
        if task:
            task["status"] = status
            task["result"] = result
            task["completed_at"] = datetime.utcnow().isoformat()
            self.storage.set(task_id, task)
