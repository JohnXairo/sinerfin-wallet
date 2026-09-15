#!/bin/bash
# ============================================================
# deploy-openshift.sh
# Despliega sinerfin-wallet en Red Hat OpenShift 4.22
# Prerequisitos:
#   - oc CLI instalado y autenticado: oc login https://api.<cluster>:6443
#   - Acceso al proyecto sinerfin: oc project sinerfin
# ============================================================

set -e

echo ""
echo "=== sinerfin-wallet Deploy OpenShift 4.22 ==="
echo ""

# ── 1. Crear proyecto si no existe ───────────────────────────
oc new-project sinerfin 2>/dev/null || oc project sinerfin
echo "OK proyecto: sinerfin"

# ── 2. Aplicar ConfigMap y Secret ────────────────────────────
oc apply -f k8s/01-namespace-configmap.yaml
echo "OK ConfigMap"

# Crear Secret si no existe (editar con tus valores reales)
oc create secret generic wallet-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL="postgresql://sinerfin:TU_PASSWORD@192.168.1.192:5432/sinerfin_wallet" \
  --dry-run=client -o yaml | oc apply -f -
echo "OK Secret"

# ── 3. Crear ImageStream y BuildConfig ───────────────────────
oc apply -f ocp/01-imagestream.yaml
oc apply -f ocp/02-buildconfig.yaml
echo "OK ImageStream + BuildConfig"

# ── 4. Iniciar el build (compila la imagen en RHOS) ──────────
echo "Iniciando build S2I..."
oc start-build sinerfin-wallet --follow
echo "OK imagen compilada"

# ── 5. Desplegar ─────────────────────────────────────────────
oc apply -f ocp/03-deployment.yaml
oc apply -f ocp/04-service.yaml
oc apply -f ocp/05-route.yaml
echo "OK manifiestos aplicados"

# ── 6. Esperar rollout ───────────────────────────────────────
oc rollout status deployment/sinerfin-wallet --timeout=120s

echo ""
echo "=== Deploy completado ==="
echo ""
oc get pods -l app=sinerfin-wallet
echo ""
oc get route sinerfin-wallet
echo ""
echo "URL: $(oc get route sinerfin-wallet -o jsonpath='{.spec.host}')"
echo "Docs: $(oc get route sinerfin-wallet -o jsonpath='{.spec.host}')/docs"
