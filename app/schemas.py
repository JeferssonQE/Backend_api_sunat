"""Schemas de request/response"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Cliente(BaseModel):
    nombre: Optional[str] = None
    dni: Optional[str] = None
    ruc: Optional[str] = None
    telefono: Optional[str] = None

class Producto(BaseModel):
    cantidad: float = Field(gt=0)
    descripcion: str
    unidad_medida: str
    precio_base: float = Field(ge=0)
    igv: int = Field(ge=0, le=100)
    precio_total: float = Field(ge=0)

class Resumen(BaseModel):
    serie: str
    numero: str
    sub_total: float = Field(ge=0)
    igv_total: float = Field(ge=0)
    total: float = Field(ge=0)

class CredencialesEncriptadas(BaseModel):
    """Credenciales SUNAT encriptadas desde el frontend (REQUERIDO)"""
    ruc_encrypted: str
    usuario_encrypted: str
    password_encrypted: str

class EmisionRequest(BaseModel):
    """Request para emitir un comprobante"""
    tipo_documento: str = Field(pattern="^(BOLETA|FACTURA)$")
    cliente: Cliente
    productos: List[Producto]
    resumen: Resumen
    fecha: str
    id_remitente: str
    
    # SOLO credenciales encriptadas 
    credenciales_encrypted: CredencialesEncriptadas
    
    #validaremos la fecha en formato dd/mm/yyyy
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_fecha
        
    @classmethod
    def validate_fecha(cls, v):
        if not isinstance(v, str):
            raise ValueError("La fecha debe ser una cadena de texto")
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("La fecha debe estar en formato dd/mm/yyyy")
        return v
    
    @classmethod
    def model_validate(cls, obj):
        """Validación completa con reglas de negocio"""
        instance = super().model_validate(obj)
        
        # Validar totales
        total_calculado = sum(p.precio_total for p in instance.productos)
        if abs(total_calculado - instance.resumen.total) > 0.01:
            raise ValueError(
                f"Total no coincide: calculado {total_calculado} "
                f"vs declarado {instance.resumen.total}"
            )
        
        # Validar cliente según tipo de documento
        if instance.tipo_documento == "BOLETA":
            if not instance.cliente.dni and not instance.cliente.nombre:
                raise ValueError("Boleta requiere DNI o nombre del cliente")
        elif instance.tipo_documento == "FACTURA":
            if not instance.cliente.ruc:
                raise ValueError("Factura requiere RUC del cliente")
        
        return instance

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    created_at: str

class StatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    selenium_ready: bool
    active_tasks: int
    uptime_seconds: Optional[float] = None

class NotaCreditoRequest(BaseModel):
    """Request para emitir una nota de crédito"""
    fecha_emision: str
    tipo_nota: str = Field(default="01", pattern="^(01|02|03|04|05)$")
    numero_boleta: str
    sustento: str
    
    # SOLO credenciales encriptadas (más seguro)
    credenciales_encrypted: CredencialesEncriptadas
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_fecha
        
    @classmethod
    def validate_fecha(cls, v):
        if not isinstance(v, str):
            raise ValueError("La fecha debe ser una cadena de texto")
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("La fecha debe estar en formato dd/mm/yyyy")
        return v
