# 🔧 Instalación - Dreame!

## Opción 1: Docker (Recomendado)

### Requisitos
- Docker + Docker Compose

### Pasos

```bash
# 1. Clonar
git clone https://github.com/Alexpa112/Home-Stock.git
cd Home-Stock

# 2. Construir e iniciar
cd docker
docker compose up -d --build

# 3. Acceder
# Localhost:    http://localhost:5000
# Red local:    http://<tu-ip>:5000
```

### Comandos útiles
```bash
docker compose logs -f              # Ver logs en tiempo real
docker compose ps                   # Ver estado
docker compose restart              # Reiniciar
docker compose down                 # Parar (datos persisten)
docker compose down -v              # Parar y borrar BD (cuidado)
```

### Volúmenes
- `data/stock.db` - Persiste datos entre reinicios

---

## Opción 2: Desarrollo Local (Python)

### Requisitos
- Python 3.9+
- Tesseract-OCR (solo si quieres escanear tickets)

### Sin Tesseract (rápido)

```bash
# 1. Entorno virtual
python -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Ejecutar
python run.py
# http://localhost:5000
```

### Con Tesseract (OCR local)

**Windows:**
```powershell
choco install tesseract-ocr         # o descargarlo de https://github.com/UB-Mannheim/tesseract/wiki
pip install -r requirements.txt
python run.py
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

pip install -r requirements.txt
python run.py
```

---

## Opción 3: Raspberry Pi (Docker)

### Requisitos
- Raspberry Pi 3 o superior
- Conexión internet (instalación una sola vez)

### Pasos

```bash
# 1. Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo reboot

# 2. Después de reiniciar
git clone https://github.com/Alexpa112/Home-Stock.git
cd Home-Stock/docker
docker compose up -d --build

# 3. Ver logs
docker compose logs app
```

### Información
- **Primer inicio**: ~5 min (construcción de imagen)
- **Reinicios**: <10 seg
- **Consumo RAM**: ~80-100 MB
- **Consumo CPU**: Mínimo (inactivo)
- **Acceso**: http://raspberrypi.local:5000 (o IP local)

---

## Primeros Pasos

1. **Crear usuario**
   - Primera vez: te pide crear usuario + contraseña
   - Luego: login normal

2. **Crear primer producto**
   - Botón "+" en pestaña "Stock"
   - Elige de catálogo o crea nuevo

3. **Crear lista de compra**
   - Click en "📋 Mi lista" para abrir drawer
   - Botón "+ Nueva lista"

4. **Escanear ticket** (opcional)
   - Botón "📷" en cabecera
   - Fotografía el recibo
   - Revisa y confirma

---

## Troubleshooting Instalación

### "Puerto 5000 en uso"
```bash
# Cambiar puerto en docker-compose.yml
ports:
  - "8000:5000"      # Ahora en http://localhost:8000
```

### "Error: módulo pytesseract no encontrado"
```bash
pip install pytesseract
# Y asegúrate que Tesseract está instalado en tu SO
```

### "Permiso denegado en /dev/shm" (Docker)
```bash
docker compose down
docker system prune -a
docker compose up -d --build
```

### "BD corrupta"
```bash
# Opción 1: Resetear (borra datos)
rm data/stock.db
docker compose restart

# Opción 2: Backup y resetear
cp data/stock.db data/stock.db.backup
rm data/stock.db
docker compose restart
```

---

## Variables de Entorno

Crear `stockhogar/.env` (no versionar):

```ini
# Base de datos
DATABASE_PATH=data/stock.db

# Flask
FLASK_ENV=production      # o development
SECRET_KEY=tu-clave-super-segura

# OCR (opcional)
TESSERACT_PATH=/usr/bin/tesseract    # Linux
TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe  # Windows
```

---

## Actualizar a Versión Nueva

```bash
cd Home-Stock
git pull                    # Descargar cambios

# Si usas Docker:
cd docker
docker compose up -d --build   # Reconstruye imagen

# Si es desarrollo local:
pip install -r requirements.txt --upgrade
python run.py
```

**Los datos (stock.db) se preservan automáticamente.**

---

## Backup y Restauración

### Backup
```bash
# Docker
docker compose exec app cp data/stock.db /backup/stock.db

# Local
cp data/stock.db ~/backups/stock.db.$(date +%Y%m%d)
```

### Restaurar
```bash
cp ~/backups/stock.db data/stock.db
docker compose restart
```

---

## Performance Tuning

### Si va lento
1. **Índices en BD**: Ya están creados, no cambia
2. **Caché del navegador**: Limpiar F12 → Network → "Disable cache"
3. **Logs DEBUG**: Cambiar `FLASK_ENV=production` (no debug)

### Si falla con muchos productos (>10k)
```python
# En stockhogar/config.py
ITEMS_POR_PAGINA = 50  # Añadir paginación (TODO)
```

---

## Soporte

- **Bugs**: Abre issue en GitHub
- **Preguntas**: Mira [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Quieres colaborar**: Lee [DESARROLLO.md](DESARROLLO.md)
