import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from starlette.concurrency import run_in_threadpool

from app.errors import ErrorAplicacion

hasher = PasswordHasher()
# Iguala el trabajo de verificación cuando el correo no existe.
HASH_FICTICIO = hasher.hash(secrets.token_urlsafe(32))
PERMISOS = {
    "admin": {"solicitudes", "bandeja", "agentes", "graficas", "reglas"},
    "gestor_anuncios": {"solicitudes", "bandeja", "graficas"},
}


def resumir_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verificar_clave(clave: str, almacenada: str) -> bool:
    try:
        return hasher.verify(almacenada, clave)
    except VerificationError, InvalidHashError, UnicodeError:
        return False


def puede(rol: str, recurso: str) -> bool:
    return recurso in PERMISOS.get(rol, set())


async def autenticar(pool, cfg, correo: str, clave: str, ip: str):
    claves = sorted([resumir_token("correo:" + correo), resumir_token("ip:" + ip)])
    ahora = datetime.now(timezone.utc)
    bloqueado = False
    usuario = None
    token = None
    async with pool.acquire() as con:
        async with con.transaction():
            # Bloqueos ordenados: el límite sigue funcionando con múltiples workers.
            for identificador in claves:
                await con.execute(
                    "INSERT INTO intentos_login(clave_hash) VALUES($1) ON CONFLICT DO NOTHING",
                    identificador,
                )
                fila = await con.fetchrow(
                    "SELECT * FROM intentos_login WHERE clave_hash=$1 FOR UPDATE", identificador
                )
                if ahora - fila["ventana_en"] >= timedelta(minutes=cfg.login_ventana_minutos):
                    await con.execute(
                        "UPDATE intentos_login SET intentos=0, ventana_en=$2 WHERE clave_hash=$1",
                        identificador,
                        ahora,
                    )
                elif fila["intentos"] >= cfg.login_max_intentos:
                    bloqueado = True
            if not bloqueado:
                usuario = await con.fetchrow("SELECT * FROM usuarios WHERE correo=$1", correo)
                valido = await run_in_threadpool(
                    verificar_clave, clave, usuario["contrasena_hash"] if usuario else HASH_FICTICIO
                )
                if not valido or not usuario or not usuario["activo"]:
                    usuario = None
                    await con.execute(
                        "UPDATE intentos_login SET intentos=intentos+1 "
                        "WHERE clave_hash=ANY($1::text[])",
                        claves,
                    )
                else:
                    # No reiniciar el contador IP: evita evadirlo con una cuenta válida.
                    await con.execute(
                        "DELETE FROM intentos_login WHERE clave_hash=$1",
                        resumir_token("correo:" + correo),
                    )
                    token = secrets.token_urlsafe(48)
                    await con.execute(
                        "INSERT INTO sesiones(token_hash,usuario_id,expira_en) VALUES($1,$2,$3)",
                        resumir_token(token),
                        usuario["id"],
                        ahora + timedelta(hours=cfg.sesion_horas),
                    )
                    await con.execute("DELETE FROM sesiones WHERE expira_en <= now()")
                    if hasher.check_needs_rehash(usuario["contrasena_hash"]):
                        nuevo = await run_in_threadpool(hasher.hash, clave)
                        await con.execute(
                            "UPDATE usuarios SET contrasena_hash=$1 WHERE id=$2",
                            nuevo,
                            usuario["id"],
                        )
    # Fuera de la transacción para conservar los intentos fallidos.
    if bloqueado:
        raise ErrorAplicacion(
            "demasiados_intentos", "Espere unos minutos antes de intentar nuevamente.", 429
        )
    if not usuario:
        raise ErrorAplicacion("credenciales_invalidas", "Correo o contraseña incorrectos.", 401)
    return token, usuario


async def sesion_actual(request: Request):
    token = request.cookies.get("nexus_sesion", "")
    if not token:
        raise ErrorAplicacion("sin_sesion", "Inicie sesión para continuar.", 401)
    usuario = await request.app.state.pool.fetchrow(
        """
        SELECT u.id,u.correo,u.nombre,u.rol FROM sesiones s
        JOIN usuarios u ON u.id=s.usuario_id
        WHERE s.token_hash=$1 AND s.expira_en>now() AND u.activo
    """,
        resumir_token(token),
    )
    if not usuario:
        raise ErrorAplicacion("sesion_expirada", "Su sesión terminó. Ingrese nuevamente.", 401)
    return dict(usuario)


def requiere(recurso: str):
    async def comprobar(usuario=Depends(sesion_actual)):
        if not puede(usuario["rol"], recurso):
            raise ErrorAplicacion("sin_permiso", "Su rol no tiene acceso a esta sección.", 403)
        return usuario

    return comprobar
