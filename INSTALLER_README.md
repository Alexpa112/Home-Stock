# 📦 Instalador de StockHogar para Raspbian

## Qué incluye este paquete

Este instalador contiene todo lo necesario para ejecutar StockHogar en una Raspberry Pi:

```
stockhogar/
├── install.sh              ← EJECUTA ESTO PRIMERO
├── verify.sh               ← Verificar instalacion
├── maintenance.sh          ← Mantenimiento
├── Dockerfile.raspbian     ← Definicion de imagen Docker
├── docker-compose.yml      ← Orquestacion de contenedores
├── .env.example            ← Variables de configuracion
├── INSTALL_DOCKER.md       ← Guia completa
├── INSTALLER_README.md     ← Este archivo
└── stockhogar/             ← Codigo de la aplicacion
    ├── __init__.py
    ├── db.py
    ├── config.py
    ├── rutas/              ← Endpoints API
    ├── servicios/          ← OCR y servicios
    ├── templates/          ← HTML frontend
    └── static/             ← CSS/JS
```

## 🚀 Comenzar en 30 segundos

### PASO 1: Descargar/Descomprimir

Asegurate de que tienes toda la carpeta `stockhogar` en tu home de Raspberry:

```bash
ls ~/stockhogar/install.sh
# Deberia mostrar el archivo
```

### PASO 2: Ejecutar Instalador

```bash
cd ~/stockhogar
bash install.sh
```

El script:
- Verificará requisitos ✓
- Instalará Docker ✓
- Instalará Docker Compose ✓
- Creará directorios ✓
- Construirá imagen (10-20 min) ✓
- Iniciará aplicacion ✓
- Verificará que funciona ✓

### PASO 3: Acceder

```
http://localhost:5000
```

O desde otra máquina en la red:

```
http://<IP-RASPBERRY>:5000
```

Obtener IP:
```bash
hostname -I
```

## ✅ Verificación Post-Instalación

```bash
bash verify.sh
```

Debería ver 20+ checks en verde [OK].

## 🔧 Comandos Principales

```bash
# Ver logs en tiempo real
docker-compose logs -f

# Detener
docker-compose down

# Reiniciar
docker-compose restart

# Mantenimiento
bash maintenance.sh
```

## 📚 Documentación Completa

Ver `INSTALL_DOCKER.md` para:
- Instalación manual paso a paso
- Troubleshooting detallado
- Backup y restauracion
- Seguridad y monitoreo
- Actualizaciones

## 🆘 Si algo sale mal

1. **Lee los logs:**
   ```bash
   docker-compose logs stockhogar
   ```

2. **Verifica requisitos:**
   ```bash
   bash verify.sh
   ```

3. **Intenta reiniciar:**
   ```bash
   docker-compose restart
   ```

4. **Reconstruye si es necesario:**
   ```bash
   docker-compose down
   docker-compose up -d --force-recreate
   ```

## 💾 Dónde están tus datos

```
stockhogar/
├── data/stockhogar.db      ← Base de datos (IMPORTANTE!)
├── logs/                   ← Logs de aplicacion
└── uploads/                ← Imagenes OCR
```

**Backup importante:** Copia regularly la carpeta `data/`

## 🔐 Seguridad

Por defecto:
- Solo accesible en localhost
- Puerto 5000
- SQLite local (no necesita servidor)
- Cambiar SECRET_KEY en `.env` para produccion

## ⚡ Requisitos Minimos

- Raspbian (cualquier version reciente)
- 512MB RAM (1GB+ recomendado)
- 2GB espacio libre
- Internet para instalacion

## 📊 Especificaciones Instaladas

- **Flask 3.1.3** - Web framework
- **Python 3.11** - Runtime
- **SQLite3** - Base de datos
- **Tesseract OCR 5.x** - OCR con soporte español
- **OpenCV 5.0** - Procesamiento de imagenes
- **Fuzzywuzzy** - Busqueda fuzzy
- **Docker** - Contenedorizacion

## 🎯 Proximos Pasos Despues de Instalar

1. Accede a http://localhost:5000
2. Crea usuario admin
3. Configura tus espacios (cocina, almacen, etc.)
4. Agrega categorias de productos
5. Empieza a agregar productos
6. Prueba la funcionalidad OCR de tickets

## 📞 Soporte

- Ver `INSTALL_DOCKER.md` para troubleshooting completo
- Ejecutar `bash verify.sh` para diagnosticos
- Revisar logs: `docker-compose logs -f`

## ✨ Ventajas de esta Instalacion

✅ 100% Automatica
✅ A prueba de fallos
✅ Facil de mantener
✅ Completamente funcional
✅ Datos persistentes
✅ Facil actualizacion
✅ Optimizado para ARM (Raspberry Pi)
✅ OCR en español incluido
✅ Backup y restauracion facil
✅ Monitoreo y logs

## 📝 Licencia

StockHogar - Sistema de Inventario

---

**Instalacion completada correctamente:** Accede a http://localhost:5000
