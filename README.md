# Backend API REST - Sistema de Facturación SUNAT

API REST para centralizar la emisión de comprobantes (boletas y facturas) a SUNAT mediante web scraping con Selenium.

## Características

- Emisión asíncrona de boletas y facturas
- Consulta de estado de emisiones
- Validación de datos antes de enviar
- Documentación automática con Swagger
- Soporte para Docker

## Requisitos

- Python 3.11+
- Chrome/Chromium
- ChromeDriver (se instala automáticamente con webdriver-manager)

## Instalación Local

```bash
# Clonar repositorio
git clone <repo-url>
cd backend-sunat

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# Iniciar servidor
python run.py
```

## Instalación con Docker

```bash
# Construir imagen
docker-compose build

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f api
```

## Uso de la API

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Emitir Boleta

```bash
curl -X POST http://localhost:8000/api/v1/emitir \
  -H "Content-Type: application/json" \
  -d @test_boleta.json
```

### Consultar Estado

```bash
curl http://localhost:8000/api/v1/status/{task_id}
```

### Validar Datos

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d @test_boleta.json
```

## Documentación

Una vez iniciado el servidor, accede a:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Estructura del Proyecto

```
backend-sunat/
├── app/                     # Aplicación principal
│   ├── main.py             # Punto de entrada FastAPI
│   ├── config.py           # Configuración
│   ├── schemas.py          # Schemas Pydantic
│   ├── api/                # Endpoints REST
│   │   ├── emission_secure_routes.py
│   │   └── sender_routes.py
│   ├── services/           # Lógica de negocio
│   │   ├── scraper_service.py      # Scraping SUNAT (boletas, facturas, notas de crédito)
│   │   ├── driver_manager.py       # Pool de drivers Selenium
│   │   ├── worker_manager.py       # Gestión de workers
│   │   ├── queue_manager.py        # Cola Redis
│   │   ├── task_processor.py       # Procesamiento de tareas
│   │   ├── auth_service.py         # Autenticación
│   │   ├── credential_service.py   # Manejo de credenciales
│   │   └── sender_service.py       # Lógica de emisores
│   └── utils/              # Utilidades
│       ├── logger.py       # Sistema de logging
│       ├── encryption.py   # Cifrado de credenciales
│       ├── selenium_utils.py       # Helpers Selenium
│       ├── redis_client.py         # Cliente Redis
│       ├── supabase_client.py      # Cliente Supabase
│       └── task_storage.py         # Almacenamiento de tareas
├── tests/                  # Tests organizados
│   ├── unit/              # Tests unitarios
│   ├── integration/       # Tests de integración
│   ├── use_cases/         # Tests de casos de uso
│   ├── data/              # Datos de prueba
│   │   ├── boleta_sample.json
│   │   ├── factura_sample.json
│   │   └── nota_credito_sample.json
│   ├── conftest.py        # Configuración pytest
│   └── run_tests.py       # Runner de tests
├── scripts/               # Scripts utilitarios
│   ├── generate_test_token.py
│   ├── security_check.py
│   ├── load_test.py
│   └── install_chromedriver.py
├── docs/                  # Documentación
│   ├── API_GUIDE.md
│   ├── INTEGRATION_PROMPT.md
│   └── FRONTEND_ENCRYPTION_INTEGRATION.md
├── run.py                 # Script de inicio
├── requirements.txt       # Dependencias
├── Dockerfile            # Contenedor Docker
├── docker-compose.yml    # Orquestación
├── .env.example          # Template de configuración
└── README.md             # Este archivo
```

## Estados de Tareas

- `pending`: En cola
- `processing`: Ejecutándose
- `completed`: Completado exitosamente
- `failed`: Error en el proceso

## Integración con App Escritorio

```python
import requests

class BoletaController:
    def __init__(self):
        self.api_url = "http://localhost:8000"
    
    def emitir_boleta(self, boleta_data):
        # Enviar a API
        response = requests.post(
            f"{self.api_url}/api/v1/emitir",
            json=boleta_data,
            timeout=10
        )
        
        if response.status_code == 202:
            task_id = response.json()["task_id"]
            return self.wait_for_completion(task_id)
        
        return False
    
    def wait_for_completion(self, task_id, timeout=300):
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.api_url}/api/v1/status/{task_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "completed":
                    return data["result"]["success"]
                elif data["status"] == "failed":
                    return False
            
            time.sleep(5)
        
        return False
```

## Licencia

MIT
