"""
Servicio para gestionar credenciales SUNAT.

Responsable de:
- Desencriptar credenciales encriptadas (ÚNICO formato aceptado)
- Validar credenciales
- Sanitizar credenciales para logs
"""
from typing import Dict

from app.utils.encryption import decrypt_credentials, EncryptionError
from app.utils.logger import logger


class CredentialError(Exception):
    """Error en operaciones con credenciales"""
    pass


class CredentialService:
    """Servicio para gestionar credenciales de forma segura"""
    
    @staticmethod
    def decrypt_and_validate(encrypted_data: Dict[str, str]) -> Dict[str, str]:
        """
        Desencripta y valida credenciales encriptadas.
        
        NOTA: Solo acepta credenciales encriptadas por seguridad.
        
        Args:
            encrypted_data: Datos encriptados con:
                - ruc_encrypted: RUC encriptado
                - usuario_encrypted: Usuario encriptado
                - password_encrypted: Contraseña encriptada
            
        Returns:
            Diccionario con credenciales desencriptadas
            
        Raises:
            CredentialError: Si hay error desencriptando o validando
        """
        try:
            # Desencriptar
            decrypted = decrypt_credentials(encrypted_data)
            logger.info("Credenciales desencriptadas correctamente")
            
            # Validar
            CredentialService._validate_credentials(decrypted)
            
            return decrypted
        
        except EncryptionError as e:
            logger.error(f"Error desencriptando credenciales: {e}")
            raise CredentialError(f"Error al desencriptar credenciales: {e}")
    
    @staticmethod
    def _validate_credentials(credentials: Dict[str, str]) -> None:
        """
        Valida que las credenciales tengan los campos requeridos.
        
        Args:
            credentials: Credenciales a validar
            
        Raises:
            CredentialError: Si faltan campos o están vacíos
        """
        required_fields = ["ruc", "usuario", "password"]
        
        for field in required_fields:
            value = credentials.get(field, "").strip()
            if not value:
                raise CredentialError(f"Campo requerido vacío: {field}")
    
    @staticmethod
    def sanitize_for_log(credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitiza credenciales para que no aparezcan en logs.
        
        Args:
            credentials: Credenciales a sanitizar
            
        Returns:
            Credenciales con valores ocultos
        """
        return {
            "ruc": credentials.get("ruc", "")[:3] + "***" if credentials.get("ruc") else "***",
            "usuario": "***",
            "password": "***"
        }
