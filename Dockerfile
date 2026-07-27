# Dockerfile genérico (x86_64) para desarrollo/pruebas.
# Para despliegue en Raspberry Pi usa Dockerfile.raspbian (ver docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs /app/uploads

# Descarga en build-time de los paquetes de idioma de Argos Translate, igual
# que en Dockerfile.raspbian, para que el contenedor no dependa de red en el
# primer arranque.
RUN python3 -c "from stockhogar.servicios.traductor_argos import _asegurar_paquetes_instalados; _asegurar_paquetes_instalados(); print('[OK] Modelos de Argos Translate descargados')"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/" >/dev/null || exit 1

CMD ["sh", "-c", "gunicorn --factory --workers 2 --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile - stockhogar:create_app"]
