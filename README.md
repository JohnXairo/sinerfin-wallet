# sinerfin-wallet

Billetera digital integrada con el core bancario **sinerfin2**.
Desarrollada en **Python 3.12 + FastAPI** — desplegada en **k3s** (Kubernetes ligero).

## Stack

```
React (frontend)
    ↓
FastAPI (Python 3.12) - puerto 8000
    ↓              ↓              ↓
PostgreSQL      sinerfin2      Redis/Kafka
(wallet DB)   (core bancario)  (cache/eventos)
```

## Funcionalidades

| Operacion | Descripcion |
|---|---|
| Registro/Login | JWT, bcrypt, sesion stateless |
| Ver saldo | Saldo wallet + saldo sinerfin2 (con cache Redis) |
| Recargar | Mueve dinero de sinerfin2 a la wallet |
| Pagar | Descuenta del saldo wallet |
| Transferir | Wallet a wallet por cedula |
| Historial | Ultimas 20 transacciones |
| QR de cobro | Genera QR para recibir pagos |
| Health | `/health`, `/live`, `/ready` para k3s probes |

## Instalacion rapida (desarrollo)

```bash
# 1. Clonar
git clone https://github.com/JohnXairo/sinerfin-wallet.git
cd sinerfin-wallet

# 2. Configurar variables
cp .env.example .env
# Editar .env con tus valores

# 3. Instalar dependencias Python
pip install -r requirements.txt

# 4. Arrancar
uvicorn app.main:app --reload --port 8000
```

Swagger UI disponible en: http://localhost:8000/docs

## Despliegue en k3s

```bash
# Instalar k3s (una sola vez)
curl -sfL https://get.k3s.io | sh -

# Completar credenciales en k8s/02-secret.yaml

# Deploy completo
bash scripts/deploy-k3s.sh
```

Acceso: http://wallet.sinergy.local  
(agregar al `/etc/hosts`: `<IP_K3S> wallet.sinergy.local`)

## Comandos utiles k3s

```bash
# Ver pods
kubectl get pods -n sinerfin

# Logs en tiempo real
kubectl logs -n sinerfin -l app=sinerfin-wallet -f

# Reiniciar deployment
kubectl rollout restart deployment/sinerfin-wallet -n sinerfin

# Escalar
kubectl scale deployment/sinerfin-wallet -n sinerfin --replicas=3
```

## Estructura del proyecto

```
sinerfin-wallet/
├── app/
│   ├── api/        # routers FastAPI (auth, wallet, health)
│   ├── core/       # config, security (JWT, bcrypt)
│   ├── db/         # SQLAlchemy engine y session
│   ├── models/     # modelos ORM (Usuario, Wallet, Transaccion)
│   └── services/   # sinerfin_client, redis_service, kafka_service
├── frontend/       # React + Vite (pendiente)
├── k8s/            # manifiestos Kubernetes/k3s
├── scripts/        # deploy-k3s.sh
├── Dockerfile      # multi-stage, compatible RHOS
└── requirements.txt
```
