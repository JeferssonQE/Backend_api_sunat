"""Configuración del Backend SUNAT Emisión"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuración especializada para emisión SUNAT"""
    
    # Aplicación
    app_name: str = "Backend SUNAT Emisión"
    version: str = "1.0.0"
    log_level: str = "INFO"
    
    # API - Puerto diferente para separar servicios
    api_host: str = "0.0.0.0"
    api_port: int = 8001  # Puerto 8001 para Backend SUNAT
    
    # CORS - Permitir comunicación con Backend Factura Móvil
    allowed_origins: str = "http://localhost:8000,http://localhost:5173,http://localhost:3000"
    
    # SUNAT - SIN valor por defecto para que lea del .env
    sunat_url: str
    
    # Selenium - SIN valores por defecto para que lea del .env
    chrome_headless: bool = True
    task_timeout: int = 300
    chrome_options: str = ""
    
    # Redis (opcional para este microservicio)
    redis_url: str = "redis://localhost:6379/1"  # DB diferente
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1
    
    # Workers - SIN valores por defecto para que lea del .env
    max_workers: int = 3
    worker_timeout: int = 300
    
    # Comunicación con Backend Factura Móvil
    factura_backend_url: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # IGNORAR variables extra del .env
    
    @property
    def origins_list(self) -> List[str]:
        """Convierte la cadena de orígenes en una lista"""
        return [
            origin.strip() 
            for origin in self.allowed_origins.split(",") 
            if origin.strip()
        ]


settings = Settings()
