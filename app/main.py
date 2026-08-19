from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.core.config import get_settings
from app.db.database import create_tables
from app.api import auth, wallet, health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: crear tablas si no existen
    create_tables()
    print(f"sinerfin-wallet {settings.app_version} iniciado")
    yield
    # Shutdown
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

# Routers
app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(health.router)

# Servir frontend React (si existe el build)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
