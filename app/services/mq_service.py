"""
Publica solicitudes a IBM MQ desde sinerfin-wallet.

Cola destino: SINERFIN.RECARGA.REQUEST
Queue Manager: SINERFIN  (bus.sinergy.local:1414)
Canal: DEV.APP.SVRCONN

Diseño fire-and-forget idéntico a kafka_service.py:
si MQ no está disponible la operación continúa sin interrupciones.
"""

import json
import threading
from datetime import datetime, timezone

from app.core.config import get_settings

settings = get_settings()

_mq_available = True  # se pone en False si la conexión inicial falla


def _publicar(queue_name: str, payload: dict):
    """Envío a MQ en thread separado — nunca bloquea el request."""
    global _mq_available

    def _send():
        global _mq_available
        try:
            import pymqi  # import diferido: no rompe el arranque si pymqi no está
            conn_info = f"{settings.mq_host}({settings.mq_port})"
            cd = pymqi.CD()
            cd.ChannelName = settings.mq_channel.encode()
            cd.ConnectionName = conn_info.encode()
            cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
            cd.TransportType = pymqi.CMQC.MQXPT_TCP

            qmgr = pymqi.QueueManager(None)
            qmgr.connectWithOptions(
                settings.mq_queue_manager,
                cd=cd,
                opts=pymqi.CMQC.MQCNO_CLIENT_BINDING
            )

            queue = pymqi.Queue(qmgr, queue_name)
            md = pymqi.MD()
            md.Format = pymqi.CMQC.MQFMT_STRING
            md.CodedCharSetId = 1208  # UTF-8

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            queue.put(body, md)
            queue.close()
            qmgr.disconnect()

            _mq_available = True

        except ImportError:
            print("pymqi no instalado — evento MQ no publicado")
        except Exception as e:
            _mq_available = False
            print(f"MQ error [{queue_name}]: {e}")

    threading.Thread(target=_send, daemon=True).start()


def publicar_recarga_request(
    cedula: str, nombre: str, monto: float, motor: str = "POSTGRES"
):
    """
    Publica una solicitud de recarga a SINERFIN.RECARGA.REQUEST.
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
