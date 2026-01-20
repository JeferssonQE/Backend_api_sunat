"""Cliente Supabase para la aplicación"""
from supabase import create_client, Client
from typing import Optional
from app.config import settings
from app.utils.logger import logger


class SupabaseClient:
    """Cliente Supabase singleton"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_instance(cls) -> Client:
        """
        Obtiene la instancia singleton de Supabase.
        
        Returns:
            Cliente de Supabase
        """
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    settings.supabase_url,
                    settings.supabase_anon_key
                )
                logger.info("Cliente Supabase inicializado")
            except Exception as e:
                logger.error(f"Error inicializando Supabase: {e}")
                raise
        
        return cls._instance


# Instancia global
supabase_client = SupabaseClient.get_instance