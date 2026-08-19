from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Sinerfin Wallet"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "sinerfin-wallet-secret-key-change-in-prod"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Base de datos (PostgreSQL)
    database_url: str = "postgresql://sinerfin:SinergyPass2026.@192.168.1.192:5432/sinerfin_wallet"

    # Redis
    redis_host: str = "192.168.1.190"
    redis_port: int = 6379
    redis_db: int = 1  # DB 1 para wallet (DB 0 la usa sinerfin2)

    # Kafka
    kafka_bootstrap_servers: str = "192.168.1.190:9092"
    kafka_topic_wallet: str = "sinerfin.wallet"
    kafka_topic_auditoria: str = "sinerfin.auditoria"

    # sinerfin2 API
    sinerfin_base_url: str = "http://192.168.1.190:8080/sinerfin2-1.0"
    sinerfin_timeout: int = 10

    # CORS
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
