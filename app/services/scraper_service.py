"""Servicio de scraping para SUNAT"""
import time
import os
import base64
import glob
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from app.utils.selenium_utils import configurar_driver
from app.utils.logger import logger
from app.config import settings

def iniciar_sesion(driver, credenciales: dict):
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
        
        logger.info("✓ Sesión iniciada correctamente")
    except Exception as e:
        logger.error(f"✗ Error al iniciar sesión: {e}")
        raise

def agregar_producto(driver, producto: dict, tipo_documento: str):
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
        
        # Seleccionar tipo de ítem
        radio_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='item.subTipoTI01']"))
        )
        radio_button.click()
        
        # Cantidad
        campo_cantidad = driver.find_element(By.XPATH, "//input[@name='cantidad']")
        campo_cantidad.clear()
        campo_cantidad.send_keys(str(producto["cantidad"]))
        
        # Unidad de medida
        unidad_input = driver.find_element(By.ID, "item.unidadMedida")
        unidad_input.clear()
        unidad_input.send_keys(producto["unidad_medida"])
        
        # Descripción
        descripcion_input = driver.find_element(By.ID, "item.descripcion")
        descripcion_input.clear()
        descripcion_input.send_keys(producto["descripcion"])
        
        # Precio
        precio_input = driver.find_element(By.ID, "item.precioUnitario")
        precio_input.clear()
        precio_formateado = "{:.4f}".format(float(producto["precio_base"]))
        precio_input.send_keys(precio_formateado)
        
        # IGV
        if producto["igv"] == 0:
            igv_checkbox = driver.find_element(By.ID, "item.subTipoTB01")
            igv_checkbox.click()
        
        # Aceptar
        boton_aceptar = driver.find_element(By.ID, "item.botonAceptar_label")
        boton_aceptar.click()
        
        logger.info(f"✓ Producto '{producto['descripcion']}' agregado")
    except Exception as e:
        logger.error(f"✗ Error al agregar producto: {e}")
        raise

def completar_emision(driver, tipo_documento: str = "BOLETA"):
    """Completa el proceso de emisión del comprobante en SUNAT"""
    try:
        # Paso 1: Grabar documento (botón principal)
        logger.info("Paso 1: Grabando documento...")
        
        button_id = "boleta.botonGrabarDocumento_label" if tipo_documento == "BOLETA" else "factura.botonGrabarDocumento_label"
        
        grabar_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
        grabar_button.click()
        
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.ID, "waitMessage_underlay"))
        )
        logger.info("✓ Documento grabado")
        
        # Paso 2: Aceptar documentos relacionados (si aparece)
        logger.info("Paso 2: Verificando documentos relacionados...")
        try:
            aceptar_docsrel = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@id='docsrel.botonGrabarDocumento']/span[1]"))
            )
            aceptar_docsrel.click()
            logger.info("✓ Documentos relacionados aceptados")
            
            WebDriverWait(driver, 20).until(
                EC.invisibility_of_element_located((By.ID, "waitMessage_underlay"))
            )
        except:
            logger.info("No hay documentos relacionados, continuando...")
        
        # Paso 3: Confirmar emisión preliminar
        logger.info("Paso 3: Confirmando emisión preliminar...")
        
        preliminar_id = "boleta-preliminar.botonGrabarDocumento_label" if tipo_documento == "BOLETA" else "factura-preliminar.botonGrabarDocumento_label"
        
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, preliminar_id))
        )
        emitir_button.click()
        
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.ID, "waitMessage_underlay"))
        )
        logger.info("✓ Emisión confirmada")
        
        # Verificar mensaje de éxito
        time.sleep(2)
        try:
            mensaje_exito = driver.find_element(
                By.XPATH, 
                "//div[contains(@class, 'success') or contains(text(), 'exitosamente') or contains(text(), 'correctamente')]"
            )
            logger.info(f"✓ Mensaje de confirmación: {mensaje_exito.text}")
        except:
            logger.info("✓ Emisión completada (sin mensaje visible)")
        
        logger.info("✓✓✓ Emisión completada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error al completar emisión: {e}")
        raise

def obtener_numero_comprobante(driver):
    """Obtiene el número de comprobante generado por SUNAT"""
    try:
        # XPath: //*[@id="numeroComprobante"]
        numero_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "numeroComprobante"))
        )
        numero_completo = numero_element.text.strip()
        logger.info(f"✓ Número de comprobante: {numero_completo}")
        return numero_completo
    except Exception as e:
        logger.warning(f"No se pudo obtener número de comprobante: {e}")
        return None

