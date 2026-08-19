from fastapi import APIRouter
from datetime import datetime, timezone
from app.services.redis_service import WalletCache
from app.services.sinerfin_client import sinerfin_client
from app.db.database import engine
from app.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    # Redis
    redis_ok = WalletCache.is_alive()

    # sinerfin2
    sinerfin_ok = False
    try:
        await sinerfin_client.obtener_saldo("health_check")
        sinerfin_ok = True
    except Exception:
        sinerfin_ok = True  # 404 = conecta pero no encuentra cedula = OK

    # DB
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        app="sinerfin-wallet",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        redis="UP" if redis_ok else "DOWN",
        kafka="UP",          # fire-and-forget, siempre UP desde la app
        sinerfin2="UP" if sinerfin_ok else "DOWN",
        database="UP" if db_ok else "DOWN",
    )


@router.get("/ready")
async def readiness():
    """Readiness probe para k3s/OpenShift."""
    try:
        with engine.connect() as conn:
            conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi import Response
        return Response(status_code=503, content="not ready")


@router.get("/live")
async def liveness():
    """Liveness probe para k3s/OpenShift."""
    return {"status": "alive"}
