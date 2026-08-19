# ── App Python ────────────────────────────────────────────────
# ubi9/python-312: imagen base certificada Red Hat
# Compatible con Docker, k3s y OpenShift (RHOS)
# NOTE: El Stage de frontend React se activará cuando exista frontend/
FROM registry.access.redhat.com/ubi9/python-312:latest

# OpenShift corre con usuario arbitrario (no root)
# k3s también funciona con este usuario
USER root
RUN mkdir -p /app && chown -R 1001:0 /app && chmod -R g=u /app
USER 1001

WORKDIR /app

# Dependencias Python
COPY --chown=1001:0 requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY --chown=1001:0 app/ ./app/

# Variables de entorno por defecto (overrideables via ConfigMap/Secret en k3s/RHOS)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# Health check para k3s y Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/live').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
