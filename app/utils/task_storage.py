"""Storage temporal para tareas en memoria"""
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional


class TemporaryTaskStorage:
    """
    Storage temporal con límite de tamaño y tiempo.
    
    NOTA: Este storage es temporal y se pierde al reiniciar.
    El frontend debe guardar los resultados en Supabase para persistencia permanente.
    """
    
    def __init__(self, max_size: int = 100, max_age_hours: int = 1):
        """
        Inicializa el storage temporal.
        Args:
            max_size: Número máximo de tareas a mantener en memoria
            max_age_hours: Tiempo máximo de vida de una tarea en horas
        """
        self.storage: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.max_age = timedelta(hours=max_age_hours)
    
    def set(self, task_id: str, data: dict) -> None:
        """
        Guarda tarea con limpieza automática.
        Args:
            task_id: ID único de la tarea
            data: Datos de la tarea
        """
        self._cleanup()
        
        if len(self.storage) >= self.max_size:
            self.storage.popitem(last=False)  # Eliminar la más antigua
        
        self.storage[task_id] = data
    
    def get(self, task_id: str) -> Optional[dict]:
        """
        Obtiene tarea por ID.
        Args:
            task_id: ID de la tarea
        Returns:
            Datos de la tarea o None si no existe
        """
        self._cleanup()
        return self.storage.get(task_id)
    
    def _cleanup(self) -> None:
        """Elimina tareas antiguas basándose en max_age"""
        now = datetime.utcnow()
        to_delete = []
        
        for task_id, data in self.storage.items():
            created = datetime.fromisoformat(data["created_at"])
            if now - created > self.max_age:
                to_delete.append(task_id)
        
        for task_id in to_delete:
            del self.storage[task_id]
    
    def count(self) -> int:
        """
        Cuenta tareas activas después de limpieza.
        
        Returns:
            Número de tareas activas
        """
        self._cleanup()
        return len(self.storage)
    
    def get_all_tasks(self) -> list[dict]:
        """
        Obtiene todas las tareas activas.
        
        Returns:
            Lista de todas las tareas
        """
        self._cleanup()
        return [self.storage[tid] for tid in list(self.storage.keys())]
