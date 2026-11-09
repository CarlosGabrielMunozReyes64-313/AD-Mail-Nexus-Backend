from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: SecretStr
    demo: bool = False
    nombre_producto: str = "AD mail nexus manager"
    cors_origins: list[str] = ["http://localhost:5173"]
    sesion_horas: int = Field(default=8, ge=1, le=168)
    cookie_segura: bool = True
    login_max_intentos: int = Field(default=5, ge=1)
    login_ventana_minutos: int = Field(default=15, ge=1)
    ia_proveedor: str = "simulado"
    gemini_modelo: str = ""
    gemini_api_key: SecretStr = SecretStr("")
