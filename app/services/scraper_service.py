"""Servicio de scraping para SUNAT - Incluye boletas, facturas y notas de crédito"""
import os
import time
import base64
import json
import asyncio
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.utils.selenium_utils import configurar_driver
from app.utils.logger import logger
from app.config import settings


def _interruptible_sleep(seconds: int) -> None:
    """Sleep que puede ser interrumpido - versión thread-safe"""
    try:
        # Sleep en chunks pequeños para ser más responsivo
        chunk_size = 5  # 5 segundos por chunk
        chunks = seconds // chunk_size
        remainder = seconds % chunk_size
        
        for i in range(chunks):
            time.sleep(chunk_size)
            logger.debug(f"Sleep progreso: {(i+1)*chunk_size}/{seconds}s")
        
        if remainder > 0:
            time.sleep(remainder)
            
    except Exception as e:
        logger.info(f"Sleep interrumpido: {e}")
        raise


class SunatScraperError(Exception):
    """Error base para el scraper de SUNAT"""
    pass


class LoginError(SunatScraperError):
    """Error al iniciar sesión en SUNAT"""
    pass


class ProductAdditionError(SunatScraperError):
    """Error al agregar producto"""
    pass


class EmissionError(SunatScraperError):
    """Error al completar emisión"""
    pass


class PDFDownloadError(SunatScraperError):
    """Error al descargar PDF"""
    pass


class NotaCreditoError(SunatScraperError):
    """Error en nota de crédito"""
    pass


# Constantes para notas de crédito
MOTIVOS_NOTA_CREDITO = {
    "01": "Anulacion de la Operacion",
    "02": "Anulacion por Error en el RUC",
    "03": "Devolucion Total",
    "04": "Correccion por error en la descripcion",
    "05": "Devolucion por item"
}


def iniciar_sesion(driver, credenciales: dict, max_reintentos: int = 3) -> None:
    """Iniciar sesión en SUNAT con reintentos"""
    for intento in range(max_reintentos):
        try:
            logger.info(f"Intento de login {intento + 1}/{max_reintentos}")
            
            # Navegar a SUNAT con timeout más largo
            driver.set_page_load_timeout(60)
            driver.get(settings.sunat_url)
            
            # Esperar más tiempo para elementos críticos
            ruc_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "txtRuc"))
            )
            usuario_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "txtUsuario"))
            )
            password_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "txtContrasena"))
            )
            
            # Limpiar campos antes de escribir
            ruc_input.clear()
            ruc_input.send_keys(credenciales["ruc"])
            
            usuario_input.clear()
            usuario_input.send_keys(credenciales["usuario"])
            
            password_input.clear()
            password_input.send_keys(credenciales["password"])
            
            login_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.ID, "btnAceptar"))
            )
            login_button.click()
            
            # Verificar que el login fue exitoso esperando un elemento de la página principal
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "txtBusca"))
            )
            
            logger.info("Sesión iniciada correctamente")
            return
            
        except Exception as e:
            logger.warning(f"Error en intento {intento + 1}: {e}")
            if intento < max_reintentos - 1:
                logger.info(f"Reintentando en 5 segundos...")
                time.sleep(5)
            else:
                logger.error(f"Falló después de {max_reintentos} intentos")
                raise LoginError(f"No se pudo iniciar sesión después de {max_reintentos} intentos: {e}")


