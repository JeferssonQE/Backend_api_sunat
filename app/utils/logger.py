"""Configuración de logging"""
import logging
import sys
from pathlib import Path

def setup_logger(name: str = "sunat_api", level: str = "INFO") -> logging.Logger:
    """Configura y retorna un logger"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Agregar handler
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger

# Logger global
logger = setup_logger()
