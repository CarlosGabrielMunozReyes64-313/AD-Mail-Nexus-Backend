import argparse
import asyncio
from getpass import getpass
from uuid import uuid4

from app.config import Configuracion
from app.db import conectar
from app.security import hasher


async def main():
    parser = argparse.ArgumentParser(description="Crear un usuario interno sin enviar correos")
    parser.add_argument("--correo", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--rol", choices=["admin", "gestor_anuncios"], default="admin")
    args = parser.parse_args()
    clave = getpass("Contraseña (mínimo 12 caracteres): ")
    if len(clave) < 12 or clave != getpass("Repita la contraseña: "):
        raise SystemExit("Contraseña insuficiente o confirmación diferente.")
    if "@" not in args.correo:
        raise SystemExit("Correo inválido.")
    pool = await conectar(Configuracion().database_url.get_secret_value())
    try:
        resultado = await pool.execute(
            """INSERT INTO usuarios(id,correo,nombre,contrasena_hash,rol)
            VALUES($1,$2,$3,$4,$5) ON CONFLICT(correo) DO NOTHING""",
            uuid4(),
            args.correo.strip().lower(),
            args.nombre,
            hasher.hash(clave),
            args.rol,
        )
        print(
            "Usuario creado."
            if resultado.endswith("1")
            else "El usuario ya existe; no fue modificado."
        )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
