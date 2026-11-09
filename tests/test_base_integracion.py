import asyncio
from pathlib import Path

import pytest
from fastapi import Depends

from app.db import migrar
from app.security import requiere, resumir_token
from scripts.sembrar_demo import sembrar
from tests.conftest import ingresar

pytestmark = pytest.mark.integracion


async def test_sesion_cookie_hash_logout_y_expiracion(entorno):
    cliente, pool, _ = entorno
    assert (await cliente.get("/api/solicitudes")).status_code == 401
    respuesta = await ingresar(cliente)
    assert respuesta.status_code == 200
    assert "HttpOnly" in respuesta.headers["set-cookie"]
    assert "SameSite=strict" in respuesta.headers["set-cookie"]
    token = cliente.cookies["nexus_sesion"]
    assert await pool.fetchval("SELECT token_hash FROM sesiones") == resumir_token(token)
    assert (await cliente.get("/api/auth/me")).json()["rol"] == "admin"
    assert (await cliente.post("/api/auth/logout")).status_code == 204
    assert await pool.fetchval("SELECT count(*) FROM sesiones") == 0
    assert (await cliente.get("/api/auth/me")).status_code == 401
    await ingresar(cliente)
    await pool.execute("UPDATE sesiones SET expira_en=now()-interval '1 second'")
    assert (await cliente.get("/api/auth/me")).status_code == 401


async def test_limite_persiste_y_se_recupera(entorno):
    cliente, pool, _ = entorno
    for _ in range(5):
        assert (await ingresar(cliente, contrasena="mal")).status_code == 401
    assert (await ingresar(cliente)).status_code == 429
    await pool.execute("UPDATE intentos_login SET ventana_en=now()-interval '16 minutes'")
    assert (await ingresar(cliente)).status_code == 200


async def test_limite_concurrente(entorno):
    cliente, _, _ = entorno
    respuestas = await asyncio.gather(*(ingresar(cliente, contrasena="mal") for _ in range(8)))
    assert sum(r.status_code == 401 for r in respuestas) == 5
    assert sum(r.status_code == 429 for r in respuestas) == 3


async def test_roles_backend(entorno):
    cliente, _, app = entorno

    # Prueba el mismo guard que usarán los routers de la fase 5, sin crear endpoints falsos.
    @app.get("/api/prueba-reglas", dependencies=[Depends(requiere("reglas"))])
    async def reglas():
        return {"permitido": True}

    await ingresar(cliente, "gestor@example.test")
    assert (await cliente.get("/api/prueba-reglas")).status_code == 403
    assert (await cliente.get("/api/solicitudes")).status_code == 200
    await ingresar(cliente)
    assert (await cliente.get("/api/prueba-reglas")).status_code == 200


async def test_migraciones_y_semilla_idempotentes(entorno):
    _, pool, _ = entorno
    await migrar(pool)
    # También se verifica la idempotencia del SQL, sin depender del registro de migraciones.
    for p in sorted((Path(__file__).parents[1] / "db").glob("*.sql")):
        if any(
            linea.strip() and not linea.strip().startswith("--")
            for linea in p.read_text().splitlines()
        ):
            await pool.execute(p.read_text())
    await sembrar(pool)
    assert await pool.fetchval("SELECT count(*) FROM solicitudes") == 8
    assert await pool.fetchval("SELECT count(*) FROM migraciones") == 2


async def test_resumen_filtros_paginacion_busqueda(entorno):
    cliente, _, _ = entorno
    await ingresar(cliente)
    resumen = (await cliente.get("/api/solicitudes/resumen")).json()
    assert resumen["indicadores"] == dict(
        solicitudes=37, registros=12, completados=9, respuestas=14, bajas=2
    )
    assert len(resumen["serie"]) == 14
    assert resumen["serie"][-1]["cantidad"] == 37
    lista = (await cliente.get("/api/solicitudes?origen=Google&tamano=1")).json()
    assert lista["total"] == 2
    assert len(lista["items"]) == 1
    segunda = (await cliente.get("/api/solicitudes?origen=Google&tamano=1&pagina=2")).json()
    assert lista["items"][0]["id"] != segunda["items"][0]["id"]
    assert (await cliente.get("/api/solicitudes?origen=Inexistente")).json()["total"] == 0
    assert (await cliente.get("/api/solicitudes?pagina=0")).status_code == 422
    assert len((await cliente.get("/api/buscar?q=Mirador")).json()["solicitudes"]) == 1
    assert (await cliente.get("/api/buscar?q=%25%25")).json()["solicitudes"] == []
    assert (await cliente.get("/api/pendientes")).json()["cantidad"] == 3


async def test_csrf_errores_y_cors(entorno):
    cliente, _, _ = entorno
    assert (
        await cliente.post("/api/auth/login", headers={"X-Nexus-Request": "0"}, json={})
    ).status_code == 403
    assert (
        await cliente.post("/api/auth/login", headers={"Origin": "https://malicioso.test"}, json={})
    ).status_code == 403
    respuesta = await cliente.post("/api/auth/login", json={})
    assert respuesta.status_code == 422
    assert set(respuesta.json()) == {"codigo", "mensaje"}
    assert (await cliente.get("/no-existe")).status_code == 404
    assert set((await cliente.get("/no-existe")).json()) == {"codigo", "mensaje"}
    respuesta = await cliente.options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_no_mezcla_demo_y_datos_reales(entorno):
    cliente, _, app = entorno
    await ingresar(cliente)
    app.state.cfg.demo = False
    respuesta = (await cliente.get("/api/solicitudes")).json()
    assert respuesta["total"] == 0
    resumen = (await cliente.get("/api/solicitudes/resumen")).json()
    assert resumen["indicadores"]["solicitudes"] == 0
    assert len(resumen["serie"]) == 14
    assert not resumen["demo"]


async def test_usuario_desactivado_y_health(entorno):
    cliente, pool, _ = entorno
    await ingresar(cliente)
    await pool.execute("UPDATE usuarios SET activo=false WHERE rol='admin'")
    assert (await cliente.get("/api/auth/me")).status_code == 401
    assert (await ingresar(cliente)).status_code == 401
    assert (await cliente.get("/api/health")).json()["estado"] == "ok"
