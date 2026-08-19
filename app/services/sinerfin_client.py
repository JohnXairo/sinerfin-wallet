import httpx
from app.core.config import get_settings

settings = get_settings()


class SinerfinClient:
    """
    Cliente HTTP para consumir la API REST de sinerfin2 (JBoss).
    Endpoints:
        GET  /api/saldo?cedula=X
        POST /api/transaccion
        GET  /api/tarjetas?cedula=X
    """

    def __init__(self):
        self.base_url = settings.sinerfin_base_url
        self.timeout  = settings.sinerfin_timeout

    async def obtener_saldo(self, cedula: str, motor: str = "POSTGRES") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.base_url}/api/saldo",
                params={"cedula": cedula},
                headers={"X-DB-Motor": motor}
            )
            r.raise_for_status()
            return r.json()

    async def registrar_transaccion(
        self, cedula: str, nombre: str,
        tipo: str, valor: float, motor: str = "POSTGRES"
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/transaccion",
                json={"cedula": cedula, "nombre": nombre,
                      "tipo": tipo, "valor": valor},
                headers={"X-DB-Motor": motor}
            )
            r.raise_for_status()
            return r.json()

    async def obtener_tarjetas(self, cedula: str, motor: str = "POSTGRES") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.base_url}/api/tarjetas",
                params={"cedula": cedula},
                headers={"X-DB-Motor": motor}
            )
            r.raise_for_status()
            return r.json()


sinerfin_client = SinerfinClient()