def agregar_producto(driver, producto: dict, tipo_documento: str) -> None:
    """Agregar producto al formulario"""
    try:
        logger.info(f"Agregando producto: {producto['descripcion']}")
        
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.ID, "waitMessage_underlay"))
        )
        
        button_id = "boleta.addItemButton" if tipo_documento == "BOLETA" else "factura.addItemButton_label"
        logger.info(f"Buscando botón adicionar: {button_id}")
        boton_adicionar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
        boton_adicionar.click()
        logger.info("Botón adicionar clickeado")
        
        logger.info("Seleccionando tipo de ítem...")
        radio_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='item.subTipoTI01']"))
        )
        radio_button.click()
        
        logger.info("Configurando cantidad...")
        campo_cantidad = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@name='cantidad']"))
        )
        campo_cantidad.clear()
        campo_cantidad.send_keys(str(producto["cantidad"]))
        
        logger.info("Configurando unidad de medida...")
        unidad_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "item.unidadMedida"))
        )
        unidad_input.clear()
        unidad_input.send_keys(producto["unidad_medida"])
        
        logger.info("Configurando descripción...")
        descripcion_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "item.descripcion"))
        )
        descripcion_input.clear()
        descripcion_input.send_keys(producto["descripcion"])
        
        logger.info("Configurando precio...")
        precio_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "item.precioUnitario"))
        )
        precio_input.clear()
        precio_formateado = "{:.4f}".format(float(producto["precio_base"]))
        precio_input.send_keys(precio_formateado)
        
        if producto["igv"] == 0:
            logger.info("Configurando producto sin IGV...")
            igv_checkbox = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "item.subTipoTB01"))
            )
            igv_checkbox.click()
        
        logger.info("Guardando producto...")
        boton_aceptar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "item.botonAceptar_label"))
        )
        boton_aceptar.click()
        
        logger.info(f"Producto '{producto['descripcion']}' agregado correctamente")
    except Exception as e:
        error_msg = f"No se pudo agregar producto '{producto.get('descripcion', 'UNKNOWN')}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ProductAdditionError(error_msg) from e


def completar_emision(driver, tipo_documento: str = "BOLETA") -> bool:
    """Completa el proceso de emisión del comprobante en SUNAT"""
    try:
        logger.info("Iniciando proceso de emisión")
        
        button_id = "boleta.botonGrabarDocumento_label" if tipo_documento == "BOLETA" else "factura.botonGrabarDocumento_label"
        grabar_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
        grabar_button.click()
        logger.info("Documento grabado")
        
        try:
            aceptar_docsrel = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@id='docsrel.botonGrabarDocumento']/span[1]"))
            )
            aceptar_docsrel.click()
            logger.info("Documentos relacionados aceptados")
        except:
            logger.info("No se encontraron documentos relacionados")
        
        preliminar_id = "boleta-preliminar.botonGrabarDocumento_label" if tipo_documento == "BOLETA" else "factura-preliminar.botonGrabarDocumento_label"
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, preliminar_id))
        )
        emitir_button.click()
        logger.info("Emisión preliminar confirmada")
        
        confirmar_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "dlgBtnAceptarConfirm_label"))
        )
        confirmar_button.click()
        logger.info("Emisión definitiva confirmada")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al completar emisión: {e}")
        raise EmissionError(f"No se pudo completar la emisión: {e}")


def obtener_numero_comprobante(driver) -> str:
    """Obtiene el número de comprobante generado por SUNAT"""
    try:
        numero_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "numeroComprobante"))
        )
        numero_completo = numero_element.text.strip()
        logger.info(f"Número de comprobante obtenido: {numero_completo}")
        return numero_completo
    except Exception as e:
        logger.error(f"Error al obtener número de comprobante: {e}")
        raise


def construir_nombre_pdf(tipo_documento: str, numero_comprobante: str, ruc: str) -> str:
    """Construye el nombre del archivo PDF según el tipo de documento"""
    prefijos = {
        "BOLETA": "PDF-BOLETA",
        "FACTURA": "PDF-FACTURA",
        "NOTA_CREDITO": "PDF-NOTA_CREDITO"
    }
    
    prefijo = prefijos.get(tipo_documento, None)
    return f"{prefijo}{numero_comprobante}{ruc}.pdf"


