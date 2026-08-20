import redis
import json
from app.core.config import get_settings

# Pool lazy — se crea la primera vez que se usa, no al importar el módulo
# Así toma las variables de entorno ya resueltas por k3s
_pool: redis.ConnectionPool | None = None


def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        # Leer directamente del entorno para evitar el lru_cache de settings
        import os
        _pool = redis.ConnectionPool(
            host=os.environ.get("REDIS_HOST", "192.168.1.190"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=int(os.environ.get("REDIS_DB", 1)),
            password=os.environ.get("REDIS_PASSWORD") or None,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return redis.Redis(connection_pool=_pool)


class WalletCache:

    TTL_SALDO   = 30    # segundos
    TTL_PERFIL  = 300   # 5 minutos

    @staticmethod
    def _r() -> redis.Redis:
        return get_redis()

    # ── Saldo wallet ──────────────────────────────────────────
    @staticmethod
    def set_saldo(user_id: int, saldo: float):
        try:
            WalletCache._r().setex(f"wallet:saldo:{user_id}", WalletCache.TTL_SALDO, saldo)
        except Exception: pass

    @staticmethod
    def get_saldo(user_id: int) -> float | None:
        try:
            v = WalletCache._r().get(f"wallet:saldo:{user_id}")
            return float(v) if v else None
        except Exception: return None

    @staticmethod
    def invalidar_saldo(user_id: int):
        try:
            WalletCache._r().delete(f"wallet:saldo:{user_id}")
        except Exception: pass

    # ── Saldo sinerfin ────────────────────────────────────────
    @staticmethod
    def set_saldo_sinerfin(cedula: str, motor: str, data: dict):
        try:
            WalletCache._r().setex(
                f"wallet:sinerfin:{motor}:{cedula}",
                WalletCache.TTL_SALDO,
                json.dumps(data)
            )
        except Exception: pass

    @staticmethod
    def get_saldo_sinerfin(cedula: str, motor: str) -> dict | None:
        try:
            v = WalletCache._r().get(f"wallet:sinerfin:{motor}:{cedula}")
            return json.loads(v) if v else None
        except Exception: return None

    @staticmethod
    def invalidar_sinerfin(cedula: str, motor: str):
        try:
            WalletCache._r().delete(f"wallet:sinerfin:{motor}:{cedula}")
        except Exception: pass

    # ── Stats para dashboard ──────────────────────────────────
    @staticmethod
    def incr_transacciones():
        try:
            WalletCache._r().incr("wallet:stats:transacciones")
        except Exception: pass

    @staticmethod
    def get_stats() -> dict:
        try:
            r = WalletCache._r()
            return {
                "transacciones": int(r.get("wallet:stats:transacciones") or 0),
                "cache_hits":    int(r.get("wallet:stats:hits") or 0),
            }
        except Exception:
            return {"transacciones": 0, "cache_hits": 0}

    @staticmethod
    def is_alive() -> bool:
        try:
            return WalletCache._r().ping()
        except Exception: return False
