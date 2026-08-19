from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime, timezone
import enum


def _utcnow():
    """Timestamp UTC con zona horaria explícita (datetime.utcnow está deprecado en Python 3.12)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class EstadoTransaccion(str, enum.Enum):
    PENDIENTE  = "PENDIENTE"
    COMPLETADA = "COMPLETADA"
    FALLIDA    = "FALLIDA"
    REVERTIDA  = "REVERTIDA"


class TipoTransaccion(str, enum.Enum):
    RECARGA       = "RECARGA"        # cargar saldo a la wallet desde sinerfin
    PAGO          = "PAGO"           # pagar con wallet
    TRANSFERENCIA = "TRANSFERENCIA"  # wallet a wallet
    RETIRO        = "RETIRO"         # retirar a cuenta sinerfin
    QR_COBRO      = "QR_COBRO"       # cobro via QR


class Usuario(Base):
    __tablename__ = "wallet_usuarios"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    username       = Column(String(50), unique=True, nullable=False)
    email          = Column(String(100), unique=True, nullable=False)
    password_hash  = Column(String(100), nullable=False)
    nombre         = Column(String(150), nullable=False)
    cedula         = Column(String(20), unique=True, nullable=False)  # vincula con sinerfin2
    activo         = Column(Boolean, default=True)
    creado_en      = Column(DateTime(timezone=True), default=_utcnow)

    wallet         = relationship("Wallet", back_populates="usuario", uselist=False)


class Wallet(Base):
    __tablename__ = "wallets"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id     = Column(Integer, ForeignKey("wallet_usuarios.id"), unique=True)
    # Numeric(18,2): evita errores de redondeo en punto flotante para dinero
    saldo          = Column(Numeric(18, 2), default=0, nullable=False)
    activa         = Column(Boolean, default=True)
    creado_en      = Column(DateTime(timezone=True), default=_utcnow)
    actualizado_en = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    usuario        = relationship("Usuario", back_populates="wallet")
    transacciones  = relationship("Transaccion", back_populates="wallet")


class Transaccion(Base):
    __tablename__ = "wallet_transacciones"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id      = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    tipo           = Column(String(20), nullable=False)
    # Numeric(18,2): precisión exacta en centavos
    monto          = Column(Numeric(18, 2), nullable=False)
    descripcion    = Column(String(200))
    referencia     = Column(String(50))          # codigo de autorizacion
    cedula_destino = Column(String(20))          # para transferencias
    estado         = Column(String(20), default="COMPLETADA")
    creado_en      = Column(DateTime(timezone=True), default=_utcnow)

    wallet         = relationship("Wallet", back_populates="transacciones")
