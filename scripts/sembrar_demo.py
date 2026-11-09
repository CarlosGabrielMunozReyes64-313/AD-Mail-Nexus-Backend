import asyncio
from datetime import datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from app.config import Configuracion
from app.db import conectar
from app.marketing.solicitudes import BOGOTA, hoy

FILAS = [
    (
        "10:42",
        "Diagnóstico completado",
        "Lácteos El Mirador SAS",
        "Pasto",
        "Facebook",
        "Caliente",
        "Por contactar",
    ),
    ("10:35", "Registro", "Café Sendero SAS", "Buesaco", "Google", "Tibio", "Registrada"),
    (
        "10:21",
        "Respuesta",
        "Textiles Río Claro SAS",
        "Cali",
        "LinkedIn",
        "Caliente",
        "En conversación",
    ),
    (
        "10:08",
        "Diagnóstico iniciado",
        "Agrosemillas del Sur SAS",
        "Ipiales",
        "WhatsApp",
        "Tibio",
        "En progreso",
    ),
    ("09:54", "Baja", "Panadería La Colina SAS", "Palmira", "Facebook", "Frío", "Retirada"),
    (
        "09:40",
        "Registro",
        "Frutas del Pacífico SAS",
        "Tumaco",
        "Cámara de comercio",
        "Frío",
        "Registrada",
    ),
    (
        "09:27",
        "Diagnóstico completado",
        "Empaques Verde Valle SAS",
        "Yumbo",
        "Google",
        "Caliente",
        "Por contactar",
    ),
    (
        "09:10",
        "Respuesta",
        "Turismo Montaña Viva SAS",
        "Túquerres",
        "WhatsApp",
        "Tibio",
        "Respondida",
    ),
]


async def sembrar(pool, fecha=None):
    fecha = fecha or hoy()
    async with pool.acquire() as con:
        async with con.transaction():
            for indice, (hora, *datos) in enumerate(FILAS):
                await con.execute(
                    """INSERT INTO solicitudes
                    (id,ocurrido_en,tipo,empresa,municipio,origen,temperatura,estado,demo)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,true) ON CONFLICT(id)
                    DO UPDATE SET ocurrido_en=excluded.ocurrido_en""",
                    uuid5(NAMESPACE_URL, f"nexus-demo-solicitud-{indice}"),
                    datetime.combine(fecha, time.fromisoformat(hora), BOGOTA),
                    *datos,
                )
            await con.execute(
                """INSERT INTO demo_indicadores VALUES($1,37,12,9,14,2,3)
                ON CONFLICT(fecha) DO NOTHING""",
                fecha,
            )
            for indice, cantidad in enumerate(
                [17, 21, 18, 24, 22, 28, 26, 30, 27, 33, 29, 31, 32, 37]
            ):
                await con.execute(
                    "INSERT INTO demo_serie VALUES($1,$2) ON CONFLICT(fecha) "
                    "DO UPDATE SET cantidad=excluded.cantidad",
                    fecha - timedelta(days=13 - indice),
                    cantidad,
                )


async def main():
    cfg = Configuracion()
    if not cfg.demo:
        raise SystemExit("Active DEMO=true para sembrar datos ficticios.")
    pool = await conectar(cfg.database_url.get_secret_value())
    try:
        await sembrar(pool)
        print(
            "Demostración preparada para hoy en America/Bogota. No se crearon usuarios ni envíos."
        )
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
