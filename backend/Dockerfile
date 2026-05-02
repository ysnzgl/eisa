FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 eisa \
    && useradd -m -u 1000 -g 1000 -s /usr/sbin/nologin eisa

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=eisa:eisa . .

USER eisa

EXPOSE 8000
CMD ["gunicorn", "core_api.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "30", \
     "--graceful-timeout", "10", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
