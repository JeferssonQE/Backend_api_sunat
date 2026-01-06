"""Servicio de scraping para SUNAT"""
import os
import time
import base64
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.utils.selenium_utils import configurar_driver
from app.utils.logger import logger
from app.config import settings


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


def iniciar_sesion(driver, credenciales: dict) -> None:
    """Iniciar sesión en SUNAT"""
    try:
        driver.get(settings.sunat_url)
        
        ruc_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtRuc"))
        )
        usuario_input = driver.find_element(By.ID, "txtUsuario")
        password_input = driver.find_element(By.ID, "txtContrasena")
        
        ruc_input.send_keys(credenciales["ruc"])
        usuario_input.send_keys(credenciales["usuario"])
        password_input.send_keys(credenciales["password"])
        
        login_button = driver.find_element(By.ID, "btnAceptar")
        login_button.click()
        
        logger.info("Sesión iniciada correctamente")
    except Exception as e:
        logger.error(f"Error al iniciar sesión: {e}")
        raise LoginError(f"No se pudo iniciar sesión: {e}")


def agregar_producto(driver, producto: dict, tipo_documento: str) -> None:
    """Agregar producto al formulario"""
    try:
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.ID, "waitMessage_underlay"))
        )
        
        button_id = "boleta.addItemButton" if tipo_documento == "BOLETA" else "factura.addItemButton_label"
        boton_adicionar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
        boton_adicionar.click()
        
        radio_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='item.subTipoTI01']"))
        )
        radio_button.click()
        
        campo_cantidad = driver.find_element(By.XPATH, "//input[@name='cantidad']")
        campo_cantidad.clear()
        campo_cantidad.send_keys(str(producto["cantidad"]))
        
        unidad_input = driver.find_element(By.ID, "item.unidadMedida")
        unidad_input.clear()
        unidad_input.send_keys(producto["unidad_medida"])
        
        descripcion_input = driver.find_element(By.ID, "item.descripcion")
        descripcion_input.clear()
        descripcion_input.send_keys(producto["descripcion"])
        
        precio_input = driver.find_element(By.ID, "item.precioUnitario")
        precio_input.clear()
        precio_formateado = "{:.4f}".format(float(producto["precio_base"]))
        precio_input.send_keys(precio_formateado)
        
        if producto["igv"] == 0:
            igv_checkbox = driver.find_element(By.ID, "item.subTipoTB01")
            igv_checkbox.click()
        
        boton_aceptar = driver.find_element(By.ID, "item.botonAceptar_label")
        boton_aceptar.click()
        
        logger.info(f"Producto '{producto['descripcion']}' agregado correctamente")
    except Exception as e:
        logger.error(f"Error al agregar producto: {e}")
        raise ProductAdditionError(f"No se pudo agregar producto: {e}")


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
        "BOLETA": "PDF-BOLETAEB01-",
        "FACTURA": "PDF-FACTURAEB01-",
        "NOTA_CREDITO": "PDF-NOTA_CREDITOEB01-"
    }
    
    prefijo = prefijos.get(tipo_documento, f"PDF-{tipo_documento}EB01-")
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
            "numero_comprobante": numero_comprobante
        }
        
    except Exception as e:
        logger.error(f"Error al descargar PDF: {e}")
        raise PDFDownloadError(f"No se pudo descargar el PDF: {e}")


def configurar_cliente_boleta(driver, cliente: dict) -> None:
    """Configura los datos del cliente para una boleta"""
    input_tipo = driver.find_element(By.ID, "inicio.tipoDocumento")
    input_tipo.clear()
    
    if cliente.get("dni"):
        input_tipo.send_keys("DOC. NACIONAL DE IDENTIDAD")
        input_tipo.send_keys(Keys.RETURN)
        
        input_dni = driver.find_element(By.ID, "inicio.numeroDocumento")
        input_dni.send_keys(cliente["dni"])
        input_dni.send_keys(Keys.TAB)
        
        WebDriverWait(driver, 20).until(
            lambda d: d.find_element(By.ID, "inicio.razonSocial").get_attribute("value").strip() != ""
        )
        logger.info("Cliente con DNI configurado")
    else:
        input_tipo.send_keys("SIN DOCUMENTO")
        input_tipo.send_keys(Keys.RETURN)
        
        input_razon = driver.find_element(By.ID, "inicio.razonSocial")
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
    input_total = driver.find_element(By.ID, field_id)
    actual_value = float(input_total.get_attribute("value").replace("S/ ", ""))
    
    if abs(actual_value - total_esperado) > 0.01:
        error_msg = f"Total no coincide: {actual_value} vs {total_esperado}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Total validado correctamente: S/ {actual_value}")


