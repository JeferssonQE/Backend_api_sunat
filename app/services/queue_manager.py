"""Gestor de cola Redis para tareas de emisión - Versión optimizada"""
import json
import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime

from app.utils.redis_client import RedisClient
from app.utils.logger import logger


class QueueManager:
    """Gestor de cola Redis optimizado para MVP"""
    
    QUEUE_KEY = "sunat:tasks:pending"
    PROCESSING_KEY = "sunat:tasks:processing"
    
    def __init__(self):
        """Inicializa el gestor de cola"""
        self._redis = None
    
    @property
    def redis(self):
        """Obtiene la instancia de Redis de forma lazy"""
        if self._redis is None:
            self._redis = RedisClient.get_instance()
        return self._redis
    
    async def enqueue_task(self, task_data: Dict) -> str:
        """
        Encola una nueva tarea.
        
        Args:
            task_data: Datos de la tarea
            
        Returns:
            ID de la tarea
        """
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "data": task_data,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0
        }
        
        try:
            # Ejecutar en thread pool para evitar bloqueo
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.redis.lpush(self.QUEUE_KEY, json.dumps(task))
            )
            logger.info(f"Tarea {task_id} encolada")
            return task_id
            
        except Exception as e:
            logger.error(f"Error encolando tarea: {e}")
            raise
    
    async def dequeue_task(self, timeout: int = 10) -> Optional[Dict]:
        """
        Obtiene la siguiente tarea de la cola.
        
        Args:
            timeout: Tiempo de espera en segundos
            
        Returns:
            Datos de la tarea o None si no hay tareas
        """
        try:
            # Ejecutar brpop en thread pool para evitar bloqueo del event loop
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.brpop(self.QUEUE_KEY, timeout=timeout)
            )
            
            if result:
                _, task_json = result
                task = json.loads(task_json)
                
                # Mover a processing
                task["started_at"] = datetime.utcnow().isoformat()
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.hset(
                        self.PROCESSING_KEY, 
                        task["task_id"], 
                        json.dumps(task)
                    )
                )
                
                logger.debug(f"Tarea {task['task_id']} obtenida de la cola")
                return task
                
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo tarea de la cola: {e}")
            return None
    
    async def complete_task(self, task_id: str, result: Dict) -> None:
        """
        Marca una tarea como completada.
        
        Args:
            task_id: ID de la tarea
            result: Resultado de la tarea
        """
        try:
            # Obtener tarea de processing
            task_json = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.hget(self.PROCESSING_KEY, task_id)
            )
            
            if task_json:
                task = json.loads(task_json)
                task["completed_at"] = datetime.utcnow().isoformat()
                task["result"] = result
                task["status"] = "completed" if result.get("success") else "failed"
                
                # Guardar resultado y remover de processing en paralelo
                await asyncio.gather(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.redis.setex(
                            f"sunat:result:{task_id}",
                            3600,  # 1 hora
                            json.dumps(task)
                        )
                    ),
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.redis.hdel(self.PROCESSING_KEY, task_id)
                    )
                )
                
                logger.info(f"Tarea {task_id} completada: {task['status']}")
            
        except Exception as e:
            logger.error(f"Error completando tarea {task_id}: {e}")
    
    async def fail_task(self, task_id: str, error: str) -> None:
        """
        Marca una tarea como fallida.
        
        Args:
            task_id: ID de la tarea
            error: Mensaje de error
        """
        result = {
            "success": False,
            "error": error
        }
        await self.complete_task(task_id, result)
    
    async def get_task_result(self, task_id: str) -> Optional[Dict]:
        """
        Obtiene el resultado de una tarea.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Resultado de la tarea o None si no existe
        """
        try:
            # Buscar en resultados completados
            result_json = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.get(f"sunat:result:{task_id}")
            )
            
            if result_json:
                return json.loads(result_json)
            
            # Buscar en processing
            task_json = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.hget(self.PROCESSING_KEY, task_id)
            )
            
            if task_json:
                task = json.loads(task_json)
                task["status"] = "processing"
                return task
            
            # No encontrada
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo resultado de tarea {task_id}: {e}")
            return None
    
    async def get_queue_stats(self) -> Dict:
        """
        Obtiene estadísticas de la cola.
        
        Returns:
            Estadísticas de la cola
        """
        try:
            # Ejecutar ambas operaciones en paralelo
            pending, processing = await asyncio.gather(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.redis.llen(self.QUEUE_KEY)
                ),
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.redis.hlen(self.PROCESSING_KEY)
                )
            )
            
            return {
                "pending": pending,
                "processing": processing,
                "total": pending + processing
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {"pending": 0, "processing": 0, "total": 0}


# Instancia global
queue_manager = QueueManager()