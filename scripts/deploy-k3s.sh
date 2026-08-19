#!/bin/bash
# ============================================================
# deploy-k3s.sh
# Build de la imagen y despliegue completo en k3s
# Ejecutar en el servidor k3s como root o con permisos kubectl
# ============================================================

set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="sinerfin-wallet:latest"

echo ""
echo "=== Sinerfin Wallet - Deploy k3s ==="
echo "Directorio: $APP_DIR"
echo "Imagen:     $IMAGE"
echo ""

# ── 1. Verificar k3s ─────────────────────────────────────────
echo "[1/5] Verificando k3s..."
kubectl version --client --short 2>/dev/null || {
    echo "ERROR: kubectl no encontrado. Instala k3s primero:"
    echo "  curl -sfL https://get.k3s.io | sh -"
    exit 1
}
echo "OK"

# ── 2. Build de la imagen Docker ──────────────────────────────
echo "[2/5] Construyendo imagen Docker..."
cd "$APP_DIR"
docker build -t "$IMAGE" . || {
    # Si no hay Docker, intentar con nerdctl (containerd nativo de k3s)
    echo "Docker no encontrado, intentando con nerdctl..."
    nerdctl build -t "$IMAGE" .
}
echo "OK - imagen $IMAGE construida"

# ── 3. Importar imagen en k3s (si se usa containerd) ─────────
echo "[3/5] Importando imagen en k3s containerd..."
if command -v k3s &>/dev/null; then
    docker save "$IMAGE" | k3s ctr images import - 2>/dev/null \
        && echo "OK - imagen importada en containerd" \
        || echo "AVISO: import manual no necesario (Docker socket disponible)"
fi

# ── 4. Aplicar manifiestos ────────────────────────────────────
echo "[4/5] Aplicando manifiestos k8s..."
kubectl apply -f "$APP_DIR/k8s/01-namespace-configmap.yaml"
kubectl apply -f "$APP_DIR/k8s/02-secret.yaml"
kubectl apply -f "$APP_DIR/k8s/03-deployment.yaml"
kubectl apply -f "$APP_DIR/k8s/04-service-ingress.yaml"
echo "OK - manifiestos aplicados"

# ── 5. Esperar que los pods esten listos ──────────────────────
echo "[5/5] Esperando pods..."
kubectl rollout status deployment/sinerfin-wallet -n sinerfin --timeout=120s

echo ""
echo "=== Deploy completado ==="
echo ""
kubectl get pods -n sinerfin
echo ""
echo "URL: http://wallet.sinergy.local"
echo "     (agrega al /etc/hosts: <IP_K3S> wallet.sinergy.local)"
echo ""
echo "Health: kubectl exec -n sinerfin deploy/sinerfin-wallet -- curl -s localhost:8000/health"
echo "Logs:   kubectl logs -n sinerfin -l app=sinerfin-wallet -f"
echo "Docs:   http://wallet.sinergy.local/docs"
echo ""
