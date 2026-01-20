"""Gestor de workers para procesamiento de tareas"""
import asyncio
from typing import List, Optional
from datetime import datetime

from app.services.queue_manager import queue_manager
from app.services.scraper_service import send_billing_sunat_async, send_nota_credito_sunat
from app.services.driver_semaphore import driver_semaphore
from app.utils.logger import logger
from app.config import settings


class WorkerManager:
    """Gestor de workers que procesan tareas de la cola Redis"""
    
    def __init__(self, num_workers: int = None):
        """
        Inicializa el gestor de workers.
        
        Args:
            num_workers: Número de workers (por defecto usa settings.max_workers)
        """
        self.num_workers = num_workers or settings.max_workers
        self.workers: List[asyncio.Task] = []
        self.running = False
        
    async def start(self) -> None:
        """Inicia todos los workers"""
        if self.running:
            logger.warning("Workers ya están ejecutándose")
            return
        
        self.running = True
        logger.info(f"Iniciando {self.num_workers} workers...")
        
        # Crear y iniciar workers
        for i in range(self.num_workers):
            worker_task = asyncio.create_task(
                self._worker_loop(worker_id=i+1)
            )
            self.workers.append(worker_task)
        
        logger.info(f"✅ {self.num_workers} workers iniciados")
    
    async def stop(self) -> None:
        """Detiene todos los workers de forma elegante y rápida"""
        if not self.running:
            return
        
        logger.info("Deteniendo workers...")
        self.running = False
        
        # Cancelar todos los workers
        for i, worker in enumerate(self.workers, 1):
            worker.cancel()
            logger.info(f"Worker {i} cancelado")
        
        # Esperar que terminen (máximo 5 segundos para ser más rápido)
        if self.workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.workers, return_exceptions=True),
                    timeout=5.0
                )
                logger.info("Workers terminados correctamente")
            except asyncio.TimeoutError:
                logger.warning("Timeout esperando workers (5s), continuando...")
        
        # Limpiar lista de workers
        for i, worker in enumerate(self.workers, 1):
            if not worker.done():
                logger.warning(f"Worker {i} aún corriendo, será forzado")
            logger.info(f"Worker {i} terminado")
        
        self.workers.clear()
        logger.info("✅ Workers detenidos")
    
    async def _worker_loop(self, worker_id: int) -> None:
        """
        Loop principal de un worker.
        
        Args:
            worker_id: ID del worker para logging
        """
        logger.info(f"Worker {worker_id} iniciado")
        
        while self.running:
            try:
                # Obtener tarea de la cola (espera 10 segundos)
                task = await queue_manager.dequeue_task(timeout=10)
                
                if task is None:
                    # No hay tareas, continuar esperando
                    continue
                
                task_id = task["task_id"]
                logger.info(f"Worker {worker_id} procesando tarea {task_id}")
                
                # Procesar tarea con timeout
                try:
                    result = await asyncio.wait_for(
                        self._process_task(task, worker_id),
                        timeout=settings.worker_timeout
                    )
                    
                    # Marcar como completada
                    await queue_manager.complete_task(task_id, result)
                    logger.info(f"Worker {worker_id} completó tarea {task_id}")
                    
                except asyncio.TimeoutError:
                    # Timeout en la tarea
                    error_msg = f"Timeout después de {settings.worker_timeout}s"
                    await queue_manager.fail_task(task_id, error_msg)
                    logger.error(f"Worker {worker_id} timeout en tarea {task_id}")
                
                except Exception as e:
                    # Error en el procesamiento
                    await queue_manager.fail_task(task_id, str(e))
                    logger.error(f"Worker {worker_id} error en tarea {task_id}: {e}")
                
            except asyncio.CancelledError:
                # Worker cancelado, salir del loop
                logger.info(f"Worker {worker_id} cancelado")
                break
                
            except Exception as e:
                # Error inesperado, continuar con siguiente tarea
                logger.error(f"Worker {worker_id} error inesperado: {e}")
                await asyncio.sleep(1)  # Pausa antes de continuar
        
        logger.info(f"Worker {worker_id} terminado")
    
    async def _process_task(self, task: dict, worker_id: int) -> dict:
        """
        Procesa una tarea individual.
        
        Args:
            task: Datos de la tarea
            worker_id: ID del worker
            
        Returns:
            Resultado del procesamiento
        """
        task_data = task["data"]
        
        # Transformar datos del endpoint al formato que espera el scraper
        if "type" in task_data and "invoice" in task_data and "sender" in task_data:
            # Formato del endpoint: {type, invoice, sender}
            invoice_data = task_data["invoice"]
            sender_data = task_data["sender"]
            
            # Transformar al formato que espera send_billing_sunat
            scraper_data = {
                "tipo_documento": invoice_data.get("tipo_documento", "BOLETA"),
                "cliente": invoice_data.get("cliente", {}),
                "productos": invoice_data.get("productos", []),
                "resumen": invoice_data.get("resumen", {}),
                "fecha": invoice_data.get("fecha", ""),
                "credenciales": {
                    "ruc": sender_data.get("ruc", ""),
                    "usuario": sender_data.get("sunat_user", ""),
                    "password": sender_data.get("sunat_pass", "")
                }
            }
            
            task_type = scraper_data["tipo_documento"]
            logger.info(f"Worker {worker_id} procesando {task_type} (transformado)")
            
        else:
            # Formato directo del scraper
            scraper_data = task_data
            task_type = task_data.get("tipo_documento", "UNKNOWN")
            logger.info(f"Worker {worker_id} procesando {task_type} (directo)")
        
        # Procesar según tipo de documento
        if task_type in ["BOLETA", "FACTURA"]:
            # USAR LA FUNCIÓN ASYNC que usa el pool correctamente
            result = await send_billing_sunat_async(scraper_data)
        elif task_type == "NOTA_CREDITO":
            # Usar función de nota de crédito
            result = await asyncio.get_event_loop().run_in_executor(
                None, send_nota_credito_sunat, task_data
            )
        else:
            raise ValueError(f"Tipo de documento no soportado: {task_type}")
        
        logger.debug(f"Worker {worker_id} completó procesamiento")
        return result
    
    async def get_status(self) -> dict:
        """
        Obtiene el estado actual de los workers.
        
        Returns:
            Estado de los workers y cola
        """
        queue_stats = await queue_manager.get_queue_stats()
        
        return {
            "workers": {
                "total": self.num_workers,
                "running": self.running,
                "active_tasks": len([w for w in self.workers if not w.done()])
            },
            "queue": queue_stats,
            "driver_semaphore": driver_semaphore.get_status()
        }


# Instancia global
worker_manager = WorkerManager()