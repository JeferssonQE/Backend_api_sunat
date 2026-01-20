# 📋 Ejemplos de API - Backend SUNAT

## Estructura Actualizada (Sin id_remitente)

### 1. **Endpoint: `POST /emit/invoice`**

```json
{
  "invoice": {
    "tipo_documento": "BOLETA",
    "cliente": {
      "nombre": "JUAN PEREZ",
      "dni": null,
      "ruc": null,
      "telefono": "987654321"
    },
    "productos": [
      {
        "cantidad": 2.0,
        "descripcion": "FREGOL CAMANEJO",
        "unidad_medida": "KILOGRAMO",
        "precio_base": 3.5,
        "igv": 0,
        "precio_total": 7.0
      }
    ],
    "resumen": {
      "serie": "B001",
      "numero": "00123",
      "sub_total": 7.0,
      "igv_total": 0.0,
      "total": 7.0
    },
    "fecha": "17/01/2025"
  },
  "sender": {
    "ruc": "10432404272",
    "sunat_user": "ISELANDO",
    "sunat_pass": "ntrestald"
  }
}
```

### 2. **Endpoint: `POST /emit/test-invoice`** (Para Testing)

```json
{
  "invoice": {
    "tipo_documento": "BOLETA",
    "cliente": {
      "nombre": "CLIENTE TEST",
      "dni": "12345678",
      "telefono": "999888777"
    },
    "productos": [
      {
        "cantidad": 1.0,
        "descripcion": "PRODUCTO TEST",
        "unidad_medida": "UNIDAD",
        "precio_base": 10.0,
        "igv": 18,
        "precio_total": 11.8
      }
    ],
    "resumen": {
      "serie": "B001",
      "numero": "TEST001",
      "sub_total": 10.0,
      "igv_total": 1.8,
      "total": 11.8
    },
    "fecha": "16/01/2026"
  },
  "sender": {
    "ruc": "10432404272",
    "sunat_user": "TESTUSER",
    "sunat_pass": "testpass123"
  }
}
```

### 3. **Respuesta del Endpoint**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "ESPERANDO",
  "message": "Invoice emission queued",
  "invoice_id": null
}
```

### 4. **Consulta de Estado: `GET /emit/status/{task_id}`**

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "message": "BOLETA emitida correctamente",
  "pdf_base64": "JVBERi0xLjQKJcOkw7zDtsO...",
  "sunat_response": {
    "success": true,
    "message": "BOLETA emitida correctamente",
    "serie": "B001",
    "numero": "00123",
    "total": 7.0,
    "pdf": {
      "filename": "PDF-BOLETAEB01-B001-00123.pdf",
      "content": "JVBERi0xLjQKJcOkw7zDtsO...",
      "size": 2048,
      "mime_type": "application/pdf",
      "numero_comprobante": "B001-00123"
    }
  }
}
```

## 🔄 Cambios Principales

### ❌ **Eliminado:**
- `"id_remitente": "5"` - Ya no es necesario

### ✅ **Mantenido:**
- Estructura `invoice` con todos los datos del comprobante
- Estructura `sender` con credenciales separadas
- Todos los campos de productos, cliente y resumen

### 📝 **Notas:**
1. Las credenciales ahora vienen completamente separadas en `sender`
2. El `invoice` contiene solo los datos del comprobante
3. El campo `id_remitente` es opcional en el schema por compatibilidad
4. La API funciona con la nueva estructura sin `id_remitente`

## 🎯 Endpoints Disponibles

- `POST /emit/invoice` - Emisión de comprobantes
- `POST /emit/test-invoice` - Testing de emisión  
- `POST /emit/credit-note` - Emisión de notas de crédito
- `GET /emit/status/{task_id}` - Consultar estado
- `GET /health` - Health check del sistema