"""Configuración de la aplicación"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # Aplicación
    app_name: str = "SUNAT Billing API"
    version: str = "1.0.0"
    log_level: str = "INFO"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080  
    
    # CORS - Orígenes permitidos (separados por coma en .env)
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    
    # SUNAT
    sunat_url: str = "https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm"
    
    # Selenium
    chrome_headless: bool = True
    task_timeout: int = 300
    
    # Encriptación - Clave para desencriptar credenciales del frontend
    encryption_key: str = "CAMBIAR_EN_PRODUCCION"
    
    class Config:
        env_file = ".env"
    
    @property
    def origins_list(self) -> List[str]:
        """
        Convierte la cadena de orígenes en una lista.
        
        Returns:
            Lista de orígenes permitidos
        """
        return [
            origin.strip() 
            for origin in self.allowed_origins.split(",") 
            if origin.strip()
        ]


settings = Settings()
