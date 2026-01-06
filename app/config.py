"""Configuración de la aplicación"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "SUNAT Billing API"
    version: str = "1.0.0"
    sunat_url: str = "https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    task_timeout: int = 300
    chrome_headless: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
