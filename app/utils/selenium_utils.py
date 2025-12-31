"""Utilidades para Selenium"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from app.utils.logger import logger
import os
from pathlib import Path

def configurar_driver(headless: bool = True) -> webdriver.Chrome:
    """Configura y retorna un WebDriver de Chrome"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Buscar chromedriver.exe en el directorio del proyecto
    project_root = Path(__file__).parent.parent.parent
    chromedriver_path = project_root / "chromedriver.exe"
    
    logger.info(f"Directorio del proyecto: {project_root}")
    logger.info(f"Buscando ChromeDriver en: {chromedriver_path}")
    logger.info(f"ChromeDriver existe: {chromedriver_path.exists()}")
    
    try:
        if chromedriver_path.exists():
            logger.info(f"Usando ChromeDriver local: {chromedriver_path}")
            logger.info(f"Tamaño del archivo: {chromedriver_path.stat().st_size} bytes")
            
            # Verificar que el archivo sea ejecutable
            import subprocess
            try:
                result = subprocess.run([str(chromedriver_path), "--version"], 
                                      capture_output=True, text=True, timeout=5)
                logger.info(f"ChromeDriver version: {result.stdout.strip()}")
            except Exception as e:
                logger.error(f"Error al verificar ChromeDriver: {e}")
            
            service = Service(str(chromedriver_path))
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("WebDriver configurado correctamente con ChromeDriver local")
            return driver
        else:
            logger.info("ChromeDriver local no encontrado, intentando usar PATH del sistema...")
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("WebDriver configurado correctamente usando PATH")
            return driver
    except Exception as e1:
        logger.error(f"Error al configurar WebDriver: {e1}")
        logger.error(f"Tipo de error: {type(e1).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Último intento con webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            logger.info("Intentando con webdriver-manager...")
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("WebDriver configurado con webdriver-manager")
            return driver
        except Exception as e2:
            logger.error(f"Error con webdriver-manager: {e2}")
            raise Exception(
                f"No se pudo configurar ChromeDriver.\n"
                f"Error 1: {e1}\n"
                f"Error 2: {e2}\n\n"
                f"Solución: Ejecuta 'python install_chromedriver.py' para instalar ChromeDriver"
            )
