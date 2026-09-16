# Despliegue en Red Hat OpenShift 4.22

## Prerequisitos

1. Acceso al cluster RHOS 4.22 con `oc` CLI
2. Permisos para crear proyectos y builds
3. El repo GitHub accesible desde el cluster (o imagen pre-compilada)

## Estructura de manifiestos

```
ocp/
├── 01-imagestream.yaml   # Registry interno RHOS
├── 02-buildconfig.yaml   # Build S2I desde GitHub
├── 03-deployment.yaml    # Deployment compatible SCC restricted-v2
├── 04-service.yaml       # Service interno
├── 05-route.yaml         # Route con TLS edge (equivalente al Ingress)
├── 06-configmap.yaml     # Variables de entorno (sin secretos)
├── 07-secret.yaml        # Credenciales (DATABASE_URL, SECRET_KEY)
├── 08-hpa.yaml           # Autoscaling 2-6 pods
└── 09-networkpolicy.yaml # Trafico permitido
```

## Deploy en 3 pasos

### Paso 1 — Login y proyecto
```bash
oc login https://api.<tu-cluster>:6443 -u <usuario>
oc new-project sinerfin
```

### Paso 2 — Configurar credenciales
```bash
# Editar ocp/07-secret.yaml con tus valores reales, luego:
oc apply -f ocp/07-secret.yaml

# O directamente con oc:
oc create secret generic wallet-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=DATABASE_URL="postgresql://sinerfin:PASS@192.168.1.192:5432/sinerfin_wallet" \
  -n sinerfin
```

### Paso 3 — Deploy completo
```bash
bash scripts/deploy-openshift.sh
```

## Diferencias clave vs k3s

| Concepto      | k3s                    | OpenShift 4.22              |
|---------------|------------------------|-----------------------------|
| Ingress       | Traefik Ingress        | Route (con TLS edge)        |
| Imagen        | localhost (containerd) | ImageStream (registry RHOS) |
| Build         | Manual (docker build)  | BuildConfig S2I             |
| Seguridad     | Sin restricciones      | SCC restricted-v2           |
| Autoscaling   | Manual                 | HPA cpu/memory              |
| DNS interno   | wallet.sinergy.local   | wallet-sinerfin.apps.<cluster> |

## Verificar el despliegue

```bash
# Estado de los pods
oc get pods -n sinerfin -l app=sinerfin-wallet

# URL de acceso
oc get route sinerfin-wallet -n sinerfin

# Logs en tiempo real
oc logs -n sinerfin -l app=sinerfin-wallet -f

# Health check
curl https://$(oc get route sinerfin-wallet -o jsonpath='{.spec.host}')/health

# Docs Swagger
curl https://$(oc get route sinerfin-wallet -o jsonpath='{.spec.host}')/docs
```

## Notas importantes para RHOS 4.22

1. **SCC restricted-v2** — el Dockerfile ya usa usuario 1001 (no root), compatible
2. **ImageStream** — RHOS no puede usar `imagePullPolicy: Never`, la imagen
   debe estar en el registry interno (generada por BuildConfig) o en uno externo
3. **Route TLS** — el certificado lo genera RHOS automáticamente con Let's Encrypt
   o el CA interno del cluster
4. **NetworkPolicy** — incluida para limitar el trafico de red (requerido en algunos clusters RHOS enterprise)
5. **HPA** — el autoscaling es visible en Instana — buena demo de observabilidad

## Para la demo de Instana en RHOS

El agente de Instana en RHOS se despliega como DaemonSet via el Instana Operator.
El pod wallet ya tiene la anotacion `instana.io/service-name: sinerfin-wallet`
y la variable `INSTANA_AGENT_HOST` que apunta al agente del nodo.
