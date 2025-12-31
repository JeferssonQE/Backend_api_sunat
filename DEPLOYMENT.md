# 🚀 Guía de Deployment - Backend SUNAT API

## Opciones Gratuitas para Estudiantes

### 1️⃣ Railway.app (RECOMENDADO)

**Ventajas:**
- $5 USD/mes de crédito gratis
- Deploy automático desde GitHub
- Dominio HTTPS gratis
- Fácil configuración

**Pasos:**

1. **Crear cuenta en Railway**
   - Ve a https://railway.app
   - Regístrate con tu cuenta de GitHub

2. **Subir código a GitHub**
   ```bash
   cd backend-sunat
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/backend-sunat.git
   git push -u origin main
   ```

3. **Crear proyecto en Railway**
   - Clic en "New Project"
   - Selecciona "Deploy from GitHub repo"
   - Autoriza Railway a acceder a tu repo
   - Selecciona el repositorio `backend-sunat`

4. **Configurar variables de entorno**
   - En Railway, ve a tu proyecto
   - Clic en "Variables"
   - Agrega:
     ```
     CHROME_HEADLESS=true
     LOG_LEVEL=INFO
     SUNAT_URL=https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm
     ```

5. **Deploy automático**
   - Railway detectará el Dockerfile
   - Iniciará el build automáticamente
   - En 5-10 minutos estará listo

6. **Obtener URL**
   - Ve a "Settings" → "Domains"
   - Clic en "Generate Domain"
   - Tu API estará en: `https://tu-proyecto.up.railway.app`

**Costo:** Gratis con $5/mes de crédito (suficiente para este proyecto)

---

### 2️⃣ Render.com

**Ventajas:**
- Completamente gratis
- Fácil de usar
- HTTPS automático

**Desventajas:**
- Se duerme después de 15 min sin uso
- Tarda ~30 segundos en despertar

**Pasos:**

1. **Crear cuenta**
   - Ve a https://render.com
   - Regístrate con GitHub

2. **Subir código a GitHub** (igual que Railway)

3. **Crear Web Service**
   - Clic en "New +"
   - Selecciona "Web Service"
   - Conecta tu repositorio GitHub
   - Selecciona `backend-sunat`

4. **Configuración:**
   - **Name:** backend-sunat-api
   - **Environment:** Docker
   - **Plan:** Free
   - **Docker Command:** (dejar vacío, usa el CMD del Dockerfile)

5. **Variables de entorno:**
   ```
   CHROME_HEADLESS=true
   LOG_LEVEL=INFO
   PORT=10000
   ```

6. **Deploy**
   - Clic en "Create Web Service"
   - Espera 10-15 minutos

7. **URL:** `https://backend-sunat-api.onrender.com`

**Costo:** Gratis (750 horas/mes)

---

### 3️⃣ Fly.io

**Ventajas:**
- 3 VMs gratis
- Buen rendimiento
- No se duerme

**Pasos:**

1. **Instalar Fly CLI**
   ```powershell
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login**
   ```bash
   fly auth login
   ```

3. **Crear app**
   ```bash
   cd backend-sunat
   fly launch
   ```
   - Nombre: backend-sunat-api
   - Region: Selecciona la más cercana (ej: Santiago, Chile)
   - PostgreSQL: No
   - Redis: No

4. **Configurar variables**
   ```bash
   fly secrets set CHROME_HEADLESS=true
   fly secrets set LOG_LEVEL=INFO
   ```

5. **Deploy**
   ```bash
   fly deploy
   ```

6. **URL:** `https://backend-sunat-api.fly.dev`

**Costo:** Gratis (3 VMs pequeñas)

---

### 4️⃣ GitHub Student Developer Pack 🎁

**¡IMPORTANTE!** Como estudiante, puedes obtener créditos gratis:

1. **Aplica aquí:** https://education.github.com/pack

2. **Obtendrás:**
   - **Azure:** $100 USD de crédito
   - **DigitalOcean:** $200 USD de crédito (1 año)
   - **Heroku:** Créditos gratis
   - **Namecheap:** Dominio .me gratis por 1 año
   - Y muchos más...

3. **Requisitos:**
   - Correo institucional (.edu o similar)
   - Foto de tu credencial de estudiante
   - Aprobación en 1-3 días

---

## 📝 Preparar para Deployment

### Actualizar requirements.txt

Asegúrate de que `requirements.txt` tenga todas las dependencias:

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
selenium==4.39.0
webdriver-manager==4.0.2
python-dotenv==1.0.0
```

### Crear .gitignore

```
venv/
__pycache__/
*.pyc
.env
chromedriver.exe
logs/
*.log
.vscode/
.idea/
```

---

## 🧪 Probar el Deployment

Una vez deployado, prueba:

```bash
# Health check
curl https://tu-dominio.com/api/v1/health

# Documentación
# Abre en navegador: https://tu-dominio.com/docs

# Emitir boleta
curl -X POST https://tu-dominio.com/api/v1/emitir \
  -H "Content-Type: application/json" \
  -d @test_boleta.json
```

---

## 💡 Recomendación Final

**Para empezar:** Railway.app
- Más fácil
- Mejor rendimiento
- $5/mes gratis es suficiente

**Si necesitas más:** GitHub Student Pack
- Obtén créditos en DigitalOcean o Azure
- Deploy en un VPS real
- Más control y recursos

---

## 🔒 Seguridad

**IMPORTANTE:** No subas credenciales a GitHub

1. **Nunca subas `.env` con credenciales reales**
2. **Usa variables de entorno en la plataforma**
3. **Agrega `.env` al `.gitignore`**

```bash
# Verificar que .env no esté en git
git status
# Si aparece .env, eliminarlo:
git rm --cached .env
```

---

## 📞 Soporte

Si tienes problemas:
- Railway: https://railway.app/discord
- Render: https://render.com/docs
- Fly.io: https://community.fly.io

¡Buena suerte con tu deployment! 🚀
