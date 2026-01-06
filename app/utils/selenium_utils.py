"""Utilidades para Selenium"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from app.utils.logger import logger
import os
from pathlib import Path

def configurar_driver(headless: bool = True, download_dir: str = None) -> webdriver.Chrome:
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
    
    if chromedriver_path.exists():
        logger.info(f"Usando ChromeDriver local: {chromedriver_path}")
        service = Service(str(chromedriver_path))
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✓ WebDriver configurado correctamente")
        return driver
    else:
        logger.info("ChromeDriver local no encontrado, usando PATH del sistema...")
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("✓ WebDriver configurado correctamente")
        return driver
