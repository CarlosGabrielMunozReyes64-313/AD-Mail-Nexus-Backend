CREATE TABLE IF NOT EXISTS usuarios (
    id uuid PRIMARY KEY,
    correo text NOT NULL UNIQUE CHECK (correo = lower(correo)),
    nombre text NOT NULL,
    contrasena_hash text NOT NULL,
    rol text NOT NULL CHECK (rol IN ('admin', 'gestor_anuncios')),
    activo boolean NOT NULL DEFAULT true,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sesiones (
    token_hash text PRIMARY KEY,
    usuario_id uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en timestamptz NOT NULL DEFAULT now(),
    expira_en timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS sesiones_expiracion_idx ON sesiones(expira_en);
CREATE TABLE IF NOT EXISTS intentos_login (
    clave_hash text PRIMARY KEY,
    intentos integer NOT NULL DEFAULT 0,
    ventana_en timestamptz NOT NULL DEFAULT now()
);
