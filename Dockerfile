# syntax=docker/dockerfile:1
# Dockerfile genérico (x86_64) para desarrollo/pruebas.
# Para despliegue en Raspberry Pi usa Dockerfile.raspbian (ver docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa poppler-utils libheif-examples curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs /app/uploads

# Descarga en build-time de los paquetes de idioma de Argos Translate, igual
# que en Dockerfile.raspbian, para que el contenedor no dependa de red en el
# primer arranque.
RUN python3 -c "from stockhogar.servicios.traductor_argos import _asegurar_paquetes_instalados; _asegurar_paquetes_instalados(); print('[OK] Modelos de Argos Translate descargados')"

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/" >/dev/null || exit 1

# --timeout 240 --worker-class gthread --threads 4: igual que en
# Dockerfile.raspbian, para que el escaneo de tickets no se corte a mitad de
# petición por el timeout de 30s por defecto de gunicorn. 240s es el escalón
# intermedio de la cadena del escáner (llamada a la API 180s < worker 240s <
# abort del frontend 270s, ver servicios/ocr/claude_ocr.py): deja 60s para la
# subida de la foto, el troceado y el emparejado contra el catálogo.
CMD ["sh", "-c", "gunicorn --workers 2 --worker-class gthread --threads 4 --timeout 240 --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile - 'stockhogar:create_app()'"]
