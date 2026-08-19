from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Usuario, Wallet
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.api.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.services import kafka_service

router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Verificar duplicados
    if db.query(Usuario).filter(Usuario.username == req.username).first():
        raise HTTPException(400, "El usuario ya existe")
    if db.query(Usuario).filter(Usuario.email == req.email).first():
        raise HTTPException(400, "El email ya esta registrado")
    if db.query(Usuario).filter(Usuario.cedula == req.cedula).first():
        raise HTTPException(400, "La cedula ya esta registrada")

    # Crear usuario
    usuario = Usuario(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        nombre=req.nombre,
        cedula=req.cedula,
    )
    db.add(usuario)
    db.flush()

    # Crear wallet con saldo 0
    wallet = Wallet(usuario_id=usuario.id, saldo=0.0)
    db.add(wallet)
    db.commit()
    db.refresh(usuario)

    kafka_service.publicar_auditoria("REGISTER", req.username,
        f"Nuevo usuario registrado cedula={req.cedula}")

    token = create_access_token({"sub": usuario.username})
    return TokenResponse(
        access_token=token,
        nombre=usuario.nombre,
        cedula=usuario.cedula,
        saldo_wallet=0.0
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.username == req.username).first()

    if not usuario or not verify_password(req.password, usuario.password_hash):
        kafka_service.publicar_auditoria("LOGIN_FALLIDO", req.username,
            "Credenciales incorrectas")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos"
        )

    if not usuario.activo:
        raise HTTPException(400, "Usuario inactivo")

    kafka_service.publicar_auditoria("LOGIN_OK", req.username, "Login exitoso")

    saldo = usuario.wallet.saldo if usuario.wallet else 0.0
    token = create_access_token({"sub": usuario.username})
    return TokenResponse(
        access_token=token,
        nombre=usuario.nombre,
        cedula=usuario.cedula,
        saldo_wallet=saldo
    )


@router.get("/me")
async def me(usuario: Usuario = Depends(get_current_user)):
    return {
        "username": usuario.username,
        "nombre":   usuario.nombre,
        "email":    usuario.email,
        "cedula":   usuario.cedula,
        "saldo_wallet": usuario.wallet.saldo if usuario.wallet else 0.0
    }
