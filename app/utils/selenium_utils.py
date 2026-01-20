"""Utilidades para Selenium"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from app.utils.logger import logger
from app.config import settings
import os
from pathlib import Path
import random

def configurar_driver(headless: bool = True, download_dir: str = None) -> webdriver.Chrome:
    """Configura y retorna un WebDriver de Chrome"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Usar opciones del .env si están disponibles
    if settings.chrome_options:
        for option in settings.chrome_options.split(","):
            option = option.strip()
            if option:
                chrome_options.add_argument(option)
                logger.info(f"Agregando opción Chrome: {option}")
    else:
        # Opciones por defecto si no hay en .env
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
    
    # Opciones adicionales para mejorar conectividad
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--ignore-certificate-errors-spki-list")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-default-apps")
    
    # IMPORTANTE: Puerto único para cada instancia
    debug_port = random.randint(9223, 9300)
    chrome_options.add_argument(f"--remote-debugging-port={debug_port}")
    
    # Directorio de datos único para cada instancia
    user_data_dir = f"/tmp/chrome_data_{debug_port}"
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Configurar directorio de descarga si se proporciona
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        logger.info(f"Directorio de descarga configurado: {download_dir}")
    
    # Buscar chromedriver.exe en el directorio del proyecto
    project_root = Path(__file__).parent.parent.parent
    chromedriver_path = project_root / "chromedriver.exe"
    
    try:
        if chromedriver_path.exists():
            logger.info(f"Usando ChromeDriver local: {chromedriver_path}")
            service = Service(str(chromedriver_path))
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            logger.info("ChromeDriver local no encontrado, usando PATH del sistema...")
            driver = webdriver.Chrome(options=chrome_options)
        
        # Configurar timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
        logger.info(f"✓ WebDriver configurado correctamente (puerto: {debug_port})")
        return driver
        
    except Exception as e:
        logger.error(f"Error configurando WebDriver: {e}")
        raise
