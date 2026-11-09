from pathlib import Path

import asyncpg


async def conectar(url: str):
    return await asyncpg.create_pool(url, min_size=1, max_size=10, command_timeout=30)


async def migrar(pool):
    # Bloqueo compartido por todos los procesos que intenten migrar la misma base.
    async with pool.acquire() as conexion:
        async with conexion.transaction():
            await conexion.execute("SELECT pg_advisory_xact_lock(7345801)")
            await conexion.execute("""CREATE TABLE IF NOT EXISTS migraciones (
                nombre text PRIMARY KEY, aplicada_en timestamptz NOT NULL DEFAULT now())""")
            for archivo in sorted((Path(__file__).resolve().parents[1] / "db").glob("*.sql")):
                sql = archivo.read_text().strip()
                if not sql or not any(
                    not linea.strip().startswith("--") for linea in sql.splitlines()
                ):
                    continue
                if not await conexion.fetchval(
                    "SELECT 1 FROM migraciones WHERE nombre=$1", archivo.name
                ):
                    await conexion.execute(sql)
                    await conexion.execute(
                        "INSERT INTO migraciones(nombre) VALUES($1)", archivo.name
                    )
