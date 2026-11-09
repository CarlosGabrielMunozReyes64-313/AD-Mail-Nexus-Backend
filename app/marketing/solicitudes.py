from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def hoy():
    return datetime.now(BOGOTA).date()


async def listar(pool, demo, fecha, tipo, origen, estado, pagina, tamano):
    async with pool.acquire() as con:
        async with con.transaction(isolation="repeatable_read", readonly=True):
            parametros = [demo, fecha, tipo, origen, estado]
            condicion = """demo=$1 AND ($2::date IS NULL OR
                (ocurrido_en AT TIME ZONE 'America/Bogota')::date=$2)
                AND ($3::text IS NULL OR tipo=$3) AND ($4::text IS NULL OR origen=$4)
                AND ($5::text IS NULL OR estado=$5)"""
            total = await con.fetchval(
                "SELECT count(*) FROM solicitudes WHERE " + condicion, *parametros
            )
            filas = await con.fetch(
                "SELECT * FROM solicitudes WHERE "
                + condicion
                + " ORDER BY ocurrido_en DESC,id LIMIT $6 OFFSET $7",
                *parametros,
                tamano,
                (pagina - 1) * tamano,
            )
    return {"items": [dict(f) for f in filas], "total": total, "pagina": pagina, "tamano": tamano}


async def resumen(pool, demo):
    fecha = hoy()
    if demo:
        fila = await pool.fetchrow("SELECT * FROM demo_indicadores WHERE fecha=$1", fecha)
        serie = await pool.fetch(
            "SELECT fecha,cantidad FROM demo_serie WHERE fecha BETWEEN $1 AND $2 ORDER BY fecha",
            fecha - timedelta(days=13),
            fecha,
        )
        indicadores = {
            k: fila[k] if fila else 0
            for k in ("solicitudes", "registros", "completados", "respuestas", "bajas")
        }
    else:
        filas = await pool.fetch(
            """SELECT tipo,count(*) AS cantidad FROM solicitudes
            WHERE NOT demo AND (ocurrido_en AT TIME ZONE 'America/Bogota')::date=$1 GROUP BY tipo""",
            fecha,
        )
        conteos = {f["tipo"]: f["cantidad"] for f in filas}
        indicadores = dict(
            solicitudes=sum(conteos.values()),
            registros=conteos.get("Registro", 0),
            completados=conteos.get("Diagnóstico completado", 0),
            respuestas=conteos.get("Respuesta", 0),
            bajas=conteos.get("Baja", 0),
        )
        serie = await pool.fetch(
            """SELECT d::date AS fecha,count(s.id) AS cantidad
            FROM generate_series($1::date,$2::date,interval '1 day') d LEFT JOIN solicitudes s
            ON (s.ocurrido_en AT TIME ZONE 'America/Bogota')::date=d::date AND NOT s.demo
            GROUP BY d ORDER BY d""",
            fecha - timedelta(days=13),
            fecha,
        )
    return {
        "indicadores": indicadores,
        "serie": [dict(f) for f in serie],
        "demo": demo,
        "fecha": fecha,
    }


async def opciones(pool, demo):
    filas = await pool.fetch(
        "SELECT DISTINCT tipo,origen,estado FROM solicitudes WHERE demo=$1", demo
    )
    return {k: sorted({f[k] for f in filas}) for k in ("tipo", "origen", "estado")}


async def buscar(pool, demo, texto):
    # LIKE recibe comodines escapados; el texto nunca se interpola en SQL.
    patron = "%" + texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    filas = await pool.fetch(
        """SELECT id,empresa,tipo,municipio FROM solicitudes
        WHERE demo=$1 AND (empresa ILIKE $2 OR tipo ILIKE $2 OR municipio ILIKE $2)
        ORDER BY ocurrido_en DESC LIMIT 10""",
        demo,
        patron,
    )
    return {"solicitudes": [dict(f) for f in filas], "planes": []}