def descargar_pdf(driver, tipo_documento: str, ruc: str, download_dir: str = None) -> dict:
    """Descarga el PDF del comprobante emitido y retorna su información en Base64"""
    try:
        logger.info("Iniciando descarga de PDF")
        
        if not download_dir:
            download_dir = os.path.join(os.getcwd(), "downloads")
        
        os.makedirs(download_dir, exist_ok=True)
        
        numero_comprobante = obtener_numero_comprobante(driver)
        
        button_id = "dijit_form_Button_3_label" if tipo_documento == "NOTA_CREDITO" else "dijit_form_Button_2_label"
        descargar_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
        descargar_button.click()
        logger.info("Botón de descarga presionado")
        
        time.sleep(5)
        
        pdf_filename = construir_nombre_pdf(tipo_documento, numero_comprobante, ruc)
        pdf_file = os.path.join(download_dir, pdf_filename)
        
        if not os.path.exists(pdf_file):
            logger.error(f"PDF no encontrado: {pdf_filename}")
            raise PDFDownloadError(f"No se encontró el archivo PDF: {pdf_filename}")
        
        logger.info(f"PDF encontrado: {pdf_filename}")
        
        with open(pdf_file, 'rb') as f:
            pdf_content = f.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        file_size = len(pdf_content)
        file_name = os.path.basename(pdf_file)
        
        logger.info(f"PDF procesado correctamente: {file_name} ({file_size} bytes)")
        
        return {
            "filename": file_name,
            "content": pdf_base64,
            "size": file_size,
            "mime_type": "application/pdf",
            "numero_comprobante": numero_comprobante  #EB01-448   # codigo + numero de boleta
        }
        
    except Exception as e:
        logger.error(f"Error al descargar PDF: {e}")
        raise PDFDownloadError(f"No se pudo descargar el PDF: {e}")


def configurar_cliente_boleta(driver, cliente: dict) -> None:
    """Configura los datos del cliente para una boleta"""
    input_tipo = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "inicio.tipoDocumento"))
    )
    input_tipo.clear()
    
    if cliente.get("dni"):
        input_tipo.send_keys("DOC. NACIONAL DE IDENTIDAD")
        input_tipo.send_keys(Keys.RETURN)
        
        input_dni = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "inicio.numeroDocumento"))
        )
        input_dni.send_keys(cliente["dni"])
        input_dni.send_keys(Keys.TAB)
        
        WebDriverWait(driver, 20).until(
            lambda d: d.find_element(By.ID, "inicio.razonSocial").get_attribute("value").strip() != ""
        )
        logger.info("Cliente con DNI configurado")
    else:
        input_tipo.send_keys("SIN DOCUMENTO")
        input_tipo.send_keys(Keys.RETURN)
        
        input_razon = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "inicio.razonSocial"))
        )
        input_razon.send_keys(cliente["nombre"])
        logger.info("Cliente sin documento configurado")


def configurar_cliente_factura(driver, cliente: dict) -> None:
    """Configura los datos del cliente para una factura"""
    input_ruc = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "inicio.numeroDocumento"))
    )
    input_ruc.send_keys(cliente["ruc"])
    input_ruc.send_keys(Keys.TAB)
    
    WebDriverWait(driver, 20).until(
        lambda d: d.find_element(By.ID, "inicio.razonSocial").get_attribute("value").strip() != ""
    )
    logger.info("Cliente con RUC configurado")


def validar_total(driver, total_esperado: float, tipo_documento: str) -> None:
    """Valida que el total calculado coincida con el esperado"""
    field_id = f"{tipo_documento.lower()}.totalGeneral"
    input_total = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, field_id))
    )
    actual_value = float(input_total.get_attribute("value").replace("S/ ", ""))
    
    if abs(actual_value - total_esperado) > 0.01:
        error_msg = f"Total no coincide: {actual_value} vs {total_esperado}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Total validado correctamente: S/ {actual_value}")


