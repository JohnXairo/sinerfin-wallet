from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Sinerfin Wallet"
    app_version: str = "1.0.0"
    debug: bool = False

    # JWT — obligatorio en producción: openssl rand -hex 32
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Base de datos (PostgreSQL) — obligatorio
    database_url: str

    # Redis
    redis_host: str = "192.168.1.190"
    redis_port: int = 6379
    redis_db: int = 1  # DB 1 para wallet (DB 0 la usa sinerfin2)
    redis_password: str = ""  # dejar vacío si Redis no tiene contraseña

    # Kafka
    kafka_bootstrap_servers: str = "192.168.1.190:9092"
    kafka_topic_wallet: str = "sinerfin.wallet"
    kafka_topic_auditoria: str = "sinerfin.auditoria"

    # sinerfin2 API
    sinerfin_base_url: str = "http://192.168.1.190:8080/sinerfin2-1.0"
    sinerfin_timeout: int = 10

    # IBM MQ — bus.sinergy.local (192.168.1.186)
    # Usa REST API (puerto 9443) — no requiere librerías nativas
    mq_host: str = "bus.sinergy.local"
    mq_rest_port: int = 9443
    mq_queue_manager: str = "SINERFIN"
    mq_user: str = ""
    mq_password: str = ""
    mq_queue_recarga: str = "SINERFIN.RECARGA.REQUEST"

    # CORS — separar por comas en la variable de entorno:
    # CORS_ORIGINS='["http://wallet.sinergy.local","https://wallet.sinergy.com"]'
    # Para desarrollo local se puede dejar ["*"]
    cors_origins: list[str] = ["http://wallet.sinergy.local"]

    @field_validator("secret_key")
    @classmethod
    def secret_key_no_vacio(cls, v: str) -> str:
        if not v or len(v) < 16:
            raise ValueError(
                "SECRET_KEY debe tener al menos 16 caracteres. "
                "Genera una con: openssl rand -hex 32"
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
