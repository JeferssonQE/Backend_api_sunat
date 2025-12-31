# 🚀 Quick Start - Deploy en 5 Minutos

## Opción Más Rápida: Railway.app

### Paso 1: Preparar el código (2 min)

```bash
cd backend-sunat

# Inicializar git
git init
git add .
git commit -m "Backend SUNAT API - Ready for deployment"
```

### Paso 2: Subir a GitHub (1 min)

1. Ve a https://github.com/new
2. Crea un repositorio llamado `backend-sunat`
3. **NO marques** "Initialize with README"
4. Clic en "Create repository"

```bash
# Conectar con GitHub
git remote add origin https://github.com/TU_USUARIO/backend-sunat.git
git branch -M main
git push -u origin main
```

### Paso 3: Deploy en Railway (2 min)

1. **Ir a Railway:** https://railway.app
2. **Login** con GitHub
3. **New Project** → "Deploy from GitHub repo"
4. **Seleccionar** tu repositorio `backend-sunat`
5. **Esperar** 5-10 minutos mientras se construye

### Paso 4: Obtener URL

1. En Railway, ve a tu proyecto
2. Clic en **"Settings"** → **"Domains"**
3. Clic en **"Generate Domain"**
4. Copia tu URL: `https://backend-sunat-production.up.railway.app`

### Paso 5: Probar

```bash
# Reemplaza con tu URL
curl https://tu-proyecto.up.railway.app/api/v1/health
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "selenium_ready": true
}
```

---

## 🎓 Bonus: GitHub Student Pack

**Obtén créditos gratis:**

1. Ve a: https://education.github.com/pack
2. Aplica con tu correo universitario
3. Sube foto de tu credencial
4. Espera 1-3 días de aprobación
5. Obtén:
   - **$200 USD** en DigitalOcean
   - **$100 USD** en Azure
   - Dominio **.me** gratis
   - Y más...

---

## 📱 Usar desde tu App

Una vez deployado, actualiza la URL en tu app:

```python
# En tu app de escritorio
API_URL = "https://tu-proyecto.up.railway.app"

# Emitir boleta
response = requests.post(
    f"{API_URL}/api/v1/emitir",
    json=boleta_data
)
```

---

## ⚠️ Importante

**NO subas credenciales a GitHub:**
- El archivo `.env` ya está en `.gitignore`
- Las credenciales se envían en cada request
- Nunca hagas commit de datos sensibles

---

## 🆘 Problemas Comunes

**Error: "No se puede conectar"**
- Espera 10-15 minutos después del deploy
- Verifica que el build terminó exitosamente

**Error: "ChromeDriver failed"**
- Es normal en el primer intento
- Railway instalará Chrome automáticamente
- Reintenta después de 5 minutos

**Error: "Out of memory"**
- Railway free tier tiene 512MB RAM
- Considera usar Fly.io (1GB RAM gratis)

---

¡Listo! Tu API está en la nube 🎉
