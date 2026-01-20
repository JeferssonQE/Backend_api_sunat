"""Cliente Redis singleton para la aplicación"""
import redis
from typing import Optional
from app.config import settings
from app.utils.logger import logger


class RedisClient:
    """Cliente Redis singleton"""
    
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_instance(cls) -> redis.Redis:
        """
        Obtiene la instancia singleton de Redis.
        
        Returns:
            Instancia de Redis
        """
        if cls._instance is None:
            try:
                cls._instance = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=10,
                    socket_timeout=30,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                cls._instance.ping()
                logger.info("Conexión a Redis establecida")
            except Exception as e:
                logger.error(f"Error conectando a Redis: {e}")
                raise
        
        return cls._instance
    
    @classmethod
    def close(cls) -> None:
        """Cierra la conexión Redis"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            logger.info("Conexión Redis cerrada")


# Instancia global
redis_client = RedisClient.get_instance