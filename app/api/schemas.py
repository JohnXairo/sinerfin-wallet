from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


# ── Auth ──────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username:  str
    email:     EmailStr
    password:  str
    nombre:    str
    cedula:    str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("La contrasena debe tener al menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    nombre:       str
    cedula:       str
    saldo_wallet: float


# ── Wallet ────────────────────────────────────────────────────
class SaldoResponse(BaseModel):
    saldo_wallet:   float
    saldo_sinerfin: float
    cuenta_sinerfin: int
    nombre:         str
    cedula:         str


class RecargaRequest(BaseModel):
    monto: float
    motor: str = "POSTGRES"

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class TransferenciaRequest(BaseModel):
    cedula_destino: str
    monto:          float
    descripcion:    Optional[str] = "Transferencia wallet"

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class PagoRequest(BaseModel):
    concepto: str
    monto:    float
    motor:    str = "POSTGRES"

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class TransaccionResponse(BaseModel):
    id:          int
    tipo:        str
    monto:       float
    descripcion: Optional[str]
    referencia:  Optional[str]
    estado:      str
    creado_en:   datetime

    class Config:
        from_attributes = True


# ── QR ───────────────────────────────────────────────────────
class QRResponse(BaseModel):
    qr_base64: str
    cedula:    str
    nombre:    str
    monto:     Optional[float] = None


# ── Health ────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    app:       str
    version:   str
    timestamp: str
    redis:     str
    kafka:     str
    sinerfin2: str
    database:  str
