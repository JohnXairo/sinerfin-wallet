"""
Publica solicitudes a IBM MQ desde sinerfin-wallet.
Usa la REST API de IBM MQ (puerto 9443) — no requiere librerías nativas ni pymqi.
La REST API viene incluida en IBM MQ 10.0 sin configuración adicional.

Cola destino: SINERFIN.RECARGA.REQUEST
Queue Manager: SINERFIN  (bus.sinergy.local)
Endpoint: PUT https://bus.sinergy.local:9443/ibmmq/rest/v2/messaging/qmgr/SINERFIN/queue/SINERFIN.RECARGA.REQUEST/message

Diseño fire-and-forget idéntico a kafka_service.py:
si MQ no está disponible la operación continúa sin interrupciones.
"""

import json
import threading
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings

settings = get_settings()

_mq_available = True


def _publicar(queue_name: str, payload: dict):
    """Envío a MQ vía REST API en thread separado — nunca bloquea el request."""
    global _mq_available

    def _send():
        global _mq_available
        try:
            url = (
                f"https://{settings.mq_host}:{settings.mq_rest_port}"
                f"/ibmmq/rest/v2/messaging/qmgr/{settings.mq_queue_manager}"
                f"/queue/{queue_name}/message"
            )
            body = json.dumps(payload, ensure_ascii=False)

            # Autenticación básica con usuario mqm o el que se configure
            auth = None
            if settings.mq_user:
                auth = (settings.mq_user, settings.mq_password)

            with httpx.Client(verify=False, timeout=5) as client:
                r = client.post(
                    url,
                    content=body.encode("utf-8"),
                    headers={
                        "Content-Type": "text/plain;charset=utf-8",
                        "ibm-mq-rest-csrf-token": "",   # header requerido por MQ REST API
                    },
                    auth=auth,
                )
                if r.status_code in (201, 204):
                    _mq_available = True
                else:
                    print(f"MQ REST error [{queue_name}] HTTP {r.status_code}: {r.text}")

        except Exception as e:
            _mq_available = False
            print(f"MQ REST error [{queue_name}]: {e}")

    threading.Thread(target=_send, daemon=True).start()


def publicar_recarga_request(
    cedula: str, nombre: str, monto: float, motor: str = "POSTGRES"
):
    """
    Publica una solicitud de recarga a SINERFIN.RECARGA.REQUEST via REST API.
    sinerfin2 (Java/JBoss) consume esta cola y procesa el retiro de la cuenta bancaria.
    """
    _publicar(settings.mq_queue_recarga, {
        "cedula":    cedula,
        "nombre":    nombre,
        "tipo":      "RETIRO",
        "valor":     monto,
        "motor":     motor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "origen":    "sinerfin-wallet"
    })


def is_alive() -> bool:
    return _mq_available
