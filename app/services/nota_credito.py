"""Servicio de scraping para Notas de Crédito en SUNAT"""
import os
import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.utils.logger import logger
from app.services.scraper_service import iniciar_sesion, descargar_pdf
from app.utils.selenium_utils import configurar_driver
from app.config import settings


class NotaCreditoError(Exception):
    """Error base para notas de crédito"""
    pass


class EmissionNotaCreditoError(NotaCreditoError):
    """Error al emitir nota de crédito"""
    pass



MOTIVOS_NOTA_CREDITO = {
    "01": "Anulacion de la Operacion",
    "02": "Anulacion por Error en el RUC",
    "03": "Devolucion Total",
    "04": "Correccion por error en la descripcion",
    "05": "Devolucion por item"
}


def extraer_numero_boleta(numero_completo: str) -> str:
    """Extrae solo el número de la boleta sin la serie"""
    if "-" in numero_completo:
        numero_solo = numero_completo.split("-")[1]
        logger.info(f"Número completo: {numero_completo} → Número extraído: {numero_solo}")
        return numero_solo
    
    logger.warning(f"Número sin guion detectado: {numero_completo}")
    return numero_completo


def navegar_a_emision_nota_credito(driver) -> None:
    """Navega al formulario de emisión de nota de crédito"""
    campo_busqueda = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "txtBusca"))
    )
    campo_busqueda.clear()
    campo_busqueda.send_keys("BOLETA")
    logger.info("Búsqueda de BOLETA realizada")
    
    emitir_nc_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="nivel4_11_5_4_1_2"]/span'))
    )
    emitir_nc_button.click()
    logger.info("Navegación a 'Emitir Nota de Crédito' completada")
    
    WebDriverWait(driver, 20).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeApplication"))
    )
    logger.info("Cambio a iframe realizado")


def ingresar_fecha_emision(driver, fecha: str) -> None:
    """Ingresa la fecha de emisión de la nota de crédito"""
    input_fecha = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "pantallaInicial.fechaEmision"))
    )
    input_fecha.clear()
    input_fecha.send_keys(fecha)
    input_fecha.send_keys(Keys.TAB)
    logger.info(f"Fecha de emisión ingresada: {fecha}")


def seleccionar_motivo_nota_credito(driver, tipo_nota: str) -> None:
    """Selecciona el motivo de la nota de crédito"""
    texto_motivo = MOTIVOS_NOTA_CREDITO.get(tipo_nota, "Devolucion Total")
    
    input_motivo = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "pantallaInicial.tipoNotaCredito"))
    )
    input_motivo.clear()
    input_motivo.send_keys(texto_motivo)
    input_motivo.send_keys(Keys.RETURN)
    
    logger.info(f"Motivo seleccionado: {texto_motivo}")
    time.sleep(2)


def ingresar_numero_boleta(driver, numero_boleta: str) -> None:
    """Ingresa el número de la boleta a anular"""
    input_numero_boleta = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "pantallaInicial.numeroBVE"))
    )
    
    numero_solo = extraer_numero_boleta(numero_boleta)
    input_numero_boleta.send_keys(numero_solo)
    input_numero_boleta.send_keys(Keys.TAB)
    
    logger.info(f"Número de boleta ingresado: {numero_solo}")


def ingresar_sustento(driver, sustento: str) -> None:
    """Ingresa el sustento de la nota de crédito"""
    input_sustento = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "pantallaInicial.motivoEmisionNC"))
    )
    input_sustento.send_keys(sustento)
    logger.info(f"Sustento ingresado: {sustento}")


def emitir_nota_credito(driver, data: dict) -> None:
    """Emite una nota de crédito en SUNAT"""
    try:
        logger.info("Iniciando emisión de nota de crédito")
        
        navegar_a_emision_nota_credito(driver)
        ingresar_fecha_emision(driver, data["fecha_emision"])
        seleccionar_motivo_nota_credito(driver, data.get("tipo_nota", "01"))
        ingresar_numero_boleta(driver, data["numero_boleta"])
        ingresar_sustento(driver, data["sustento"])
        
        continuar_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "pantallaInicial.btnContinuar_label"))
        )
        continuar_button.click()
        
        logger.info("Nota de crédito cargada correctamente")
        
    except Exception as e:
        logger.error(f"Error al emitir nota de crédito: {e}")
        raise EmissionNotaCreditoError(f"No se pudo emitir nota de crédito: {e}")



