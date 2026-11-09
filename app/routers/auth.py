from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.security import autenticar, resumir_token, sesion_actual

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class Credenciales(BaseModel):
    correo: str = Field(min_length=3, max_length=254)
    contrasena: str = Field(min_length=1, max_length=1024)

    @field_validator("correo")
    @classmethod
    def normalizar(cls, valor):
        valor = valor.strip().lower()
        if "@" not in valor:
            raise ValueError("Correo inválido")
        return valor


@router.post("/login")
async def login(datos: Credenciales, request: Request, response: Response):
    cfg = request.app.state.cfg
    token, usuario = await autenticar(
        request.app.state.pool,
        cfg,
        datos.correo,
        datos.contrasena,
        request.client.host if request.client else "desconocido",
    )
    response.set_cookie(
        "nexus_sesion",
        token,
        httponly=True,
        secure=cfg.cookie_segura,
        samesite="strict",
        max_age=cfg.sesion_horas * 3600,
        path="/api",
    )
    return {k: usuario[k] for k in ("id", "correo", "nombre", "rol")}


@router.get("/me")
async def me(usuario=Depends(sesion_actual)):
    return usuario


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, usuario=Depends(sesion_actual)):
    await request.app.state.pool.execute(
        "DELETE FROM sesiones WHERE token_hash=$1", resumir_token(request.cookies["nexus_sesion"])
    )
    response.delete_cookie(
        "nexus_sesion",
        path="/api",
        secure=request.app.state.cfg.cookie_segura,
        httponly=True,
        samesite="strict",
    )
