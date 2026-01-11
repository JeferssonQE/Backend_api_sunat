# 🔐 Integración de Encriptación en Frontend

## Resumen

El backend **SOLO acepta credenciales encriptadas**. Las credenciales se desencriptan de forma segura sin exponerlas en logs. No hay soporte para credenciales en texto plano.

---

## 📋 Cambios en el Backend

### 1. Nuevo Módulo: `app/utils/encryption.py`
- Desencripta credenciales usando AES-256-GCM
- Valida la clave de encriptación
- Maneja errores de forma segura

### 2. Nuevo Servicio: `app/services/credential_service.py`
- **SOLO** procesa credenciales encriptadas
- Valida credenciales desencriptadas
- Sanitiza credenciales para logs

### 3. Schemas Actualizados: `app/schemas.py`
- Nuevo schema: `CredencialesEncriptadas`
- `EmisionRequest` **REQUIERE** `credenciales_encrypted`
- `NotaCreditoRequest` **REQUIERE** `credenciales_encrypted`
- Validación automática (rechaza texto plano)

### 4. Rutas Actualizadas: `app/api/emission_routes.py`
- Desencripta credenciales automáticamente
- Sanitiza logs (no muestra contraseñas)
- Maneja errores de desencriptación

---

## 🔧 Implementación en Frontend

### 1. Crear Módulo de Encriptación

Crear `services/crypto.ts`:

```typescript
// services/crypto.ts
const ENCRYPTION_KEY = import.meta.env.VITE_ENCRYPTION_KEY || 'fM-2026-sUnAt-CrEdS-k3y-Ch4ng3-1n-Pr0d';
const SALT = new TextEncoder().encode('factumovil-salt-v1');

async function deriveKey(password: string): Promise<CryptoKey> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: SALT,
      iterations: 100000,
      hash: 'SHA-256'
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

export async function encryptCredential(plaintext: string): Promise<string> {
  const key = await deriveKey(ENCRYPTION_KEY);
  const encoder = new TextEncoder();
  const data = encoder.encode(plaintext);
  
  // Generar IV aleatorio (12 bytes para AES-GCM)
  const iv = crypto.getRandomValues(new Uint8Array(12));
  
  // Encriptar
  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    data
  );
  
  // Combinar IV + datos encriptados
  const combined = new Uint8Array(iv.length + encrypted.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encrypted), iv.length);
  
  // Convertir a Base64
  return btoa(String.fromCharCode(...combined));
}

export async function encryptCredentials(credentials: {
  ruc: string;
  usuario: string;
  password: string;
}) {
  return {
    ruc_encrypted: await encryptCredential(credentials.ruc),
    usuario_encrypted: await encryptCredential(credentials.usuario),
    password_encrypted: await encryptCredential(credentials.password)
  };
}
```

### 2. Actualizar Servicio de API

Actualizar `services/sunatApi.ts`:

```typescript
import { encryptCredentials } from './crypto';

export const SunatApiService = {
  async emitir(
    invoice: Invoice,
    items: InvoiceItem[],
    sender: Sender,
    client: Client,
    credentials: SunatCredentials
  ): Promise<{ taskId: string }> {
    // ... código existente ...
    
    // Encriptar credenciales antes de enviar (OBLIGATORIO)
    const credenciales_encrypted = await encryptCredentials(credentials);
    
    const request = {
      tipo_documento: invoice.type === InvoiceType.FACTURA ? 'FACTURA' : 'BOLETA',
      fecha,
      cliente: clienteData,
      productos,
      resumen: { ... },
      id_remitente: invoice.id,
      credenciales_encrypted  // ← OBLIGATORIO
      // NO enviar: credenciales (texto plano) - RECHAZADO por el backend
    };

    const response = await fetch(`${API_BASE_URL}/api/v1/emitir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    
    // ...
  }
};
```

### 3. Configurar Variable de Entorno

En `.env.local`:

```bash
# IMPORTANTE: Misma clave que el backend
VITE_ENCRYPTION_KEY=fM-2026-sUnAt-CrEdS-k3y-Ch4ng3-1n-Pr0d
```

---

## 🔄 Flujo de Seguridad (SOLO Encriptado)

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND                                 │
│  1. Usuario ingresa credenciales                            │
│  2. Encripta con AES-256-GCM (OBLIGATORIO)                  │
│  3. Envía credenciales_encrypted                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTPS
                 │ {
                 │   "credenciales_encrypted": {
                 │     "ruc_encrypted": "base64...",
                 │     "usuario_encrypted": "base64...",
                 │     "password_encrypted": "base64..."
                 │   }
                 │ }
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND                                  │
│  4. Valida que credenciales_encrypted esté presente         │
│  5. Desencripta con la misma clave                          │
│  6. Valida credenciales desencriptadas                      │
│  7. Usa credenciales solo en memoria                        │
│  8. Logs muestran: ruc: "104***", usuario: "***"            │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Validación Automática

Pydantic rechaza automáticamente:

```python
# ❌ INVÁLIDO - Falta credenciales_encrypted
{
  "tipo_documento": "BOLETA",
  "fecha": "06/01/2026",
  "cliente": {"nombre": "Test"},
  "productos": [...],
  "resumen": {...},
  "id_remitente": "test-id"
  # Falta: credenciales_encrypted
}
# Error: "Field required"

