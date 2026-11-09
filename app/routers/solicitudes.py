from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.marketing import solicitudes
from app.security import requiere

router = APIRouter(tags=["Solicitudes"], dependencies=[Depends(requiere("solicitudes"))])


@router.get("/solicitudes/resumen")
async def resumen(request: Request):
    return await solicitudes.resumen(request.app.state.pool, request.app.state.cfg.demo)


@router.get("/solicitudes/opciones")
async def opciones(request: Request):
    return await solicitudes.opciones(request.app.state.pool, request.app.state.cfg.demo)


@router.get("/solicitudes")
async def listar(
    request: Request,
    fecha: date | None = None,
    tipo: str | None = None,
    origen: str | None = None,
    estado: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(8, ge=1, le=100),
):
    return await solicitudes.listar(
        request.app.state.pool,
        request.app.state.cfg.demo,
        fecha,
        tipo,
        origen,
        estado,
        pagina,
        tamano,
    )


@router.get("/pendientes")
async def pendientes(request: Request):
    cantidad = 0
    if request.app.state.cfg.demo:
        cantidad = (
            await request.app.state.pool.fetchval(
                "SELECT pendientes FROM demo_indicadores WHERE fecha=$1", solicitudes.hoy()
            )
            or 0
        )
    return {"cantidad": cantidad, "demo": request.app.state.cfg.demo}


@router.get("/buscar")
async def buscar(request: Request, q: str = Query(min_length=2, max_length=100)):
    return await solicitudes.buscar(request.app.state.pool, request.app.state.cfg.demo, q.strip())
