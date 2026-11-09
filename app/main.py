import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Configuracion
from app.db import conectar
from app.errors import FiltroPrivacidad, configurar_errores
from app.routers import auth, solicitudes


def crear_app(configuracion=None, pool=None):
    @asynccontextmanager
    async def vida(app):
        cfg = configuracion or Configuracion()
        app.state.cfg = cfg
        app.state.pool = pool or await conectar(cfg.database_url.get_secret_value())
        yield
        if pool is None:
            await app.state.pool.close()

    app = FastAPI(title="AD Mail Nexus Manager", version="0.1.0", lifespan=vida)
    # La configuración se carga al construir la app; no hay credenciales por defecto.
    cfg = configuracion or Configuracion()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH"],
        allow_headers=["Content-Type", "X-Nexus-Request"],
    )

    @app.middleware("http")
    async def proteger(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            # Estas rutas usan cookie; cabecera obligatoria y Origin permitido previenen CSRF.
            # Los futuros eventos/webhooks usarán sus propios tokens y firmas.
            if request.url.path.startswith("/api/auth/"):
                origen = request.headers.get("origin")
                if request.headers.get("x-nexus-request") != "1" or (
                    origen and origen not in cfg.cors_origins
                ):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "codigo": "origen_no_permitido",
                            "mensaje": "La solicitud no procede de una aplicación autorizada.",
                        },
                    )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    configurar_errores(app)
    app.include_router(auth.router, prefix="/api")
    app.include_router(solicitudes.router, prefix="/api")

    @app.get("/api/health")
    async def health(request: Request):
        try:
            await request.app.state.pool.fetchval("SELECT 1")
        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "codigo": "base_no_disponible",
                    "mensaje": "No hay conexión con la base de datos.",
                },
            )
        return {"estado": "ok", "fase": 1}

    for manejador in logging.getLogger().handlers:
        manejador.addFilter(FiltroPrivacidad())
    return app
