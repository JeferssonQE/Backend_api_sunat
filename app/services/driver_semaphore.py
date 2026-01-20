"""Semáforo simple para limitar drivers concurrentes"""
import asyncio
from app.config import settings
from app.utils.logger import logger


class DriverSemaphore:
    """Contador simple para controlar máximo de drivers concurrentes"""
    
    def __init__(self, max_drivers: int = None):
        self.max_drivers = max_drivers or settings.max_workers
        self.active_count = 0
        self.lock = asyncio.Lock()
        
    async def acquire(self) -> bool:
        """
        Intenta adquirir permiso para crear driver
        
        Returns:
            True si se puede crear driver, False si está lleno
        """
        async with self.lock:
            if self.active_count >= self.max_drivers:
                logger.warning(f"Max drivers reached ({self.max_drivers}), rejecting request")
                return False
            
            self.active_count += 1
            logger.info(f"Driver permit acquired ({self.active_count}/{self.max_drivers})")
            return True
    
    async def release(self):
        """Libera permiso de driver"""
        async with self.lock:
            self.active_count = max(0, self.active_count - 1)
            logger.info(f"Driver permit released ({self.active_count}/{self.max_drivers})")
    
    def get_status(self) -> dict:
        """Obtiene estado actual del semáforo"""
        return {
            "max_drivers": self.max_drivers,
            "active_drivers": self.active_count,
            "available_permits": self.max_drivers - self.active_count
        }


# Instancia global
driver_semaphore = DriverSemaphore()