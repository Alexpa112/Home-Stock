# Guía Completa: Instalar Home-Stock en Raspberry Pi

## 📋 Requisitos Previos

- **Raspberry Pi 3 o superior** (idealmente Pi 4 con 2GB+ RAM)
- **Raspbian Bullseye o Bookworm** (32-bit o 64-bit)
- **Conexión a internet estable**
- **Acceso sudo en la Raspberry Pi**
- **Tarjeta SD de 8GB mínimo** (recomendado 16GB+)

## 🚀 Instalación Rápida (Recomendado)

### Paso 1: Conectar a la Raspberry Pi

```bash
ssh pi@[DIRECCIÓN_IP_RPi]
# Contraseña por defecto: raspberry
```

### Paso 2: Descargar e Instalar

```bash
# Clonar el repositorio
git clone https://github.com/Alexpa112/Home-Stock.git
cd Home-Stock

# Ejecutar instalador (one-click)
chmod +x install.sh
./install.sh
```

**Tiempo estimado**: 15-25 minutos (varía según velocidad de internet)

El script se encargará de:
- ✅ Verificar requisitos
- ✅ Instalar Docker
- ✅ Instalar Docker Compose
- ✅ Descargar Home-Stock
- ✅ Configurar variables de entorno
- ✅ Construir imágenes Docker
- ✅ Iniciar servicios

### Paso 3: Acceder a la Aplicación

Una vez completado, abra el navegador en:
```
http://[DIRECCIÓN_IP_RPi]:5000
```

---

## 📝 Instalación Manual (Si el script falla)

Si el instalador automático no funciona, siga estos pasos:

### 1. Actualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Instalar Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
```

### 3. Instalar Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 4. Descargar Home-Stock

```bash
mkdir -p /opt/homestock
cd /opt/homestock
git clone https://github.com/Alexpa112/Home-Stock.git .
```

### 5. Configurar Variables

```bash
cp .env.example .env
# Editar según necesidad:
nano .env
```

### 6. Iniciar Servicios

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🛠️ Comandos Útiles

### Ver logs en tiempo real
```bash
cd /opt/homestock
docker-compose -f docker-compose.prod.yml logs -f stockhogar
```

### Reiniciar aplicación
```bash
docker-compose -f docker-compose.prod.yml restart stockhogar
```

### Detener aplicación
```bash
docker-compose -f docker-compose.prod.yml down
```

### Actualizar a última versión
```bash
cd /opt/homestock
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Ver estado de servicios
```bash
docker ps
docker stats
```

---

## 🔧 Solución de Problemas

### "docker command not found"
```bash
# Necesitas reiniciar para que el grupo docker se aplique
sudo reboot
```

### "Cannot connect to Docker daemon"
```bash
# Asegúrate que Docker está corriendo
sudo systemctl status docker
sudo systemctl start docker
```

### "Out of memory"
Si la Raspberry Pi se queda sin memoria:

1. Aumentar swap:
```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Cambiar CONF_SWAPSIZE=2048 (de 100)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

2. Liberar memoria:
```bash
docker system prune -a --volumes
```

### Aplicación lenta

En Raspberry Pi 3, puede ser lenta. Optimizaciones:

```bash
# Reducir logs
docker-compose -f docker-compose.prod.yml logs --tail 100

# Limitar recursos si es necesario (en docker-compose.prod.yml)
services:
  stockhogar:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
```

---

## 📊 Especificaciones por Modelo

### Raspberry Pi 3B
- RAM: 1GB
- **Capacidad**: 100-500 usuarios simultáneos
- Recomendación: Personal/pequeña familia

### Raspberry Pi 4 (2GB)
- RAM: 2GB
- **Capacidad**: 500-2000 usuarios
- Recomendación: Familia grande

### Raspberry Pi 4 (4GB+)
- RAM: 4GB+
- **Capacidad**: 2000+ usuarios
- Recomendación: Uso empresarial

---

## 🔐 Seguridad

### Cambiar Contraseña Predeterminada

Al iniciar por primera vez, crea un usuario con contraseña fuerte.

### Acceso Remoto Seguro

Si accedes desde fuera de la red local, usa SSH:

```bash
# Desde tu computadora
ssh pi@[DOMINIO_EXTERNO]
# Luego accede a Home-Stock via localhost:5000
```

### Firewall

```bash
# Habilitar UFW
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22    # SSH
sudo ufw allow 5000  # Home-Stock
sudo ufw enable
```

---

## 📈 Monitoreo

### Consumo de Recursos

```bash
docker stats homestock-app
```

### Verificar Salud de la Aplicación

```bash
curl http://localhost:5000/api/auth/estado
```

### Logs con Filtros

```bash
# Ver solo errores
docker-compose logs -f stockhogar | grep ERROR

# Ver últimas 100 líneas
docker-compose logs --tail 100
```

---

## 🔄 Actualización

Home-Stock se actualiza automáticamente cuando hay nuevas versiones.

Para actualizaciones manuales:

```bash
cd /opt/homestock
git pull origin main
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisa el log**: `docker logs homestock-app`
2. **Abre un issue**: [GitHub Issues](https://github.com/Alexpa112/Home-Stock/issues)
3. **Documentación**: Revisa `/opt/homestock/docs/`

---

## 📝 Configuración Avanzada

Ver `docker-compose.prod.yml` para opciones como:
- Puerto personalizado
- Variables de entorno
- Volúmenes persistentes
- Redes personalizadas

---

**¡Home-Stock está listo para usar!** 🎉

Última actualización: Julio 2026
