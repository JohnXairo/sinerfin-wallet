import qrcode
import base64
import secrets
from io import BytesIO
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Usuario, Wallet, Transaccion
from app.core.security import get_current_user
from app.services.sinerfin_client import sinerfin_client
from app.services.redis_service import WalletCache
from app.services import kafka_service
from app.api.schemas import (
    SaldoResponse, RecargaRequest, TransferenciaRequest,
    PagoRequest, TransaccionResponse, QRResponse
)

router = APIRouter(prefix="/api/wallet", tags=["Wallet"])


def _get_wallet(usuario: Usuario, db: Session) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.usuario_id == usuario.id).first()
    if not wallet:
        raise HTTPException(404, "Wallet no encontrada")
    if not wallet.activa:
        raise HTTPException(400, "Wallet inactiva")
    return wallet


# ── GET /saldo ────────────────────────────────────────────────
@router.get("/saldo", response_model=SaldoResponse)
async def get_saldo(
    motor: str = "POSTGRES",
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = _get_wallet(usuario, db)

    # Cache Redis para saldo wallet
    saldo_wallet = WalletCache.get_saldo(usuario.id)
    if saldo_wallet is None:
        saldo_wallet = wallet.saldo
        WalletCache.set_saldo(usuario.id, saldo_wallet)

    # Cache Redis para saldo sinerfin
    sinerfin_data = WalletCache.get_saldo_sinerfin(usuario.cedula, motor)
    if not sinerfin_data:
        try:
            sinerfin_data = await sinerfin_client.obtener_saldo(usuario.cedula, motor)
            WalletCache.set_saldo_sinerfin(usuario.cedula, motor, sinerfin_data)
        except Exception:
            sinerfin_data = {"saldo": 0, "cuenta": 0}

    return SaldoResponse(
        saldo_wallet=saldo_wallet,
        saldo_sinerfin=sinerfin_data.get("saldo", 0),
        cuenta_sinerfin=sinerfin_data.get("cuenta", 0),
        nombre=usuario.nombre,
        cedula=usuario.cedula,
    )


# ── POST /recargar ────────────────────────────────────────────
@router.post("/recargar")
async def recargar(
    req: RecargaRequest,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mueve dinero desde cuenta sinerfin2 hacia la wallet."""
    wallet = _get_wallet(usuario, db)

    # Verificar saldo en sinerfin
    try:
        sinerfin_data = await sinerfin_client.obtener_saldo(usuario.cedula, req.motor)
        if sinerfin_data.get("saldo", 0) < req.monto:
            raise HTTPException(422, f"Saldo insuficiente en sinerfin. Disponible: ${sinerfin_data.get('saldo', 0):.2f}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Error consultando sinerfin2: {e}")

    # Debitar de sinerfin2
    try:
        tx = await sinerfin_client.registrar_transaccion(
            usuario.cedula, usuario.nombre, "RETIRO", req.monto, req.motor
        )
        if not tx.get("ok"):
            raise HTTPException(422, tx.get("mensaje", "Error en sinerfin2"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Error en sinerfin2: {e}")

    # Acreditar en wallet
    ref = secrets.token_hex(4).upper()
    wallet.saldo += req.monto
    db.add(Transaccion(
        wallet_id=wallet.id, tipo="RECARGA", monto=req.monto,
        descripcion=f"Recarga desde sinerfin ({req.motor})",
        referencia=ref, estado="COMPLETADA"
    ))
    db.commit()

    WalletCache.invalidar_saldo(usuario.id)
    WalletCache.invalidar_sinerfin(usuario.cedula, req.motor)
    WalletCache.incr_transacciones()
    kafka_service.publicar_transaccion_wallet(
        usuario.id, usuario.cedula, "RECARGA", req.monto, wallet.saldo, ref
    )

    return {"ok": True, "saldo_wallet": wallet.saldo, "referencia": ref,
            "mensaje": f"Recarga de ${req.monto:.2f} exitosa"}


# ── POST /pagar ───────────────────────────────────────────────
@router.post("/pagar")
async def pagar(
    req: PagoRequest,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pagar un concepto descontando del saldo de la wallet."""
    wallet = _get_wallet(usuario, db)

    if wallet.saldo < req.monto:
        raise HTTPException(422,
            f"Saldo insuficiente en wallet. Disponible: ${wallet.saldo:.2f}")

    ref = secrets.token_hex(4).upper()
    wallet.saldo -= req.monto
    db.add(Transaccion(
        wallet_id=wallet.id, tipo="PAGO", monto=req.monto,
        descripcion=req.concepto, referencia=ref, estado="COMPLETADA"
    ))
    db.commit()

    WalletCache.invalidar_saldo(usuario.id)
    WalletCache.incr_transacciones()
    kafka_service.publicar_transaccion_wallet(
        usuario.id, usuario.cedula, "PAGO", req.monto, wallet.saldo, ref
    )

    return {"ok": True, "saldo_wallet": wallet.saldo, "referencia": ref,
            "mensaje": f"Pago de ${req.monto:.2f} exitoso"}


# ── POST /transferir ──────────────────────────────────────────
@router.post("/transferir")
async def transferir(
    req: TransferenciaRequest,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Transferencia wallet a wallet por cedula."""
    if req.cedula_destino == usuario.cedula:
        raise HTTPException(400, "No puedes transferirte a ti mismo")

    wallet_origen = _get_wallet(usuario, db)
    if wallet_origen.saldo < req.monto:
        raise HTTPException(422,
            f"Saldo insuficiente. Disponible: ${wallet_origen.saldo:.2f}")

    # Buscar destinatario
    destino = db.query(Usuario).filter(Usuario.cedula == req.cedula_destino).first()
    if not destino or not destino.activo:
        raise HTTPException(404, "Usuario destinatario no encontrado en la wallet")

    wallet_destino = _get_wallet(destino, db)

    ref = secrets.token_hex(4).upper()

    # Debitar origen
    wallet_origen.saldo -= req.monto
    db.add(Transaccion(
        wallet_id=wallet_origen.id, tipo="TRANSFERENCIA", monto=req.monto,
        descripcion=req.descripcion or f"Transferencia a {destino.nombre}",
        referencia=ref, cedula_destino=req.cedula_destino, estado="COMPLETADA"
    ))

    # Acreditar destino
    wallet_destino.saldo += req.monto
    db.add(Transaccion(
        wallet_id=wallet_destino.id, tipo="TRANSFERENCIA", monto=req.monto,
        descripcion=f"Transferencia de {usuario.nombre}",
        referencia=ref, estado="COMPLETADA"
    ))

    db.commit()

    WalletCache.invalidar_saldo(usuario.id)
    WalletCache.invalidar_saldo(destino.id)
    WalletCache.incr_transacciones()
    kafka_service.publicar_transaccion_wallet(
        usuario.id, usuario.cedula, "TRANSFERENCIA", req.monto, wallet_origen.saldo, ref
    )

    return {"ok": True, "saldo_wallet": wallet_origen.saldo, "referencia": ref,
            "mensaje": f"Transferencia de ${req.monto:.2f} a {destino.nombre} exitosa"}


# ── GET /historial ────────────────────────────────────────────
@router.get("/historial", response_model=list[TransaccionResponse])
async def historial(
    limit: int = 20,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = _get_wallet(usuario, db)
    txs = (db.query(Transaccion)
           .filter(Transaccion.wallet_id == wallet.id)
           .order_by(Transaccion.creado_en.desc())
           .limit(limit).all())
    return txs


# ── GET /qr ───────────────────────────────────────────────────
@router.get("/qr", response_model=QRResponse)
async def generar_qr(
    monto: float | None = None,
    usuario: Usuario = Depends(get_current_user)
):
    """Genera QR de cobro para mostrar al pagador."""
    data = {"cedula": usuario.cedula, "nombre": usuario.nombre}
    if monto:
        data["monto"] = monto

    import json
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(json.dumps(data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0a0f1e", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return QRResponse(
        qr_base64=qr_b64,
        cedula=usuario.cedula,
        nombre=usuario.nombre,
        monto=monto
    )
