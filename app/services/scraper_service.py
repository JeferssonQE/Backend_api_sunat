"""Servicio de scraping para SUNAT"""
import time
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
        
        logger.info("Sesión iniciada correctamente")
    except Exception as e:
        logger.error(f"Error al iniciar sesión: {e}")
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
        
        logger.info(f"Producto '{producto['descripcion']}' agregado")
    except Exception as e:
        logger.error(f"Error al agregar producto: {e}")
        raise

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
        
        logger.info("Boleta emitida correctamente")
    except Exception as e:
        logger.error(f"Error al emitir boleta: {e}")
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
        
        logger.info("Factura emitida correctamente")
    except Exception as e:
        logger.error(f"Error al emitir factura: {e}")
        raise

def send_billing_sunat(data: dict) -> dict:
    """Función principal para enviar comprobante"""
    driver = None
    try:
        logger.info(f"Iniciando proceso de emisión de {data['tipo_documento']}")
        
        driver = configurar_driver(headless=settings.chrome_headless)
        iniciar_sesion(driver, data["credenciales"])
        
        if data["tipo_documento"] == "BOLETA":
            emitir_boleta(driver, data)
        elif data["tipo_documento"] == "FACTURA":
            emitir_factura(driver, data)
        else:
            raise ValueError(f"Tipo de documento no soportado: {data['tipo_documento']}")
        
        logger.info("Proceso completado exitosamente")
        return {
            "success": True,
            "message": f"{data['tipo_documento']} emitida correctamente",
            "serie": data["resumen"]["serie"],
            "numero": data["resumen"]["numero"],
            "total": data["resumen"]["total"]
        }
    except Exception as e:
        logger.error(f"Error en emisión: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if driver:
            driver.quit()
