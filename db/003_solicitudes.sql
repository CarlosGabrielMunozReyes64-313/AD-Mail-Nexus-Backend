CREATE TABLE IF NOT EXISTS solicitudes (
    id uuid PRIMARY KEY,
    ocurrido_en timestamptz NOT NULL,
    tipo text NOT NULL,
    empresa text NOT NULL,
    municipio text NOT NULL,
    origen text NOT NULL,
    temperatura text NOT NULL CHECK (temperatura IN ('Caliente','Tibio','Frío')),
    estado text NOT NULL,
    demo boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS solicitudes_fecha_idx ON solicitudes(ocurrido_en DESC);
CREATE TABLE IF NOT EXISTS demo_indicadores (
    fecha date PRIMARY KEY,
    solicitudes integer NOT NULL,
    registros integer NOT NULL,
    completados integer NOT NULL,
    respuestas integer NOT NULL,
    bajas integer NOT NULL,
    pendientes integer NOT NULL
);
-- Los agregados reproducen la referencia; las ocho filas son una muestra de empresas.
CREATE TABLE IF NOT EXISTS demo_serie (
    fecha date PRIMARY KEY,
    cantidad integer NOT NULL CHECK (cantidad >= 0)
);