def descargar_pdf(driver, tipo_documento: str = "BOLETA", download_dir: str = None):
    """Descarga el PDF del comprobante emitido y retorna su contenido en base64"""
    try:
        logger.info("Descargando PDF del comprobante...")
        
        # Configurar directorio de descarga
        if not download_dir:
            download_dir = os.path.join(os.getcwd(), "downloads")
        
        os.makedirs(download_dir, exist_ok=True)
        
        # Limpiar descargas anteriores
        for old_file in glob.glob(os.path.join(download_dir, "*.pdf")):
            try:
                os.remove(old_file)
                logger.info(f"Archivo anterior eliminado: {old_file}")
            except:
                pass
        
        # Obtener número de comprobante antes de descargar
        numero_comprobante = obtener_numero_comprobante(driver)
        
        # Buscar botón de descarga
        # XPath: //*[@id="dijit_form_Button_2_label"] - DESCARGAR PDF
        # XPath: //*[@id="dijit_form_Button_4_label"] - IMPRIMIR
        
        posibles_selectores = [
            (By.XPATH, "//*[@id='dijit_form_Button_2_label']"),  # Descargar PDF
            (By.XPATH, "//span[contains(text(), 'Descargar PDF')]"),
            (By.ID, "btnDescargarPDF"),
            (By.ID, "boleta.botonDescargarPDF"),
            (By.ID, "factura.botonDescargarPDF"),
            (By.XPATH, "//button[contains(text(), 'PDF')]"),
        ]
        
        descargar_button = None
        for by_type, selector in posibles_selectores:
            try:
                descargar_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                logger.info(f"✓ Botón de descarga encontrado: {selector}")
                break
            except:
                continue
        
        if not descargar_button:
            logger.warning("No se encontró botón de descarga de PDF")
            return None
        
        # Hacer clic en descargar
        descargar_button.click()
        logger.info("✓ Clic en descargar PDF")
        
        # Esperar a que se descargue el archivo (máximo 30 segundos)
        pdf_file = None
        for i in range(30):
            time.sleep(1)
            pdf_files = glob.glob(os.path.join(download_dir, "*.pdf"))
            if pdf_files:
                pdf_file = pdf_files[0]
                logger.info(f"✓ PDF descargado: {os.path.basename(pdf_file)}")
                break
        
        if not pdf_file:
            logger.warning("Timeout esperando descarga del PDF")
            return None
        
        # Leer el PDF y convertirlo a base64
        with open(pdf_file, 'rb') as f:
            pdf_content = f.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Obtener información del archivo
        file_size = len(pdf_content)
        file_name = os.path.basename(pdf_file)
        
        logger.info(f"✓ PDF procesado: {file_name} ({file_size} bytes)")
        
        return {
            "filename": file_name,
            "content": pdf_base64,
            "size": file_size,
            "mime_type": "application/pdf",
            "numero_comprobante": numero_comprobante
        }
            
    except Exception as e:
        logger.error(f"Error al descargar PDF: {e}")
        return None

def emitir_boleta(driver, data: dict):
    """Emitir boleta en SUNAT"""
    try:
        cliente = data["cliente"]
        
        # Buscar "BOLETA"
        campo_busqueda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtBusca"))
        )
        campo_busqueda.send_keys("BOLETA")
        
        # Clic en "Emitir Boleta"
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Emitir Boleta de Venta')]"))
        )
        emitir_button.click()
        
        # Cambiar a iframe
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeApplication"))
        )
        
        # Tipo de documento
        input_tipo = driver.find_element(By.ID, "inicio.tipoDocumento")
        input_tipo.clear()
        
        if cliente.get("dni"):
            input_tipo.send_keys("DOC. NACIONAL DE IDENTIDAD")
            input_tipo.send_keys(Keys.RETURN)
            
            input_dni = driver.find_element(By.ID, "inicio.numeroDocumento")
            input_dni.send_keys(cliente["dni"])
            input_dni.send_keys(Keys.TAB)
            
            # Esperar razón social
            WebDriverWait(driver, 20).until(
                lambda d: d.find_element(By.ID, "inicio.razonSocial").get_attribute("value").strip() != ""
            )
        else:
            input_tipo.send_keys("SIN DOCUMENTO")
            input_tipo.send_keys(Keys.RETURN)
            
            input_razon = driver.find_element(By.ID, "inicio.razonSocial")
            input_razon.send_keys(cliente["nombre"])
        
        # Continuar
        boton_continuar = driver.find_element(By.ID, "inicio.botonGrabarDocumento_label")
        boton_continuar.click()
        
        # Fecha
        input_fecha = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "boleta.fechaEmision"))
        )
        input_fecha.clear()
        input_fecha.send_keys(data["fecha"])
        
        # Agregar productos
        for producto in data["productos"]:
            agregar_producto(driver, producto, "BOLETA")
        
        # Validar total
        time.sleep(1)
        input_total = driver.find_element(By.ID, "boleta.totalGeneral")
        actual_value = float(input_total.get_attribute("value").replace("S/ ", ""))
        expected_total = float(data["resumen"]["total"])
        
        if abs(actual_value - expected_total) > 0.01:
            raise ValueError(f"Total no coincide: {actual_value} vs {expected_total}")

        logger.info("✓ Boleta cargada correctamente")
    except Exception as e:
        logger.error(f"✗ Error al emitir boleta: {e}")
        raise