def emitir_boleta(driver, data: dict) -> None:
    """Emitir boleta en SUNAT"""
    try:
        cliente = data["cliente"]
        
        campo_busqueda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtBusca"))
        )
        campo_busqueda.send_keys("BOLETA")
        
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Emitir Boleta de Venta')]"))
        )
        emitir_button.click()
        
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeApplication"))
        )
        
        configurar_cliente_boleta(driver, cliente)
        
        boton_continuar = driver.find_element(By.ID, "inicio.botonGrabarDocumento_label")
        boton_continuar.click()
        
        input_fecha = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "boleta.fechaEmision"))
        )
        input_fecha.clear()
        input_fecha.send_keys(data["fecha"])
        
        for producto in data["productos"]:
            agregar_producto(driver, producto, "BOLETA")
        
        time.sleep(1)
        validar_total(driver, float(data["resumen"]["total"]), "boleta")
        
        logger.info("Boleta cargada correctamente")
    except Exception as e:
        logger.error(f"Error al emitir boleta: {e}")
        raise


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
        logger.error(f"Error al emitir factura: {e}")
        raise


def send_billing_sunat(data: dict) -> dict:
    """Función principal para enviar comprobante a SUNAT"""
    driver = None
    try:
        tipo_documento = data["tipo_documento"]
        logger.info(f"Iniciando proceso de emisión de {tipo_documento}")
        
        download_dir = os.path.join(os.getcwd(), "downloads")
        driver = configurar_driver(headless=settings.chrome_headless, download_dir=download_dir)
        
        iniciar_sesion(driver, data["credenciales"])
        
        if tipo_documento == "BOLETA":
            emitir_boleta(driver, data)
            completar_emision(driver, "BOLETA")
        elif tipo_documento == "FACTURA":
            emitir_factura(driver, data)
            completar_emision(driver, "FACTURA")
        else:
            raise ValueError(f"Tipo de documento no soportado: {tipo_documento}")
        
        pdf_data = descargar_pdf(driver, tipo_documento, data["credenciales"]["ruc"], download_dir)
        
        logger.info("Proceso completado exitosamente")
        
        result = {
            "success": True,
            "message": f"{tipo_documento} emitida correctamente",
            "serie": data["resumen"]["serie"],
            "numero": data["resumen"]["numero"],
            "total": data["resumen"]["total"]
        }
        
        if pdf_data:
            result["pdf"] = pdf_data
            logger.info(f"PDF incluido en respuesta: {pdf_data['filename']}")
        else:
            logger.warning("PDF no disponible en la respuesta")
        
        return result
        
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
    # ⚠️ NO INCLUIR CREDENCIALES REALES EN EL CÓDIGO
    # Usar variables de entorno o archivos de configuración externos
    test_data = {
        "tipo_documento": "BOLETA",
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "cliente": {
            "dni": "12345678",
            "nombre": "Cliente Test"
        },
        "productos": [
            {
                "cantidad": 2.0,
                "unidad_medida": "KILOGRAMO",
                "descripcion": "PRODUCTO TEST",
                "precio_base": 5.0,
                "igv": 0,
                "precio_total": 10.0
            }
        ],
        "resumen": {
            "serie": "B001",
            "numero": "00001",
            "sub_total": 10.0,
            "igv_total": 0.0,
            "total": 10.0
        },
        "credenciales": {
            "ruc": os.getenv("TEST_RUC", "10000000000"),
            "usuario": os.getenv("TEST_USUARIO", "TESTUSER"),
            "password": os.getenv("TEST_PASSWORD", "test123")
        }
    }

    result = send_billing_sunat(test_data)
    logger.info(f"Resultado: {result}")

    if result.get("success") and result.get("pdf"):
        pdf_bytes = base64.b64decode(result["pdf"]["content"])
        with open("./comprobante.pdf", "wb") as f:
            f.write(pdf_bytes)
            logger.info("PDF guardado en ./comprobante.pdf")