def emitir_boleta(driver, data: dict) -> None:
    """Emitir boleta en SUNAT"""
    try:
        logger.info("Iniciando emisión de boleta")
        cliente = data["cliente"]
        
        logger.info("Buscando campo de búsqueda...")
        campo_busqueda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtBusca"))
        )
        campo_busqueda.clear()
        campo_busqueda.send_keys("BOLETA")
        logger.info("Campo de búsqueda completado")
        
        logger.info("Buscando botón 'Emitir Boleta de Venta'...")
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Emitir Boleta de Venta')]"))
        )
        emitir_button.click()
        logger.info("Botón 'Emitir Boleta de Venta' clickeado")
        
        logger.info("Esperando iframe de aplicación...")
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeApplication"))
        )
        logger.info("Cambio a iframe completado")
        
        logger.info("Configurando cliente...")
        configurar_cliente_boleta(driver, cliente)
        
        logger.info("Buscando botón continuar...")
        boton_continuar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "inicio.botonGrabarDocumento_label"))
        )
        boton_continuar.click()
        logger.info("Botón continuar clickeado")
        
        logger.info("Configurando fecha de emisión...")
        input_fecha = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "boleta.fechaEmision"))
        )
        input_fecha.clear()
        input_fecha.send_keys(data["fecha"])
        logger.info(f"Fecha configurada: {data['fecha']}")
        
        logger.info(f"Agregando {len(data['productos'])} productos...")
        for i, producto in enumerate(data["productos"]):
            logger.info(f"Agregando producto {i+1}: {producto['descripcion']}")
            agregar_producto(driver, producto, "BOLETA")
        
        logger.info("Validando total...")
        time.sleep(1)
        validar_total(driver, float(data["resumen"]["total"]), "boleta")
        
        logger.info("Boleta cargada correctamente")
    except Exception as e:
        error_msg = f"Error al emitir boleta: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e


def emitir_factura(driver, data: dict) -> None:
    """Emitir factura en SUNAT"""
    try:
        cliente = data["cliente"]
        
        campo_busqueda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtBusca"))
        )
        campo_busqueda.send_keys("FACTURA")
        
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Emitir Factura')]"))
        )
        emitir_button.click()
        
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeApplication"))
        )
        
        # Esperar a que el iframe esté completamente cargado
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "inicio.numeroDocumento"))
        )
        
        configurar_cliente_factura(driver, cliente)
        
        boton_continuar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "inicio.botonGrabarDocumento_label"))
        )
        boton_continuar.click()
        
        input_fecha = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "factura.fechaEmision"))
        )
        input_fecha.clear()
        input_fecha.send_keys(data["fecha"])
        
        for producto in data["productos"]:
            agregar_producto(driver, producto, "FACTURA")
        
        time.sleep(1)
        validar_total(driver, float(data["resumen"]["total"]), "factura")
        
        logger.info("Factura cargada correctamente")
    except Exception as e:
        error_msg = f"Error al emitir factura: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e


async def send_billing_sunat_async(data: dict) -> dict:
    """Función async SIMPLE - crear driver, usar, cerrar"""
    from app.services.driver_semaphore import driver_semaphore
    
    # Verificar si podemos crear driver
    if not await driver_semaphore.acquire():
        return {
            "success": False,
            "error": "Sistema ocupado - máximo de drivers alcanzado",
            "message": f"Máximo {driver_semaphore.max_drivers} drivers concurrentes. Intente más tarde."
        }
    
    driver = None
    try:
        tipo_documento = data["tipo_documento"]
        logger.info(f"Iniciando proceso de emisión de {tipo_documento}")
        
        # CREAR driver nuevo para esta tarea
        download_dir = os.path.join(os.getcwd(), "downloads")
        driver = configurar_driver(headless=settings.chrome_headless, download_dir=download_dir)
        logger.info(f"Driver creado para {tipo_documento}")
        
        # Ejecutar el procesamiento en thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            None, _process_with_driver, driver, data
        )
        
        logger.info(f"Proceso de {tipo_documento} completado exitosamente")
        return result
        
    except Exception as e:
        logger.error(f"Error en emisión: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Error procesando {data.get('tipo_documento', 'documento')}"
        }
    finally:
        # SIEMPRE cerrar driver y liberar semáforo
        if driver:
            try:
                driver.quit()
                logger.info("Driver cerrado correctamente")
            except Exception as e:
                logger.debug(f"Error cerrando driver: {e}")
        
        await driver_semaphore.release()


