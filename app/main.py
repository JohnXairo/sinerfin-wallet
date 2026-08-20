import instana  # noqa: F401  — debe importarse primero para auto-instrumentar
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.config import get_settings
from app.db.database import create_tables
from app.api import auth, wallet, health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    # Inicializar pool Redis en arranque para que tome las variables de entorno correctas
    from app.services.redis_service import get_redis
    try:
        get_redis().ping()
        print("Redis conectado OK")
    except Exception as e:
        print(f"Redis no disponible al arrancar: {e}")
    print(f"sinerfin-wallet {settings.app_version} iniciado")
    yield
    print("sinerfin-wallet detenido")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Billetera digital integrada con sinerfin2 (core bancario)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers API
app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(health.router)

# Servir frontend
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/", include_in_schema=False)
    async def frontend():
        return FileResponse(os.path.join(static_path, "index.html"))
