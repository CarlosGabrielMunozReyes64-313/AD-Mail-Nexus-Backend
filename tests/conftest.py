import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

from app.config import Configuracion
from app.db import conectar, migrar
from app.main import crear_app
from app.security import hasher
from scripts.sembrar_demo import sembrar

load_dotenv()


@pytest.fixture
async def entorno():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Active TEST_DATABASE_URL para ejecutar integración PostgreSQL.")
    # Protección adicional frente a una URL de producción copiada por error.
    if not url.rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
        pytest.fail("La base TEST_DATABASE_URL debe terminar en _test.")
    pool = await conectar(url)
    await migrar(pool)
    await pool.execute(
        "TRUNCATE sesiones, usuarios, intentos_login, solicitudes, demo_indicadores, demo_serie CASCADE"
    )
    for correo, rol in [
        ("admin@example.test", "admin"),
        ("gestor@example.test", "gestor_anuncios"),
    ]:
        await pool.execute(
            "INSERT INTO usuarios(id,correo,nombre,contrasena_hash,rol) VALUES($1,$2,$3,$4,$5)",
            uuid4(),
            correo,
            "Usuario de prueba",
            hasher.hash("clave-de-prueba-123"),
            rol,
        )
    await sembrar(pool)
    cfg = Configuracion(database_url=url, demo=True, cookie_segura=False)
    app = crear_app(cfg, pool)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Nexus-Request": "1"},
        ) as cliente:
            yield cliente, pool, app
    await pool.close()


async def ingresar(cliente, correo="admin@example.test", contrasena="clave-de-prueba-123"):
    return await cliente.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})