def _process_with_driver(driver: webdriver.Chrome, data: dict) -> dict:
    """Función sincrónica que procesa con un driver específico"""
    try:
        tipo_documento = data["tipo_documento"]
        
        # Iniciar sesión con reintentos
        iniciar_sesion(driver, data["credenciales"], max_reintentos=3)
        
        # Procesar según tipo
        if tipo_documento == "BOLETA":
            emitir_boleta(driver, data)
            completar_emision(driver, "BOLETA")  # COMENTADO para no emitir
        elif tipo_documento == "FACTURA":
            emitir_factura(driver, data)
            completar_emision(driver, "FACTURA")  # COMENTADO para no emitir
        else:
            raise ValueError(f"Tipo de documento no soportado: {tipo_documento}")
        
        try:
            download_dir = os.path.join(os.getcwd(), "downloads")
            pdf_data = descargar_pdf(driver, tipo_documento, data["credenciales"]["ruc"], download_dir)
        except Exception as e:
            logger.warning(f"No se pudo descargar PDF: {e}")
            pdf_data = None
        
        logger.info("Proceso completado exitosamente")
        
        result = {
            "success": True,
            "message": f"{tipo_documento} procesada correctamente (SIN EMITIR)",
            "serie": data["resumen"]["serie"],
            "numero": data["resumen"]["numero"],
            "total": data["resumen"]["total"]
        }
        
        if pdf_data:
            result["pdf"] = pdf_data
            logger.info(f"PDF incluido en respuesta: {pdf_data['filename']}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error procesando con driver: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e


def send_billing_sunat(data: dict) -> dict:
    """Función principal para enviar comprobante a SUNAT"""
    driver = None
    try:
        tipo_documento = data["tipo_documento"]
        logger.info(f"Iniciando proceso de emisión de {tipo_documento}")
        
        download_dir = os.path.join(os.getcwd(), "downloads")
        driver = configurar_driver(headless=settings.chrome_headless, download_dir=download_dir)
        
        iniciar_sesion(driver, data["credenciales"], max_reintentos=3)
        
        # Usar la función común _process_with_driver
        return _process_with_driver(driver, data)
        
    except Exception as e:
        logger.error(f"Error en emisión: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if driver:
            driver.quit()
            logger.info("Driver cerrado")


if __name__ == "__main__":

    with open("./test_boleta.json", "r") as f:
        test_data = json.load(f)

        result = send_billing_sunat(test_data)
        logger.info(f"Resultado: {result}")

        if result.get("success") and result.get("pdf"):
            pdf_bytes = base64.b64decode(result["pdf"]["content"])
            with open("./comprobante.pdf", "wb") as f:
                f.write(pdf_bytes)
                logger.info("PDF guardado en ./comprobante.pdf")

# ============================================================================
# FUNCIONES PARA NOTAS DE CRÉDITO
# ============================================================================

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


def ingresar_fecha_emision_nc(driver, fecha: str) -> None:
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


def ingresar_numero_boleta_nc(driver, numero_boleta: str) -> None:
    """Ingresa el número de la boleta a anular"""
    input_numero_boleta = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "pantallaInicial.numeroBVE"))
    )
    
    numero_solo = extraer_numero_boleta(numero_boleta)
    input_numero_boleta.send_keys(numero_solo)
    input_numero_boleta.send_keys(Keys.TAB)
    
    logger.info(f"Número de boleta ingresado: {numero_solo}")


def ingresar_sustento_nc(driver, sustento: str) -> None:
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
        ingresar_fecha_emision_nc(driver, data["fecha_emision"])
        seleccionar_motivo_nota_credito(driver, data.get("tipo_nota", "01"))
        ingresar_numero_boleta_nc(driver, data["numero_boleta"])
        ingresar_sustento_nc(driver, data["sustento"])
        
        continuar_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "pantallaInicial.btnContinuar_label"))
        )
        continuar_button.click()
        
        logger.info("Nota de crédito cargada correctamente")
        
    except Exception as e:
        logger.error(f"Error al emitir nota de crédito: {e}")
        raise NotaCreditoError(f"No se pudo emitir nota de crédito: {e}")


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
        raise NotaCreditoError(f"No se pudo completar la emisión: {e}")


def send_nota_credito_sunat(data: dict) -> dict:
    """Función principal para enviar nota de crédito a SUNAT"""
    driver = None
    try:
        logger.info("Iniciando proceso de emisión de nota de crédito")
        
        download_dir = os.path.join(os.getcwd(), "downloads")
        driver = configurar_driver(headless=settings.chrome_headless, download_dir=download_dir)
        
        iniciar_sesion(driver, data["credenciales"], max_reintentos=3)
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