def completar_emision_nota_credito(driver) -> bool:
    """Completa el proceso de emisión de la nota de crédito"""
    try:
        logger.info("Completando emisión de nota de crédito")
        
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "notaCredito-preliminar.botonGrabarDocumento_label"))
        )
        emitir_button.click()
        
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.ID, "waitMessage_underlay"))
        )
        logger.info("Emisión preliminar confirmada")
        
        confirmar_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "dlgBtnAceptarConfirm_label"))
        )
        confirmar_button.click()
        
        logger.info("Nota de crédito emitida correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error al completar emisión de nota de crédito: {e}")
        raise EmissionNotaCreditoError(f"No se pudo completar la emisión: {e}")



def send_nota_credito_sunat(data: dict) -> dict:
    """Función principal para enviar nota de crédito a SUNAT"""
    driver = None
    try:
        logger.info("Iniciando proceso de emisión de nota de crédito")
        
        download_dir = os.path.join(os.getcwd(), "downloads")
        driver = configurar_driver(headless=settings.chrome_headless, download_dir=download_dir)
        
        iniciar_sesion(driver, data["credenciales"])
        emitir_nota_credito(driver, data)
        completar_emision_nota_credito(driver)
        
        pdf_data = None
        try:
            pdf_data = descargar_pdf(
                driver,
                "NOTA_CREDITO",
                data["credenciales"]["ruc"],
                download_dir
            )
        except Exception as e:
            logger.warning(f"No se pudo descargar el PDF: {e}")
        
        logger.info("Proceso completado exitosamente")
        
        result = {
            "success": True,
            "message": "Nota de crédito emitida correctamente",
            "numero_boleta": data["numero_boleta"],
            "fecha_emision": data["fecha_emision"],
            "tipo_nota": data.get("tipo_nota", "01")
        }
        
        if pdf_data:
            result["pdf"] = pdf_data
            logger.info(f"PDF incluido en respuesta: {pdf_data['filename']}")
        else:
            logger.warning("PDF no disponible en la respuesta")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en emisión de nota de crédito: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if driver:
            driver.quit()
            logger.info("Driver cerrado")



if __name__ == "__main__":
    """Script de prueba para emitir nota de crédito"""
    print("=" * 70)
    print("TEST - Nota de Crédito SUNAT")
    print("=" * 70)
    
    test_data = {
        "fecha_emision": datetime.now().strftime("%d/%m/%Y"),
        "tipo_nota": "01",
        "numero_boleta": "EB01-448",
        "sustento": "Cliente solicitó anulación de la compra",
        "credenciales": {
            "ruc": "10090153566",
            "usuario": "WEEDIOND",
            "password": "Cesar123"
        }
    }
    
    print("\nDatos de la nota de crédito:")
    print(f"   Fecha: {test_data['fecha_emision']}")
    print(f"   Boleta a anular: {test_data['numero_boleta']}")
    print(f"   Motivo: {test_data['tipo_nota']}")
    print(f"   Sustento: {test_data['sustento']}")
    
    print("\nADVERTENCIA: Esto emitirá una nota de crédito REAL en SUNAT")
    respuesta = input("¿Deseas continuar? (si/no): ").lower().strip()
    
    if respuesta not in ['si', 's', 'yes', 'y']:
        print("Test cancelado")
        exit(0)
    
    print("\nIniciando emisión...")
    print("-" * 70)
    
    try:
        resultado = send_nota_credito_sunat(test_data)
        
        print("-" * 70)
        print("\nRESULTADO:")
        print("=" * 70)
        
        if resultado.get("success"):
            print("ÉXITO - Nota de crédito emitida correctamente")
            print(f"   Boleta anulada: {resultado.get('numero_boleta')}")
            print(f"   Fecha: {resultado.get('fecha_emision')}")
            if resultado.get("pdf"):
                print(f"   PDF: {resultado['pdf']['filename']}")
        else:
            print("ERROR - No se pudo emitir la nota de crédito")
            print(f"   Error: {resultado.get('error')}")
        
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
        exit(1)
    except Exception as e:
        print(f"\nERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("\nTest completado")

