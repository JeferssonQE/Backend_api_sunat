"""
Configuración simple para tests de Backend SUNAT
Fixtures básicas y configuración común
"""
import pytest
import os
import json
import asyncio
from pathlib import Path

# Configurar path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Fixture para manejar asyncio en tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def clean_redis():
    """Fixture: Redis limpio para tests"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        r.ping()
        r.flushdb()
        return True
    except Exception:
        return False


@pytest.fixture
def test_boleta():
    """Fixture: Datos de boleta de prueba"""
    data_path = Path(__file__).parent / "data" / "boleta_sample.json"
    with open(data_path, "r") as f:
        return json.load(f)


@pytest.fixture
def test_environment():
    """Fixture: Variables de entorno para tests"""
    test_env = {
        "SUNAT_URL": "https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm",
        "JWT_SECRET": "test-secret-key",
        "REDIS_URL": "redis://localhost:6379/15",
        "LOG_LEVEL": "INFO",
        "API_HOST": "127.0.0.1",
        "API_PORT": "8001",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "15",
        "MAX_WORKERS": "3",
        "WORKER_TIMEOUT": "120",
        "TASK_TIMEOUT": "120"
    }
    
    # Aplicar variables de entorno
    for key, value in test_env.items():
        os.environ[key] = value
    
    return test_env


# Configuración de logging para tests
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)