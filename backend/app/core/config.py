"""Configuración del backend leída desde variables de entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno del MVP."""

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str

    model_config = SettingsConfigDict(
        # Se aceptan .env en el directorio actual y en la raíz del repositorio.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia única de configuración."""
    # pydantic-settings llena los campos desde el entorno; mypy no lo infiere.
    return Settings()  # type: ignore[call-arg]