# ❌ INVÁLIDO - Intenta enviar texto plano
{
  "tipo_documento": "BOLETA",
  ...
  "credenciales": {
    "ruc": "10433439070",
    "usuario": "MPREASSI",
    "password": "MiPassword123"
  }
}
# Error: "Extra inputs are not permitted"

# ✅ VÁLIDO - Solo formato encriptado
{
  "tipo_documento": "BOLETA",
  ...
  "credenciales_encrypted": {
    "ruc_encrypted": "base64...",
    "usuario_encrypted": "base64...",
    "password_encrypted": "base64..."
  }
}
```

---

## 🧪 Testing

### Test en Backend

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python run.py

# Probar endpoint (DEBE usar credenciales encriptadas)
curl -X POST http://localhost:8080/api/v1/emitir \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_documento": "BOLETA",
    "fecha": "06/01/2026",
    "cliente": {"nombre": "Test"},
    "productos": [{"cantidad": 1, "descripcion": "Test", "unidad_medida": "UND", "precio_base": 100, "igv": 18, "precio_total": 118}],
    "resumen": {"serie": "B001", "numero": "00001", "sub_total": 100, "igv_total": 18, "total": 118},
    "id_remitente": "test-id",
    "credenciales_encrypted": {
      "ruc_encrypted": "...",
      "usuario_encrypted": "...",
      "password_encrypted": "..."
    }
  }'
```

### Test en Frontend

```typescript
import { encryptCredentials } from './services/crypto';

async function testEncryption() {
  const credentials = {
    ruc: "10433439070",
    usuario: "MPREASSI",
    password: "MiPassword123"
  };
  
  // Encriptar (OBLIGATORIO)
  const encrypted = await encryptCredentials(credentials);
  console.log('Encrypted:', encrypted);
  
  // Enviar al backend
  const response = await fetch('http://localhost:8080/api/v1/emitir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tipo_documento: "BOLETA",
      fecha: "06/01/2026",
      cliente: { nombre: "Test" },
      productos: [...],
      resumen: {...},
      id_remitente: "test-id",
      credenciales_encrypted: encrypted  // ← OBLIGATORIO
    })
  });
  
  console.log('Response:', await response.json());
}
```

---

## 🔒 Configuración de Producción

### Backend

1. Generar clave segura:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. Configurar en `.env`:
```bash
ENCRYPTION_KEY=<clave-generada>
```

3. Asegurar HTTPS:
```python
# app/main.py
if os.getenv("ENVIRONMENT") == "production":
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)
```

### Frontend

1. Configurar en `.env.local`:
```bash
VITE_ENCRYPTION_KEY=<misma-clave-que-backend>
```

2. **CRÍTICO:** La clave DEBE ser la misma en ambos lados

---

## 📊 Comparación: Antes vs Después

### Antes (Inseguro)
```json
{
  "credenciales": {
    "ruc": "10433439070",
    "usuario": "MPREASSI",
    "password": "MiPassword123"  // ⚠️ Texto plano
  }
}
```

### Ahora (Seguro)
```json
{
  "credenciales_encrypted": {
    "ruc_encrypted": "base64...",
    "usuario_encrypted": "base64...",
    "password_encrypted": "base64..."
  }
}
```

**Logs del Backend:**
```
INFO: Tarea abc123 creada para BOLETA con credenciales: {'ruc': '104***', 'usuario': '***', 'password': '***'}
```

---

## ⚠️ Consideraciones Críticas

### 1. Clave de Encriptación
- **DEBE** ser la MISMA en frontend y backend
- Cambiarla invalida todas las credenciales encriptadas
- Guardar en variables de entorno, **NUNCA** en código

### 2. HTTPS Obligatorio
- En producción, **SIEMPRE** usar HTTPS
- Sin HTTPS, la encriptación adicional no sirve de mucho

### 3. No hay compatibilidad hacia atrás
- El backend **NO** acepta credenciales en texto plano
- El frontend **DEBE** encriptar SIEMPRE
- No hay "modo legacy"

### 4. Errores de Desencriptación
- Si la clave no coincide: Error 400 "Error al desencriptar credenciales"
- Si falta `credenciales_encrypted`: Error 422 "Field required"
- Si envía `credenciales`: Error 422 "Extra inputs are not permitted"

---

## 🚀 Próximos Pasos

### Implementación Inmediata
1. [ ] Crear `services/crypto.ts` en frontend
2. [ ] Actualizar `services/sunatApi.ts` para encriptar SIEMPRE
3. [ ] Configurar `VITE_ENCRYPTION_KEY` en `.env.local`
4. [ ] Probar con credenciales de prueba

### Producción
1. [ ] Generar clave segura para producción
2. [ ] Configurar HTTPS
3. [ ] Actualizar variables de entorno
4. [ ] Probar flujo completo

---

## 🔍 Validación

### Código
- ✅ Solo acepta credenciales encriptadas
- ✅ Validación automática de Pydantic
- ✅ Sanitización de logs
- ✅ Manejo de errores específicos

### Seguridad
- ✅ Credenciales NUNCA en texto plano
- ✅ Encriptación AES-256-GCM
- ✅ HTTPS obligatorio en producción
- ✅ Logs no exponen datos sensibles

---

**Política de encriptación obligatoria implementada.** 🔐
