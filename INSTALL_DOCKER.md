# 🚀 Instalación de StockHogar en Docker (Raspbian)

Guía completa para instalar StockHogar en una Raspberry Pi con Docker.

## 📋 Requisitos Previos

- **Raspbian OS** (Bullseye, Bookworm o similar)
- **1GB RAM mínimo** (2GB recomendado)
- **2GB espacio libre** en disco
- **Conexión a internet** para descargas
- **Acceso sudo** en la terminal

## ⚡ Instalación Rápida (1 Comando)

```bash
cd /ruta/del/proyecto && bash install.sh
```

El script de instalación hará TODO automáticamente.

## 📖 Instalación Manual (Paso a Paso)

Si prefieres hacerlo manualmente:

### 1. Clonar/Descargar el Proyecto

```bash
cd ~
git clone <repo> stockhogar
cd stockhogar
```

### 2. Hacer el Script Ejecutable

```bash
chmod +x install.sh verify.sh
```

### 3. Ejecutar Instalación

```bash
./install.sh
```

El script:
- ✅ Actualiza el sistema
- ✅ Instala Docker
- ✅ Instala Docker Compose
- ✅ Crea directorios necesarios
- ✅ Construye la imagen Docker
- ✅ Inicia los contenedores
- ✅ Verifica que todo funciona

## ✅ Verificar Instalación

Después de instalar, verifica que todo está bien:

```bash
./verify.sh
```

Debería ver todos los checks en verde [OK].

## 🌐 Acceder a la Aplicación

Una vez instalado, accede a:

**Desde el mismo dispositivo:**
```
http://localhost:5000
```

**Desde otro dispositivo en la red:**
```
http://<IP-RASPBERRY>:5000
```

Para encontrar tu IP:
```bash
hostname -I
```

## 📂 Estructura de Datos

Los datos se guardan en directorios locales para persistencia:

```
stockhogar/
├── data/                 # Base de datos SQLite
│   └── stockhogar.db
├── logs/                 # Logs de la aplicacion
│   └── app.log
├── uploads/              # Archivos subidos (tickets OCR)
│   └── [imagenes]
└── docker-compose.yml    # Configuracion de contenedores
```

## 🔧 Comandos Útiles

### Ver Logs

```bash
# Logs en tiempo real
docker-compose logs -f stockhogar

# Últimas 50 líneas
docker-compose logs --tail=50 stockhogar

# Logs de todo hace una hora
docker-compose logs --since 1h stockhogar
```

### Detener la Aplicación

```bash
docker-compose down
```

### Reiniciar

```bash
docker-compose restart
```

### Recrear Contenedores (si falló algo)

```bash
docker-compose up -d --force-recreate
```

### Ejecutar Comandos en el Contenedor

```bash
# Acceder a bash dentro del contenedor
docker-compose exec stockhogar bash

# Ejecutar comando Python
docker-compose exec stockhogar python3 -c "import flask; print('OK')"

# Ver variables de entorno
docker-compose exec stockhogar env | grep STOCK
```

### Ver Estado

```bash
# Estado de contenedores
docker-compose ps

# Estadísticas de recursos
docker stats
```

## 🆘 Troubleshooting

### La aplicación no carga

```bash
# Ver si el contenedor está ejecutando
docker-compose ps

# Si no está ejecutando, iniciar
docker-compose up -d

# Ver logs
docker-compose logs stockhogar
```

### Permiso denegado con Docker

Si ves "Permission denied while trying to connect to Docker daemon":

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Puerto 5000 en uso

Si el puerto ya está en uso, cambiar en `.env`:

```bash
# Editar .env
nano .env

# Cambiar STOCKHOGAR_PORT=5000 a otro puerto, ej 8080
# STOCKHOGAR_PORT=8080

# Reiniciar
docker-compose restart
```

### Memoria insuficiente

Si aparecen errores de memoria:

```bash
# Ver uso de memoria
free -h

# Reducir workers en .env
# WORKERS=2

docker-compose restart
```

### Tesseract no funciona

Si OCR no funciona:

```bash
# Verificar Tesseract en contenedor
docker-compose exec stockhogar tesseract --version

# Verificar idioma español
docker-compose exec stockhogar tesseract --list-langs | grep spa

# Reinstalar si falta
docker-compose rebuild --no-cache
docker-compose up -d
```

## 🔄 Actualizar la Aplicación

Si hay nuevas versiones:

```bash
# Parar contenedores
docker-compose down

# Actualizar código
git pull

# Reconstruir imagen
docker-compose build --no-cache

# Reiniciar
docker-compose up -d

# Verificar
./verify.sh
```

## 📊 Monitoreo Avanzado

### Dashboard de Docker

```bash
# Ver uso de recursos en tiempo real
watch -n 1 docker stats stockhogar
```

### Revisar Base de Datos

```bash
# Copiar DB a tu máquina para revisar
docker cp stockhogar-app:/app/data/stockhogar.db ./

# Con SQLite
sqlite3 stockhogar.db "SELECT * FROM productos LIMIT 5;"
```

## 🔐 Seguridad

### Cambiar Puerto Público

```bash
# En .env
STOCKHOGAR_PORT=8080

# Reiniciar
docker-compose restart
```

### Limitar Acceso

```bash
# En docker-compose.yml
# ports:
#   - "127.0.0.1:5000:5000"  # Solo localhost
# O para red local:
#   - "192.168.1.100:5000:5000"  # IP específica
```

### Backup de Datos

```bash
# Backup de BD
cp data/stockhogar.db data/stockhogar.db.backup

# Backup completo
tar -czf stockhogar-backup-$(date +%Y%m%d).tar.gz data/ logs/ uploads/

# Restaurar desde backup
tar -xzf stockhogar-backup-20240708.tar.gz
```

## 📞 Soporte

Si algo no funciona:

1. Ejecuta `./verify.sh` y copia el output
2. Ver logs: `docker-compose logs stockhogar`
3. Intenta reiniciar: `docker-compose restart`
4. Último recurso: `docker-compose up -d --force-recreate`

## ✨ Características de la Instalación

✅ **100% Automática** - Solo ejecuta un comando  
✅ **Resiliente** - Manejo exhaustivo de errores  
✅ **Verificable** - Script de verificación incluido  
✅ **Persistent** - Datos guardados en disco  
✅ **Monitoreable** - Fácil acceso a logs  
✅ **Updatable** - Se puede actualizar fácilmente  
✅ **ARM Compatible** - Optimizado para Raspberry Pi  
✅ **OCR Completo** - Tesseract + Español instalado  

## 🎯 Próximos Pasos

1. Accede a http://localhost:5000
2. Crea tu cuenta de usuario
3. Agrega tus espacios (cocina, almacén, etc)
4. Agrega categorías de productos
5. ¡Empieza a usar StockHogar!

---

**Versión:** 1.0  
**Última actualización:** 2026-07-08  
**Estado:** ✅ Listo para producción
