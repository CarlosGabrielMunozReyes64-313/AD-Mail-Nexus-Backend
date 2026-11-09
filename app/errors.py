import logging
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ErrorAplicacion(Exception):
    def __init__(self, codigo: str, mensaje: str, estado: int = 400):
        self.codigo, self.mensaje, self.estado = codigo, mensaje, estado


def enmascarar(texto: str) -> str:
    texto = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo oculto]", texto)
    return re.sub(r"(?<!\w)\+?\d[\d ()-]{8,}\d", "[teléfono oculto]", texto)


class FiltroPrivacidad(logging.Filter):
    def filter(self, record):
        record.msg = enmascarar(record.getMessage())
        record.args = ()
        return True


def configurar_errores(app: FastAPI):
    @app.exception_handler(ErrorAplicacion)
    async def negocio(_: Request, error: ErrorAplicacion):
        return JSONResponse(
            status_code=error.estado, content={"codigo": error.codigo, "mensaje": error.mensaje}
        )

    @app.exception_handler(RequestValidationError)
    async def validacion(_: Request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "codigo": "datos_invalidos",
                "mensaje": "Revise los campos enviados y sus formatos.",
            },
        )

    @app.exception_handler(HTTPException)
    async def http(_: Request, error: HTTPException):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "codigo": "peticion_invalida",
                "mensaje": "Recurso no disponible o petición no permitida.",
            },
        )

    @app.exception_handler(Exception)
    async def inesperado(_: Request, error: Exception):
        # No se registran cuerpos, tokens, credenciales ni excepciones con datos personales.
        logging.getLogger("nexus").error("Error interno de tipo %s", type(error).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "codigo": "error_interno",
                "mensaje": "No pudimos completar la operación. Intente nuevamente.",
            },
        )
