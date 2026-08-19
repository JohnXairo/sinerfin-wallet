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
kubectl version --client 2>/dev/null || {
    echo "ERROR: kubectl no encontrado. Instala k3s primero:"
    echo "  curl -sfL https://get.k3s.io | sh -"
    exit 1
}
echo "OK"

# ── 2. Build de la imagen ─────────────────────────────────────
echo "[2/5] Construyendo imagen..."
cd "$APP_DIR"

if command -v docker &>/dev/null; then
    echo "Usando Docker..."
    docker build -t "$IMAGE" .
    echo "OK - imagen construida con Docker"
elif command -v podman &>/dev/null; then
    echo "Usando Podman..."
    podman build -t "$IMAGE" .
    echo "OK - imagen construida con Podman"
elif command -v buildah &>/dev/null; then
    echo "Usando Buildah..."
    buildah bud -t "$IMAGE" .
    echo "OK - imagen construida con Buildah"
else
    echo "ERROR: No se encontró Docker, Podman ni Buildah."
    echo "Instala uno de ellos:"
    echo "  dnf install -y podman    # RHEL/CentOS/Fedora"
    echo "  apt install -y podman    # Debian/Ubuntu"
    exit 1
fi

# ── 3. Importar imagen en k3s containerd ─────────────────────
echo "[3/5] Importando imagen en k3s containerd..."
if command -v docker &>/dev/null; then
    docker save "$IMAGE" | k3s ctr images import -
elif command -v podman &>/dev/null; then
    podman save --format oci-archive "$IMAGE" | k3s ctr images import -
elif command -v buildah &>/dev/null; then
    buildah push "$IMAGE" oci-archive:/tmp/wallet-image.tar
    k3s ctr images import /tmp/wallet-image.tar
    rm -f /tmp/wallet-image.tar
fi
echo "OK - imagen importada en containerd"

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
