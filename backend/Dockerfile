FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

# Build araçlar yalnızca derleme aşamasında; libpq runtime'da kalır.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 eisa \
    && useradd -m -u 1000 -g 1000 -s /usr/sbin/nologin eisa

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=eisa:eisa . .

# Stateless container: yerel disk'e yazılan media/ ve logs/ K8s'de kullanılmaz.
# Statik dosyaları image içinde topla (admin için).
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=1 python manage.py collectstatic --noinput || true

USER eisa

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1

CMD ["gunicorn", "core_api.wsgi:application", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--timeout", "30", \
     "--graceful-timeout", "10", \
     "--error-logfile", "-", \
     "--log-level", "warning"]
