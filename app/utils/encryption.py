"""
Módulo de encriptación/desencriptación de credenciales.

Proporciona funciones para desencriptar credenciales SUNAT que vienen
encriptadas desde el frontend usando AES-256-GCM.
"""
import base64
from typing import Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings
from app.utils.logger import logger


# Constantes
SALT = b'factumovil-salt-v1'
IV_LENGTH = 12  # Bytes para IV en AES-GCM
KEY_LENGTH = 32  # 256 bits para AES-256
PBKDF2_ITERATIONS = 100000


class EncryptionError(Exception):
    """Error en operaciones de encriptación/desencriptación"""
    pass


def _derive_key(password: str) -> bytes:
    """
    Deriva una clave AES-256 desde el password usando PBKDF2.
    
    Args:
        password: Contraseña o clave maestra
        
    Returns:
        Clave derivada de 256 bits
        
    Raises:
        EncryptionError: Si hay error en la derivación
    """
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=SALT,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode())
    except Exception as e:
        raise EncryptionError(f"Error derivando clave: {e}")


def decrypt_credential(encrypted_base64: str) -> str:
    """
    Desencripta una credencial individual encriptada por el frontend.
    
    Formato esperado: IV (12 bytes) + datos encriptados (AES-GCM)
    
    Args:
        encrypted_base64: Credencial encriptada en Base64
        
    Returns:
        Credencial desencriptada en texto plano
        
    Raises:
        EncryptionError: Si hay error en la desencriptación
    """
    if not encrypted_base64:
        return ''
    
    try:
        # Decodificar Base64
        combined = base64.b64decode(encrypted_base64)
        
        # Validar longitud mínima (IV + al menos 1 byte de datos)
        if len(combined) < IV_LENGTH + 1:
            raise EncryptionError("Datos encriptados inválidos: longitud insuficiente")
        
        # Extraer IV (primeros 12 bytes) y datos encriptados
        iv = combined[:IV_LENGTH]
        ciphertext = combined[IV_LENGTH:]
        
        # Derivar clave desde variable de entorno
        key = _derive_key(settings.encryption_key)
        
        # Desencriptar con AES-GCM
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        
        return plaintext.decode('utf-8')
    
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Error desencriptando credencial: {e}")


def decrypt_credentials(encrypted_data: Dict[str, str]) -> Dict[str, str]:
    """
    Desencripta un objeto de credenciales completo.
    
    Args:
        encrypted_data: Diccionario con:
            - ruc_encrypted: RUC encriptado
            - usuario_encrypted: Usuario encriptado
            - password_encrypted: Contraseña encriptada
    
    Returns:
        Diccionario con credenciales desencriptadas:
            - ruc: RUC en texto plano
            - usuario: Usuario en texto plano
            - password: Contraseña en texto plano
    
    Raises:
        EncryptionError: Si hay error desencriptando cualquier campo
    """
    try:
        decrypted = {
            "ruc": decrypt_credential(encrypted_data.get("ruc_encrypted", "")),
            "usuario": decrypt_credential(encrypted_data.get("usuario_encrypted", "")),
            "password": decrypt_credential(encrypted_data.get("password_encrypted", ""))
        }
        
        # Validar que todos los campos fueron desencriptados
        if not all(decrypted.values()):
            raise EncryptionError("Uno o más campos de credenciales están vacíos")
        
        return decrypted
    
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Error desencriptando credenciales: {e}")


def validate_encryption_key() -> bool:
    """
    Valida que la clave de encriptación sea segura.
    
    Returns:
        True si la clave es válida
        
    Raises:
        EncryptionError: Si la clave no es segura
    """
    if settings.encryption_key == "CAMBIAR_EN_PRODUCCION":
        logger.warning(
            "⚠️ Usando clave de encriptación por defecto. "
            "Configura ENCRYPTION_KEY en producción."
        )
        return False
    
    if len(settings.encryption_key) < 16:
        raise EncryptionError(
            "Clave de encriptación muy corta. Debe tener al menos 16 caracteres."
        )
    
    return True
