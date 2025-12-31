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

class Credenciales(BaseModel):
    ruc: str
    usuario: str
    password: str

class EmisionRequest(BaseModel):
    tipo_documento: str = Field(pattern="^(BOLETA|FACTURA)$")
    cliente: Cliente
    productos: List[Producto]
    resumen: Resumen
    fecha: str
    id_remitente: str
    credenciales: Credenciales

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
