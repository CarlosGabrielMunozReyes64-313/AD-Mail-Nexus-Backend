import asyncio

from app.config import Configuracion
from app.db import conectar, migrar


async def main():
    pool = await conectar(Configuracion().database_url.get_secret_value())
    try:
        await migrar(pool)
        print("Migraciones aplicadas correctamente.")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
