import json
import threading
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from app.core.config import get_settings

settings = get_settings()

_producer: KafkaProducer | None = None
_lock = threading.Lock()


def _get_producer() -> KafkaProducer | None:
    global _producer
    if _producer is not None:
        return _producer
    with _lock:
        if _producer is not None:
            return _producer
        try:
            _producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks=0,                  # fire-and-forget
                request_timeout_ms=1000,
                api_version_auto_timeout_ms=1000,
            )
        except NoBrokersAvailable:
            print("Kafka no disponible — eventos no se publicaran")
            _producer = None
    return _producer


def _publicar(topic: str, key: str, payload: dict):
    """Fire-and-forget en thread separado — nunca bloquea el request."""
    def _send():
        try:
            p = _get_producer()
            if p:
                p.send(topic, key=key, value=payload)
        except Exception as e:
            print(f"Kafka error [{topic}]: {e}")

    threading.Thread(target=_send, daemon=True).start()


def publicar_transaccion_wallet(
    user_id: int, cedula: str, tipo: str,
    monto: float, saldo_nuevo: float, referencia: str = ""
):
    _publicar(settings.kafka_topic_wallet, cedula, {
        "evento":      "WALLET_TRANSACCION",
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "user_id":     user_id,
        "cedula":      cedula,
        "tipo":        tipo,
        "monto":       monto,
        "saldo_nuevo": saldo_nuevo,
        "referencia":  referencia,
        "servicio":    "sinerfin-wallet"
    })


def publicar_auditoria(evento: str, username: str, detalle: str):
    _publicar(settings.kafka_topic_auditoria, username, {
        "evento":    evento,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "username":  username,
        "detalle":   detalle,
        "servicio":  "sinerfin-wallet"
    })