def emitir_factura(driver, data: dict):
    """Emitir factura en SUNAT"""
    try:
        cliente = data["cliente"]
        
        # Buscar "FACTURA"
        campo_busqueda = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtBusca"))
        )
        campo_busqueda.send_keys("FACTURA")
        
        # Clic en "Emitir Factura"
        emitir_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Emitir Factura')]"))
        )
        emitir_button.click()
        
        # Cambiar a iframe
        WebDriverWait(driver, 20).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframeApplication"))
        )
        
        # RUC del cliente
        input_ruc = driver.find_element(By.ID, "inicio.numeroDocumento")
        input_ruc.send_keys(cliente["ruc"])
        input_ruc.send_keys(Keys.TAB)
        
        # Esperar razón social
        WebDriverWait(driver, 20).until(
            lambda d: d.find_element(By.ID, "inicio.razonSocial").get_attribute("value").strip() != ""
        )
        
        # Continuar
        boton_continuar = driver.find_element(By.ID, "inicio.botonGrabarDocumento_label")
        boton_continuar.click()
        
        # Fecha
        input_fecha = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "factura.fechaEmision"))
        )
        input_fecha.clear()
        input_fecha.send_keys(data["fecha"])
        
        # Agregar productos
        for producto in data["productos"]:
            agregar_producto(driver, producto, "FACTURA")
        
        # Validar total
        time.sleep(1)
        input_total = driver.find_element(By.ID, "factura.totalGeneral")
        actual_value = float(input_total.get_attribute("value").replace("S/ ", ""))
        expected_total = float(data["resumen"]["total"])
        
        if abs(actual_value - expected_total) > 0.01:
            raise ValueError(f"Total no coincide: {actual_value} vs {expected_total}")
        
        logger.info("✓ Factura cargada correctamente")
    except Exception as e:
        logger.error(f"✗ Error al emitir factura: {e}")
        raise

def send_billing_sunat(data: dict) -> dict:
    """Función principal para enviar comprobante"""
    driver = None
    try:
        logger.info(f"Iniciando proceso de emisión de {data['tipo_documento']}")
        
        # Configurar directorio de descarga
        download_dir = os.path.join(os.getcwd(), "downloads")
        
        driver = configurar_driver(headless=settings.chrome_headless, download_dir=download_dir)
        iniciar_sesion(driver, data["credenciales"])
        
        if data["tipo_documento"] == "BOLETA":
            emitir_boleta(driver, data)
            completar_emision(driver, "BOLETA")
        elif data["tipo_documento"] == "FACTURA":
            emitir_factura(driver, data)
            completar_emision(driver, "FACTURA")
        else:
            raise ValueError(f"Tipo de documento no soportado: {data['tipo_documento']}")
        
        # Intentar descargar PDF
        pdf_data = descargar_pdf(driver, data["tipo_documento"], download_dir)
        
        logger.info("✓✓✓ Proceso completado exitosamente")
        
        result = {
            "success": True,
            "message": f"{data['tipo_documento']} emitida correctamente",
            "serie": data["resumen"]["serie"],
            "numero": data["resumen"]["numero"],
            "total": data["resumen"]["total"]
        }
        
        # Agregar PDF si se descargó correctamente
        if pdf_data:
            result["pdf"] = pdf_data
            logger.info(f"✓ PDF incluido en respuesta: {pdf_data['filename']}")
        else:
            logger.warning("PDF no disponible en la respuesta")
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Error en emisión: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if driver:
            driver.quit()

